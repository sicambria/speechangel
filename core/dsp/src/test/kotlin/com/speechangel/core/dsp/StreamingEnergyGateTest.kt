package com.speechangel.core.dsp

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sin

class StreamingEnergyGateTest {

    private fun tone(amp: Float, n: Int = 1600): AudioSamples =
        AudioSamples(FloatArray(n) { (amp * sin(2.0 * PI * 440.0 * it / 16_000)).toFloat() }, 16_000)

    private fun silence(n: Int = 1600): AudioSamples = AudioSamples(FloatArray(n), 16_000)

    @Test
    fun `an all-speech frame passes the gate`() {
        // The percentile EnergyVad would FAIL this (whole frame is speech, so its noise floor = speech).
        assertThat(StreamingEnergyGate().isSpeech(tone(0.3f))).isTrue()
    }

    @Test
    fun `a quiet frame does not pass`() {
        assertThat(StreamingEnergyGate().isSpeech(silence())).isFalse()
    }

    @Test
    fun `the running floor adapts on quiet frames but still admits speech`() {
        val gate = StreamingEnergyGate()
        repeat(10) { gate.isSpeech(silence()) }
        assertThat(gate.noiseFloor()).isLessThan(0.05f)
        assertThat(gate.isSpeech(tone(0.3f))).isTrue()
    }
}
