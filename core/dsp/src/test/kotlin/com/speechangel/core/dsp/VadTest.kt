package com.speechangel.core.dsp

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class VadTest {

    private val vad = EnergyVad()

    @Test
    fun `pure silence is rejected`() {
        assertThat(vad.detect(TestSignals.silence(500))).isNull()
    }

    @Test
    fun `a tone burst is located within the silent padding`() {
        // 200 ms silence | 300 ms tone | 200 ms silence, @16 kHz
        val sr = 16_000
        val audio = TestSignals.burst(440.0, leadMs = 200, toneMs = 300, trailMs = 200, sampleRateHz = sr)
        val seg = vad.detect(audio)
        assertThat(seg).isNotNull()
        val toneStart = sr * 200 / 1000
        val toneEnd = sr * 500 / 1000
        // Detected region should overlap the tone and not span the whole buffer.
        assertThat(seg!!.startSample).isLessThan(toneEnd)
        assertThat(seg.endSampleExclusive).isGreaterThan(toneStart)
        assertThat(seg.lengthSamples).isLessThan(audio.samples.size)
    }

    @Test
    fun `trim returns empty for silence`() {
        assertThat(vad.trim(TestSignals.silence(300)).isEmpty).isTrue()
    }

    @Test
    fun `trim shortens a padded utterance`() {
        val audio = TestSignals.burst(440.0, leadMs = 300, toneMs = 200, trailMs = 300)
        val trimmed = vad.trim(audio)
        assertThat(trimmed.isEmpty).isFalse()
        assertThat(trimmed.samples.size).isLessThan(audio.samples.size)
    }
}
