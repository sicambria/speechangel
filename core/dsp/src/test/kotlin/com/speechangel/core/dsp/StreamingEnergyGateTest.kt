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

    @Test
    fun `a brief command does not ratchet the floor up to reject speech`() {
        // The speech-side leak is heavily damped: across a ~1.5 s command (15 frames) the floor stays
        // far below the command's own level, so the gate keeps admitting speech and never latches
        // closed on the speaker — preserving the original "speech can't drag the floor up to itself".
        val gate = StreamingEnergyGate()
        repeat(15) { gate.isSpeech(tone(0.3f)) }
        // tone(0.3) RMS ≈ 0.212; after a brief command the floor is still a small fraction of it.
        assertThat(gate.noiseFloor()).isLessThan(0.02f)
        assertThat(gate.isSpeech(tone(0.3f))).isTrue()
    }

    @Test
    fun `sustained loud ambient noise eventually re-baselines the floor`() {
        // Regression for audit 2026-06-28_streaming-energy-gate-stuck-floor: without the speech-side
        // leak the floor would latch and the gate would admit forever. With it, a long stretch of
        // sustained loud input raises the floor toward that level.
        val gate = StreamingEnergyGate()
        repeat(2000) { gate.isSpeech(tone(0.3f)) }
        // tone(0.3) RMS ≈ 0.212; the floor must have climbed well above its 1e-3 start.
        assertThat(gate.noiseFloor()).isGreaterThan(0.1f)
    }
}
