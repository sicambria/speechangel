package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test
import kotlin.math.PI
import kotlin.math.log10
import kotlin.math.sin
import kotlin.math.sqrt

class AudioAugmentTest {

    private val sr = 16_000

    /** A silence-padded 300 ms tone burst so the VAD finds a speech region (as real utterances have). */
    private fun toneBurst(freq: Double = 300.0, amp: Float = 0.3f): AudioSamples {
        val pad = FloatArray(sr / 5) // 200 ms silence
        val tone = FloatArray(sr * 3 / 10) { i -> (amp * sin(2 * PI * freq * i / sr)).toFloat() }
        val out = FloatArray(pad.size + tone.size + pad.size)
        tone.copyInto(out, pad.size)
        return AudioSamples(out, sr)
    }

    private fun rms(a: FloatArray, from: Int = 0, to: Int = a.size): Double {
        var s = 0.0
        for (i in from until to) s += a[i].toDouble() * a[i]
        return sqrt(s / (to - from))
    }

    /** Realized SNR of [noisy] vs the clean [sig] over the tone region (pad..pad+tone). */
    private fun realizedSnrDb(sig: AudioSamples, noisy: AudioSamples): Double {
        val pad = sr / 5
        val tone = sr * 3 / 10
        val sigActive = rms(sig.samples, pad, pad + tone)
        var ns = 0.0
        for (i in 0 until tone) {
            val d = (noisy.samples[pad + i] - sig.samples[pad + i]).toDouble()
            ns += d * d
        }
        return 20 * log10(sigActive / sqrt(ns / tone))
    }

    @Test
    fun `addNoise hits the requested SNR over the active region`() {
        val sig = toneBurst()
        val target = 10.0
        val realized = realizedSnrDb(sig, AudioAugment.addWhiteNoise(sig, snrDb = target, seed = 42))
        // Within a few dB of target: the VAD active region includes ~80 ms hangover silence each side,
        // so the RMS the scaler sees is slightly below the pure-tone RMS (a known, bounded dilution).
        assertThat(realized).isWithin(3.0).of(target)
    }

    @Test
    fun `higher requested SNR adds less noise (monotonic)`() {
        val sig = toneBurst()
        val quiet = realizedSnrDb(sig, AudioAugment.addWhiteNoise(sig, snrDb = 15.0, seed = 3))
        val loud = realizedSnrDb(sig, AudioAugment.addWhiteNoise(sig, snrDb = 5.0, seed = 3))
        assertThat(quiet).isGreaterThan(loud)
        assertThat(quiet - loud).isWithin(2.0).of(10.0) // ~10 dB request gap → ~10 dB realized gap
    }

    @Test
    fun `augmentation is deterministic for a fixed seed`() {
        val sig = toneBurst()
        val a = AudioAugment.addWhiteNoise(sig, snrDb = 8.0, seed = 7)
        val b = AudioAugment.addWhiteNoise(sig, snrDb = 8.0, seed = 7)
        assertThat(a.samples).isEqualTo(b.samples)
        // Different seed → different realization.
        val c = AudioAugment.addWhiteNoise(sig, snrDb = 8.0, seed = 8)
        assertThat(a.samples).isNotEqualTo(c.samples)
    }

    @Test
    fun `bandLimit attenuates an out-of-band tone far more than an in-band tone`() {
        val inBand = toneBurst(freq = 1000.0, amp = 0.5f)
        val outBand = toneBurst(freq = 60.0, amp = 0.5f) // below a 300 Hz high-pass corner
        val inKept = AudioAugment.bandLimit(inBand, lowHz = 300.0, highHz = 3400.0)
        val outCut = AudioAugment.bandLimit(outBand, lowHz = 300.0, highHz = 3400.0)
        val inRatio = rms(inKept.samples) / rms(inBand.samples)
        val outRatio = rms(outCut.samples) / rms(outBand.samples)
        assertThat(inRatio).isGreaterThan(outRatio * 2)
    }

    @Test
    fun `reverb preserves length and adds a decaying tail beyond the dry signal`() {
        val sig = toneBurst()
        val wet = AudioAugment.reverb(sig, rt60Ms = 400, mix = 0.5)
        assertThat(wet.samples.size).isEqualTo(sig.samples.size)
        // Energy in the trailing silence region rises (a tail exists where the dry signal was ~0).
        val tailStart = sr / 5 + sr * 3 / 10 + sr / 20 // 50 ms after tone ends, into the trailing pad
        val dryTail = rms(sig.samples, tailStart, sig.samples.size)
        val wetTail = rms(wet.samples, tailStart, wet.samples.size)
        assertThat(wetTail).isGreaterThan(dryTail)
    }

    @Test
    fun `gainClip bounds the output and stays deterministic`() {
        val sig = toneBurst(amp = 0.9f)
        val hot = AudioAugment.gainClip(sig, gainDb = 20.0, clipCeil = 1.0)
        assertThat(hot.samples.maxOf { kotlin.math.abs(it) }).isAtMost(1.0f)
        val hot2 = AudioAugment.gainClip(sig, gainDb = 20.0, clipCeil = 1.0)
        assertThat(hot.samples).isEqualTo(hot2.samples)
    }
}
