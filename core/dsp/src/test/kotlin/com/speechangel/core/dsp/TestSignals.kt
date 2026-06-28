package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import kotlin.math.PI
import kotlin.math.sin

/** Synthetic signal generators for deterministic DSP tests. */
object TestSignals {

    fun tone(freqHz: Double, durationMs: Int, sampleRateHz: Int = 16_000, amplitude: Float = 0.3f): AudioSamples {
        val count = sampleRateHz * durationMs / 1000
        val samples = FloatArray(count) { i -> (amplitude * sin(2.0 * PI * freqHz * i / sampleRateHz)).toFloat() }
        return AudioSamples(samples, sampleRateHz)
    }

    fun silence(durationMs: Int, sampleRateHz: Int = 16_000): AudioSamples = AudioSamples(FloatArray(sampleRateHz * durationMs / 1000), sampleRateHz)

    /** silence | tone | silence — for VAD endpointing tests. */
    fun burst(
        freqHz: Double,
        leadMs: Int,
        toneMs: Int,
        trailMs: Int,
        sampleRateHz: Int = 16_000,
    ): AudioSamples {
        val lead = silence(leadMs, sampleRateHz).samples
        val mid = tone(freqHz, toneMs, sampleRateHz).samples
        val trail = silence(trailMs, sampleRateHz).samples
        return AudioSamples(lead + mid + trail, sampleRateHz)
    }
}
