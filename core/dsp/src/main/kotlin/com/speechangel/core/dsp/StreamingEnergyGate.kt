package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import kotlin.math.sqrt

/**
 * A cheap, stateful energy gate for the always-on Stage-1 path. Unlike [EnergyVad] (which estimates a
 * noise floor as the 10th percentile *within one buffer* and so fails on a short frame that is entirely
 * speech), this keeps a **running** noise-floor estimate across frames and gates on
 * `rms >= max(absoluteRmsFloor, runningFloor * ratioOverNoise)`.
 *
 * The floor adapts at the normal [adaptation] rate on non-speech frames, and at a heavily-damped
 * [speechLeak] rate (≪ [adaptation]) on speech frames. The asymmetry preserves the original intent —
 * a brief command (~1–2 s) barely moves the floor — while letting *sustained* loud ambient noise
 * re-baseline it over tens of seconds, instead of latching the gate permanently open (audit
 * 2026-06-28_streaming-energy-gate-stuck-floor).
 */
class StreamingEnergyGate(
    private val absoluteRmsFloor: Float = 1e-3f,
    private val ratioOverNoise: Float = 3.0f,
    private val adaptation: Float = 0.05f,
    private val speechLeak: Float = 0.002f,
) {
    private var noiseFloor = absoluteRmsFloor

    /**
     * True if [frame] is (likely) speech. Adapts the running noise floor toward the frame level on
     * every frame: at [adaptation] when non-speech, at the much slower [speechLeak] when speech.
     */
    fun isSpeech(frame: AudioSamples): Boolean {
        if (frame.isEmpty) return false
        val level = rms(frame.samples)
        val threshold = maxOf(absoluteRmsFloor, noiseFloor * ratioOverNoise)
        val speech = level >= threshold
        val rate = if (speech) speechLeak else adaptation
        noiseFloor = (1 - rate) * noiseFloor + rate * level
        return speech
    }

    /** Current running noise-floor estimate (exposed for tuning/tests). */
    fun noiseFloor(): Float = noiseFloor

    private companion object {
        fun rms(samples: FloatArray): Float {
            if (samples.isEmpty()) return 0f
            var sum = 0.0
            for (s in samples) sum += s.toDouble() * s
            return sqrt(sum / samples.size).toFloat()
        }
    }
}
