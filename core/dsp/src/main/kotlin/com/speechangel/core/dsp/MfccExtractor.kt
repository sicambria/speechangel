package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.FeatureSequence
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

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
    val applyCmvn: Boolean = true,
    val includeDeltas: Boolean = false,
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
        val frames = ArrayList<FloatArray>()
        var start = 0
        while (start + config.frameLength <= signal.size) {
            frames.add(mfccOfFrame(signal, start))
            start += config.frameShift
        }
        var sequence = frames
        if (config.applyCmvn) sequence = cmvn(sequence)
        if (config.includeDeltas) sequence = withDeltas(sequence)
        return FeatureSequence(sequence)
    }

    private fun mfccOfFrame(signal: FloatArray, start: Int): FloatArray {
        val windowed = FloatArray(config.frameLength)
        for (i in 0 until config.frameLength) {
            windowed[i] = signal[start + i] * hamming[i]
        }
        val power = Fft.powerSpectrum(windowed, fftSize)
        val logMel = melBank.logEnergies(power)
        return dct(logMel, config.numCoefficients).also { applyLifter(it) }
    }

    private fun applyLifter(coeffs: FloatArray) {
        for (k in coeffs.indices) coeffs[k] *= lifter[k]
    }

    private companion object {
        fun hammingWindow(n: Int): FloatArray =
            FloatArray(n) { i -> (0.54 - 0.46 * cos(2.0 * PI * i / (n - 1))).toFloat() }

        fun cepstralLifter(numCoeffs: Int, lifter: Int): FloatArray =
            if (lifter <= 0) {
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

        fun cmvn(frames: List<FloatArray>): ArrayList<FloatArray> {
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

        fun withDeltas(frames: List<FloatArray>): ArrayList<FloatArray> {
            val n = frames.size
            if (n == 0) return ArrayList()
            val width = frames[0].size
            val out = ArrayList<FloatArray>(n)
            for (t in 0 until n) {
                val prev = frames[(t - 1).coerceAtLeast(0)]
                val next = frames[(t + 1).coerceAtMost(n - 1)]
                val combined = FloatArray(width * 2)
                for (i in 0 until width) {
                    combined[i] = frames[t][i]
                    combined[width + i] = (next[i] - prev[i]) / 2f
                }
                out.add(combined)
            }
            return out
        }
    }
}
