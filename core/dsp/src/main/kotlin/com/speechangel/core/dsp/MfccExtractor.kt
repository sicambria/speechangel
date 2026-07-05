package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.FeatureSequence
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * How many temporal-derivative blocks the feature vector carries.
 *
 * The blocks are **concatenated**, never summed (LIVE BUG #1): static | Δ | ΔΔ. So for `numCoefficients`
 * static coefficients the per-frame width is `numCoefficients * order` where order = 1 (NONE), 2 (DELTA),
 * or 3 (DELTA_DELTA).
 */
enum class DeltaOrder { NONE, DELTA, DELTA_DELTA }

/**
 * Noise-robust front-end mode (Phase 3, far-field/noise). [NONE] is the default and byte-identical to
 * the original pipeline. [SPECTRAL_SUBTRACTION] estimates a per-mel-band stationary noise floor from
 * the quietest frames and rectify-subtracts it in the *energy* domain (before the log) — a non-linear
 * step, so unlike a constant offset it survives CMN. Its FRR+FAR benefit is only decidable on real
 * far-field/noise audio (Bucket B); this is the front-end option that bake-off measures against baseline.
 */
enum class NoiseReduction { NONE, SPECTRAL_SUBTRACTION }

/** Configuration for [MfccExtractor]. Defaults are standard 16 kHz speech settings. */
data class MfccConfig(
    val sampleRateHz: Int = 16_000,
    val frameLengthMs: Int = 25,
    val frameShiftMs: Int = 10,
    val numMelFilters: Int = 26,
    val numCoefficients: Int = 13,
    val preEmphasis: Float = 0.97f,
    val lowFreqHz: Double = 20.0,
    val highFreqHz: Double = 0.0, // 0 => Nyquist (sampleRate / 2)
    val cepstralLifter: Int = 22,
    /**
     * Cepstral Mean Normalization (CMN): subtract the per-coefficient mean over the utterance.
     * Variance is deliberately NOT normalized — that would rescale DTW distances and invalidate the
     * per-deployment acceptance-threshold calibration (audit 2026-06-28_mfcc-cmvn-misnomer).
     */
    val applyCmn: Boolean = true,
    val deltaOrder: DeltaOrder = DeltaOrder.NONE,
    /** Noise-robust front-end mode. [NoiseReduction.NONE] keeps the pipeline byte-identical. */
    val noiseReduction: NoiseReduction = NoiseReduction.NONE,
    /** Spectral-subtraction over-subtraction factor α: how many noise-floors to remove. */
    val noiseOverSubtraction: Double = 1.5,
    /** Spectral floor β as a fraction of the band's own energy, so a band is never fully zeroed. */
    val noiseSpectralFloor: Double = 0.05,
    /** Percentile (0..1) of each band's energy across frames taken as its stationary noise floor. */
    val noiseFloorPercentile: Double = 0.1,
) {
    val frameLength: Int get() = sampleRateHz * frameLengthMs / 1000
    val frameShift: Int get() = sampleRateHz * frameShiftMs / 1000
    val effectiveHighFreqHz: Double get() = if (highFreqHz > 0.0) highFreqHz else sampleRateHz / 2.0
}

/**
 * Extracts a sequence of MFCC frames from a PCM buffer. Pure, deterministic, JVM-testable —
 * this is the language-independent feature front end shared by enrollment and recognition.
 */
class MfccExtractor(private val config: MfccConfig = MfccConfig()) {

    private val fftSize = Fft.nextPowerOfTwo(config.frameLength)
    private val hamming = hammingWindow(config.frameLength)
    private val melBank = MelFilterBank(
        numFilters = config.numMelFilters,
        fftSize = fftSize,
        sampleRateHz = config.sampleRateHz,
        lowFreqHz = config.lowFreqHz,
        highFreqHz = config.effectiveHighFreqHz,
    )
    private val lifter = cepstralLifter(config.numCoefficients, config.cepstralLifter)

    fun extract(audio: AudioSamples): FeatureSequence {
        if (audio.isEmpty || audio.samples.size < config.frameLength) {
            return FeatureSequence(emptyList())
        }
        val signal = preEmphasize(audio.samples, config.preEmphasis)
        val frames = when (config.noiseReduction) {
            NoiseReduction.NONE -> mfccFrames(signal)
            NoiseReduction.SPECTRAL_SUBTRACTION -> denoisedMfccFrames(signal)
        }
        var sequence = frames
        if (config.applyCmn) sequence = cmn(sequence)
        sequence = when (config.deltaOrder) {
            DeltaOrder.NONE -> sequence
            DeltaOrder.DELTA -> withDeltas(sequence, includeAcceleration = false)
            DeltaOrder.DELTA_DELTA -> withDeltas(sequence, includeAcceleration = true)
        }
        return FeatureSequence(sequence)
    }

    /** Default (no noise reduction) per-frame MFCC extraction — byte-identical to the original path. */
    private fun mfccFrames(signal: FloatArray): ArrayList<FloatArray> {
        val frames = ArrayList<FloatArray>()
        var start = 0
        while (start + config.frameLength <= signal.size) {
            frames.add(mfccOfFrame(signal, start))
            start += config.frameShift
        }
        return frames
    }

    private fun mfccOfFrame(signal: FloatArray, start: Int): FloatArray {
        val power = powerOfFrame(signal, start)
        val logMel = melBank.logEnergies(power)
        return dct(logMel, config.numCoefficients).also { applyLifter(it) }
    }

    private fun powerOfFrame(signal: FloatArray, start: Int): FloatArray {
        val windowed = FloatArray(config.frameLength)
        for (i in 0 until config.frameLength) {
            windowed[i] = signal[start + i] * hamming[i]
        }
        return Fft.powerSpectrum(windowed, fftSize)
    }

    /**
     * Noise-robust per-frame MFCC: estimate a per-band stationary noise floor from the quietest frames,
     * rectify-subtract it in the energy domain (`max(e - α·floor, β·e)`), then log → DCT → lifter.
     */
    private fun denoisedMfccFrames(signal: FloatArray): ArrayList<FloatArray> {
        val energies = ArrayList<DoubleArray>()
        var start = 0
        while (start + config.frameLength <= signal.size) {
            energies.add(melBank.energies(powerOfFrame(signal, start)))
            start += config.frameShift
        }
        if (energies.isEmpty()) return ArrayList()

        val floors = perBandFloor(energies, config.noiseFloorPercentile)
        val out = ArrayList<FloatArray>(energies.size)
        for (e in energies) {
            val logMel = FloatArray(config.numMelFilters) { b ->
                val subtracted = e[b] - config.noiseOverSubtraction * floors[b]
                val floored = maxOf(subtracted, config.noiseSpectralFloor * e[b])
                ln(floored.coerceAtLeast(ENERGY_FLOOR)).toFloat()
            }
            out.add(dct(logMel, config.numCoefficients).also { applyLifter(it) })
        }
        return out
    }

    /** Per-band noise floor = the [percentile] (0..1) of that band's energy across all frames. */
    private fun perBandFloor(energies: List<DoubleArray>, percentile: Double): DoubleArray {
        val bands = config.numMelFilters
        val n = energies.size
        val idx = (percentile.coerceIn(0.0, 1.0) * (n - 1)).toInt()
        return DoubleArray(bands) { b ->
            val column = DoubleArray(n) { t -> energies[t][b] }
            column.sort()
            column[idx]
        }
    }

    private fun applyLifter(coeffs: FloatArray) {
        for (k in coeffs.indices) coeffs[k] *= lifter[k]
    }

    internal companion object {
        /** Positivity floor for mel-band energy before the log (matches MelFilterBank's own floor). */
        const val ENERGY_FLOOR = 1e-10

        fun hammingWindow(n: Int): FloatArray = FloatArray(n) { i -> (0.54 - 0.46 * cos(2.0 * PI * i / (n - 1))).toFloat() }

        fun cepstralLifter(numCoeffs: Int, lifter: Int): FloatArray = if (lifter <= 0) {
            FloatArray(numCoeffs) { 1f }
        } else {
            FloatArray(numCoeffs) { k -> (1.0 + lifter / 2.0 * sin(PI * k / lifter)).toFloat() }
        }

        fun preEmphasize(input: FloatArray, coeff: Float): FloatArray {
            if (coeff == 0f) return input.copyOf()
            val out = FloatArray(input.size)
            out[0] = input[0]
            for (i in 1 until input.size) out[i] = input[i] - coeff * input[i - 1]
            return out
        }

        /** Orthonormal DCT-II over [logMel], keeping [numCoeffs] coefficients. */
        fun dct(logMel: FloatArray, numCoeffs: Int): FloatArray {
            val m = logMel.size
            val out = FloatArray(numCoeffs)
            val scale0 = sqrt(1.0 / m)
            val scaleK = sqrt(2.0 / m)
            for (k in 0 until numCoeffs) {
                var sum = 0.0
                for (n in 0 until m) {
                    sum += logMel[n] * cos(PI * k * (n + 0.5) / m)
                }
                out[k] = (sum * if (k == 0) scale0 else scaleK).toFloat()
            }
            return out
        }

        /** Cepstral Mean Normalization: subtract the per-coefficient mean. Variance is left as-is. */
        fun cmn(frames: List<FloatArray>): ArrayList<FloatArray> {
            if (frames.isEmpty()) return ArrayList()
            val width = frames[0].size
            val mean = DoubleArray(width)
            for (f in frames) for (i in 0 until width) mean[i] += f[i]
            for (i in 0 until width) mean[i] /= frames.size
            val out = ArrayList<FloatArray>(frames.size)
            for (f in frames) {
                out.add(FloatArray(width) { i -> (f[i] - mean[i]).toFloat() })
            }
            return out
        }

        /** First-order finite-difference derivative `(next - prev) / 2`, edge-clamped. */
        fun derivative(frames: List<FloatArray>): List<FloatArray> {
            val n = frames.size
            if (n == 0) return emptyList()
            val width = frames[0].size
            return List(n) { t ->
                val prev = frames[(t - 1).coerceAtLeast(0)]
                val next = frames[(t + 1).coerceAtMost(n - 1)]
                FloatArray(width) { i -> (next[i] - prev[i]) / 2f }
            }
        }

        /**
         * Concatenate static | Δ [| ΔΔ] per frame — never summed (LIVE BUG #1). Output width is
         * `width * 2` for Δ only, `width * 3` with acceleration.
         */
        fun withDeltas(frames: List<FloatArray>, includeAcceleration: Boolean): ArrayList<FloatArray> {
            val n = frames.size
            if (n == 0) return ArrayList()
            val width = frames[0].size
            val delta = derivative(frames)
            val accel = if (includeAcceleration) derivative(delta) else null
            val blocks = if (includeAcceleration) 3 else 2
            val out = ArrayList<FloatArray>(n)
            for (t in 0 until n) {
                val combined = FloatArray(width * blocks)
                for (i in 0 until width) {
                    combined[i] = frames[t][i]
                    combined[width + i] = delta[t][i]
                    if (accel != null) combined[2 * width + i] = accel[t][i]
                }
                out.add(combined)
            }
            return out
        }
    }
}
