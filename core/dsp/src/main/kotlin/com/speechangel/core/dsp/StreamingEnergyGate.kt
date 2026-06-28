package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import kotlin.math.sqrt

/**
 * A cheap, stateful energy gate for the always-on Stage-1 path. Unlike [EnergyVad] (which estimates a
 * noise floor as the 10th percentile *within one buffer* and so fails on a short frame that is entirely
 * speech), this keeps a **running** noise-floor estimate across frames and gates on
 * `rms >= max(absoluteRmsFloor, runningFloor * ratioOverNoise)`. The floor only adapts on non-speech
 * frames, so sustained speech cannot drag the floor up to itself.
 */
class StreamingEnergyGate(
    private val absoluteRmsFloor: Float = 1e-3f,
    private val ratioOverNoise: Float = 3.0f,
    private val adaptation: Float = 0.05f,
) {
    private var noiseFloor = absoluteRmsFloor

    /** True if [frame] is (likely) speech. Updates the running noise floor on non-speech frames. */
    fun isSpeech(frame: AudioSamples): Boolean {
        if (frame.isEmpty) return false
        val level = rms(frame.samples)
        val threshold = maxOf(absoluteRmsFloor, noiseFloor * ratioOverNoise)
        val speech = level >= threshold
        if (!speech) noiseFloor = (1 - adaptation) * noiseFloor + adaptation * level
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
