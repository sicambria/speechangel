package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test
import java.io.File

/**
 * Pure (no-corpus) coverage for the Picovoice harness plumbing, so `:core:eval:test` exercises the
 * mixer/split logic on every host. The corpus-dependent scoring path is covered by
 * [PicovoiceBenchmarkTest] under `-Dpicovoice.dir`.
 */
class PicovoiceMixerTest {

    private val sr = 16000

    /** A non-silent buffer of [ms] milliseconds so the SNR-active RMS is well-defined. */
    private fun tone(ms: Int, level: Float = 0.4f): AudioSamples =
        AudioSamples(FloatArray(sr * ms / 1000) { if (it % 2 == 0) level else -level }, sr)

    @Test
    fun `mixer weaves keywords in and reports valid intervals`() {
        val keywords = listOf(tone(500), tone(600), tone(400))
        val background = List(20) { tone(700) }
        val noise = listOf(tone(1000))

        val mixed = PicovoiceMixer(snrDb = 10.0, targetBackgroundSeconds = 4.0).mix(keywords, background, noise)

        assertThat(mixed.keywordCount).isEqualTo(3)
        assertThat(mixed.streamSeconds).isGreaterThan(0.0)

        // Intervals are ordered, non-overlapping, in-bounds, and ~ the take duration.
        var prevEnd = 0.0
        mixed.intervals.forEachIndexed { i, iv ->
            assertThat(iv.startSec).isAtLeast(prevEnd)
            assertThat(iv.endSec).isGreaterThan(iv.startSec)
            assertThat(iv.endSec).isAtMost(mixed.streamSeconds + 1e-6)
            val expected = keywords[i].samples.size.toDouble() / sr
            assertThat(iv.endSec - iv.startSec).isWithin(1e-3).of(expected)
            prevEnd = iv.endSec
        }
    }

    @Test
    fun `noise preserves stream length so labels stay valid`() {
        val mixedNoNoise = PicovoiceMixer(targetBackgroundSeconds = 2.0)
            .mix(listOf(tone(500)), List(5) { tone(700) }, emptyList())
        val mixedNoise = PicovoiceMixer(targetBackgroundSeconds = 2.0)
            .mix(listOf(tone(500)), List(5) { tone(700) }, listOf(tone(800)))
        assertThat(mixedNoise.stream.samples.size).isEqualTo(mixedNoNoise.stream.samples.size)
    }

    @Test
    fun `split partitions takes into enroll then held-out`() {
        val takes = (0 until 10).map { File("$it.wav") }
        val kw = PicovoiceCorpus.split("alexa", takes, enrollPerKeyword = 3, maxHeldOut = 4)
        assertThat(kw.enroll).hasSize(3)
        assertThat(kw.heldOut).hasSize(4)
        assertThat(kw.enroll.first().name).isEqualTo("0.wav")
        assertThat(kw.heldOut.first().name).isEqualTo("3.wav")
    }
}
