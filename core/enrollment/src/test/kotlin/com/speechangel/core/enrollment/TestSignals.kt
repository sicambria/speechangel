package com.speechangel.core.enrollment

import com.speechangel.core.model.AudioSamples
import kotlin.math.PI
import kotlin.math.sin

/** Synthetic utterances for end-to-end recognizer tests (silence-padded so the VAD can endpoint). */
object TestSignals {

    private fun tone(freqHz: Double, durationMs: Int, sampleRateHz: Int, amplitude: Float): FloatArray {
        val count = sampleRateHz * durationMs / 1000
        // Tone + a quieter octave to give MFCC a clearer spectral envelope.
        return FloatArray(count) { i ->
            val t = i.toDouble() / sampleRateHz
            (amplitude * sin(2.0 * PI * freqHz * t) + 0.15f * sin(2.0 * PI * 2 * freqHz * t)).toFloat()
        }
    }

    fun silence(durationMs: Int, sampleRateHz: Int = 16_000) = AudioSamples(FloatArray(sampleRateHz * durationMs / 1000), sampleRateHz)

    /** silence | tone | silence, so the energy VAD has a noise floor to measure against. */
    fun utterance(freqHz: Double, toneMs: Int = 400, sampleRateHz: Int = 16_000, amplitude: Float = 0.3f, padMs: Int = 150): AudioSamples {
        val lead = FloatArray(sampleRateHz * padMs / 1000)
        val mid = tone(freqHz, toneMs, sampleRateHz, amplitude)
        val trail = FloatArray(sampleRateHz * padMs / 1000)
        return AudioSamples(lead + mid + trail, sampleRateHz)
    }
}
