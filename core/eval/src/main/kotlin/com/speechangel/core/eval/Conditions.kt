package com.speechangel.core.eval

import com.speechangel.core.model.AudioSamples

/**
 * A named simulated acoustic condition: a deterministic transform of a query's raw audio. The seed for
 * any randomised step is derived from the utterance's own content ([seedOf]) so the same utterance always
 * gets the same realization (reproducible) while different utterances get different noise (realistic).
 *
 * **Honesty:** applying these to real TORGO speech is a *simulated channel* — a controlled robustness
 * probe, NOT a field far-field recording. Reports built on it carry that banner.
 */
data class Condition(val name: String, val transform: (AudioSamples) -> AudioSamples)

object Conditions {

    /** A stable per-utterance seed from its content (length + a few samples) — no global RNG. */
    fun seedOf(a: AudioSamples): Long {
        var h = 1125899906842597L + a.samples.size
        val step = (a.samples.size / 17).coerceAtLeast(1)
        var i = 0
        while (i < a.samples.size) {
            h = 31 * h + java.lang.Float.floatToIntBits(a.samples[i]).toLong()
            i += step
        }
        return h
    }

    /** `CLEAN` is the identity transform — the regression anchor (its row must reproduce the headline). */
    val CLEAN = Condition("clean") { it }

    /**
     * The standard grid: additive white noise at 20/10/5 dB SNR, small/medium room reverb, a telephone
     * band-limit, and a combined "living room" (mild reverb + 15 dB noise + a small-speaker band). Every
     * randomised step is seeded from the utterance content.
     */
    val standard: List<Condition> = listOf(
        CLEAN,
        Condition("noise_20dB") { a -> AudioAugment.addWhiteNoise(a, 20.0, seedOf(a)) },
        Condition("noise_10dB") { a -> AudioAugment.addWhiteNoise(a, 10.0, seedOf(a)) },
        Condition("noise_5dB") { a -> AudioAugment.addWhiteNoise(a, 5.0, seedOf(a)) },
        Condition("reverb_small") { a -> AudioAugment.reverb(a, rt60Ms = 250, mix = 0.25) },
        Condition("reverb_medium") { a -> AudioAugment.reverb(a, rt60Ms = 500, mix = 0.35) },
        Condition("bandlimit_tel") { a -> AudioAugment.bandLimit(a, lowHz = 300.0, highHz = 3400.0) },
        Condition("living_room") { a ->
            val noisy = AudioAugment.addWhiteNoise(a, 15.0, seedOf(a))
            val reverbed = AudioAugment.reverb(noisy, rt60Ms = 300, mix = 0.25)
            AudioAugment.bandLimit(reverbed, lowHz = 150.0, highHz = 6000.0)
        },
    )
}
