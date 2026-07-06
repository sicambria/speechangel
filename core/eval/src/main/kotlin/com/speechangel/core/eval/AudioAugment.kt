package com.speechangel.core.eval

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.Vad
import com.speechangel.core.model.AudioSamples
import kotlin.math.PI
import kotlin.math.sqrt
import kotlin.math.tanh

/**
 * Deterministic, pure audio degradation for the realistic-condition simulation harness.
 *
 * Every function is a pure transform of [AudioSamples] → [AudioSamples] (no clock, no global RNG); the
 * only randomness is a caller-supplied `seed` feeding a local [Lcg], so a condition applied twice to the
 * same utterance is byte-identical (required by the `CLEAN`-row regression guard and by
 * `:core:eval:test`).
 *
 * **Honesty:** these apply a *simulated channel* to REAL speech — additive noise, room reverberation,
 * mic/band-limiting. That is a controlled robustness probe, **not** a field far-field recording. All
 * reports built on it carry the "real speech, simulated channel" banner. See
 * `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`.
 */
object AudioAugment {

    /** A tiny deterministic linear-congruential generator (glibc constants) → reproducible noise. */
    class Lcg(seed: Long) {
        private var state = (seed xor 0x5DEECE66DL) and 0xFFFFFFFFFFFFL

        /** Next float in [-1, 1). */
        fun nextBipolar(): Float {
            state = (state * 0x5DEECE66DL + 0xBL) and 0xFFFFFFFFFFFFL
            return ((state ushr 16).toInt() / 2.147483648E9).toFloat() // top 32 bits → [-1,1)
        }
    }

    /** RMS of [s] over its VAD-active region (or the whole buffer if the VAD finds nothing). */
    private fun activeRms(s: AudioSamples, vad: Vad): Double {
        val speech = vad.trim(s).takeIf { !it.isEmpty }?.samples ?: s.samples
        if (speech.isEmpty()) return 0.0
        var sum = 0.0
        for (v in speech) sum += v.toDouble() * v
        return sqrt(sum / speech.size)
    }

    private fun rms(a: FloatArray): Double {
        if (a.isEmpty()) return 0.0
        var sum = 0.0
        for (v in a) sum += v.toDouble() * v
        return sqrt(sum / a.size)
    }

    /** White noise, unit-ish amplitude, length [n], deterministic from [seed]. */
    fun whiteNoise(n: Int, seed: Long): FloatArray {
        val rng = Lcg(seed)
        return FloatArray(n) { rng.nextBipolar() }
    }

    /**
     * Add [noise] to [signal] scaled so the resulting **signal-to-noise ratio over the speech-active
     * region** equals [snrDb]. Noise is tiled/truncated to the signal length. The SNR is measured on the
     * VAD-active region so leading/trailing silence does not deflate it.
     */
    fun addNoise(signal: AudioSamples, noise: FloatArray, snrDb: Double, vad: Vad = EnergyVad()): AudioSamples {
        if (signal.isEmpty || noise.isEmpty()) return signal
        val sigRms = activeRms(signal, vad)
        if (sigRms <= 0.0) return signal
        val noiseRms = rms(noise)
        if (noiseRms <= 0.0) return signal
        // target noise RMS so that 20*log10(sigRms/targetNoiseRms) == snrDb
        val targetNoiseRms = sigRms / Math.pow(10.0, snrDb / 20.0)
        val scale = (targetNoiseRms / noiseRms).toFloat()
        val out = FloatArray(signal.samples.size)
        for (i in signal.samples.indices) {
            out[i] = signal.samples[i] + scale * noise[i % noise.size]
        }
        return AudioSamples(out, signal.sampleRateHz)
    }

    /** Convenience: add fresh white noise at [snrDb], deterministic from [seed]. */
    fun addWhiteNoise(signal: AudioSamples, snrDb: Double, seed: Long, vad: Vad = EnergyVad()): AudioSamples =
        addNoise(signal, whiteNoise(signal.samples.size, seed), snrDb, vad)

    /**
     * O(n) Schroeder reverberator: 4 parallel feedback comb filters into 2 series all-pass filters.
     * [rt60Ms] sets the comb feedback so the tail decays ~60 dB in that time; [mix] blends dry/wet
     * (0 = dry, 1 = fully wet). Deterministic (no RNG). This is a plausible reverb tail at O(n) cost —
     * chosen over O(n·k) impulse-response convolution so a condition grid over hundreds of utterances is
     * affordable; it is a probe, not a measured room.
     */
    fun reverb(signal: AudioSamples, rt60Ms: Int, mix: Double = 0.3): AudioSamples {
        if (signal.isEmpty || rt60Ms <= 0 || mix <= 0.0) return signal
        val sr = signal.sampleRateHz
        // Classic Schroeder comb delays (ms), mutually prime-ish to avoid flutter.
        val combMs = doubleArrayOf(29.7, 37.1, 41.1, 43.7)
        val allpassMs = doubleArrayOf(5.0, 1.7)
        var wet = signal.samples.copyOf()

        // Parallel combs summed.
        val combOut = FloatArray(wet.size)
        for (dMs in combMs) {
            val d = (sr * dMs / 1000.0).toInt().coerceAtLeast(1)
            // feedback g such that g^(rt60/delay) = 10^(-3)  →  g = 10^(-3*delay/rt60)
            val g = Math.pow(10.0, -3.0 * (d.toDouble() / sr) / (rt60Ms / 1000.0)).toFloat().coerceIn(0f, 0.98f)
            val buf = FloatArray(d)
            var idx = 0
            for (i in wet.indices) {
                val delayed = buf[idx]
                val y = wet[i] + g * delayed
                buf[idx] = y
                combOut[i] += y
                idx = (idx + 1) % d
            }
        }
        for (i in combOut.indices) combOut[i] /= combMs.size
        wet = combOut

        // Series all-pass for diffusion.
        for (dMs in allpassMs) {
            val d = (sr * dMs / 1000.0).toInt().coerceAtLeast(1)
            val g = 0.7f
            val buf = FloatArray(d)
            var idx = 0
            val next = FloatArray(wet.size)
            for (i in wet.indices) {
                val delayed = buf[idx]
                val y = -g * wet[i] + delayed
                buf[idx] = wet[i] + g * y
                next[i] = y
                idx = (idx + 1) % d
            }
            wet = next
        }

        val out = FloatArray(signal.samples.size)
        val dry = 1.0 - mix
        for (i in out.indices) out[i] = (dry * signal.samples[i] + mix * wet[i]).toFloat()
        return AudioSamples(out, signal.sampleRateHz)
    }

    /**
     * Band-pass the signal to [lowHz]..[highHz] with a cascade of a one-pole high-pass and one-pole
     * low-pass (mic / small-speaker / telephone channel colouration). O(n), deterministic.
     */
    fun bandLimit(signal: AudioSamples, lowHz: Double, highHz: Double): AudioSamples {
        if (signal.isEmpty) return signal
        val sr = signal.sampleRateHz.toDouble()
        val x = signal.samples
        val out = FloatArray(x.size)

        // One-pole low-pass coefficient.
        val dtLp = 1.0 / sr
        val rcLp = 1.0 / (2 * PI * highHz.coerceAtMost(sr / 2 - 1))
        val aLp = (dtLp / (rcLp + dtLp)).toFloat()
        // One-pole high-pass coefficient.
        val rcHp = 1.0 / (2 * PI * lowHz.coerceAtLeast(1.0))
        val aHp = (rcHp / (rcHp + dtLp)).toFloat()

        // Low-pass.
        var lp = 0f
        val tmp = FloatArray(x.size)
        for (i in x.indices) {
            lp += aLp * (x[i] - lp)
            tmp[i] = lp
        }
        // High-pass (of the low-passed signal).
        var prevIn = tmp.firstOrNull() ?: 0f
        var hp = 0f
        for (i in tmp.indices) {
            hp = aHp * (hp + tmp[i] - prevIn)
            prevIn = tmp[i]
            out[i] = hp
        }
        return AudioSamples(out, signal.sampleRateHz)
    }

    /** Apply [gainDb] then `tanh` soft-clip at [clipCeil] (AGC / mic overload). Deterministic. */
    fun gainClip(signal: AudioSamples, gainDb: Double, clipCeil: Double = 1.0): AudioSamples {
        if (signal.isEmpty) return signal
        val g = Math.pow(10.0, gainDb / 20.0)
        val out = FloatArray(signal.samples.size)
        for (i in signal.samples.indices) {
            val v = signal.samples[i] * g
            out[i] = (clipCeil * tanh(v / clipCeil)).toFloat()
        }
        return AudioSamples(out, signal.sampleRateHz)
    }
}
