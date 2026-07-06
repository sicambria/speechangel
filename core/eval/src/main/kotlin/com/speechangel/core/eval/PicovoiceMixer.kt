package com.speechangel.core.eval

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.Vad
import com.speechangel.core.model.AudioSamples

/**
 * Reimplements the Picovoice benchmark's `mixer.py` for the JVM harness: weave keyword takes through a
 * LibriSpeech background and mix in DEMAND environmental noise at a fixed SNR, emitting one continuous
 * stream **plus the time-intervals** where a keyword occurs. That single labelled stream is what both
 * SpeechAngel ([PicovoiceBenchmark]) and the same-host PocketSphinx anchor consume, so they are scored on
 * identical bytes.
 *
 * **Faithful, not byte-identical.** Placement is deterministic (fixed order, no global RNG — the
 * `mixer.py` `seed=778` is not reproduced), and the SNR is imposed by scaling noise to the target ratio
 * over the speech-active region ([AudioAugment.addNoise], RMS-based) rather than Picovoice's peak-frame
 * energy formula. The result is the *same construction* at a defined 10 dB SNR, which is why the report
 * treats published engine numbers as a directional anchor, and the same-host PocketSphinx run (on this
 * exact stream) as the apples-to-apples point.
 */
class PicovoiceMixer(
    private val snrDb: Double = 10.0,
    private val targetBackgroundSeconds: Double = 900.0,
    private val vad: Vad = EnergyVad(),
) {
    /** A [startSec, endSec) span in the mixed stream that contains one keyword utterance. */
    data class Interval(val startSec: Double, val endSec: Double)

    data class Mixed(val stream: AudioSamples, val intervals: List<Interval>) {
        val keywordCount: Int get() = intervals.size
        val streamSeconds: Double get() = if (stream.sampleRateHz <= 0) 0.0 else stream.samples.size.toDouble() / stream.sampleRateHz
    }

    /**
     * Interleave [keywordTakes] through [background], targeting [targetBackgroundSeconds] of filler spread
     * evenly across the gaps, then overlay tiled [noise] at [snrDb]. Intervals are recorded on the clean
     * offsets; noise preserves length so they stay valid.
     */
    fun mix(keywordTakes: List<AudioSamples>, background: List<AudioSamples>, noise: List<AudioSamples>): Mixed {
        require(keywordTakes.isNotEmpty()) { "need at least one keyword take" }
        val sr = keywordTakes.first().sampleRateHz
        val perGapSec = if (keywordTakes.isEmpty()) {
            targetBackgroundSeconds
        } else {
            targetBackgroundSeconds / (keywordTakes.size + 1)
        }

        val pieces = ArrayList<AudioSamples>()
        val intervals = ArrayList<Interval>()
        var offset = 0L // running sample offset into the concatenated (pre-noise) stream
        var bgIdx = 0

        fun appendGap() {
            var gapSec = 0.0
            while (gapSec < perGapSec && bgIdx < background.size) {
                val u = background[bgIdx++]
                pieces.add(u)
                offset += u.samples.size
                gapSec += u.samples.size.toDouble() / sr
            }
        }

        for (take in keywordTakes) {
            appendGap()
            val startSec = offset.toDouble() / sr
            pieces.add(take)
            offset += take.samples.size
            intervals.add(Interval(startSec, offset.toDouble() / sr))
        }
        appendGap() // trailing filler so the last keyword is not at the very edge

        var stream = AudioSamples.concat(pieces)
        if (noise.isNotEmpty()) {
            stream = AudioAugment.addNoise(stream, tile(noise, stream.samples.size), snrDb, vad)
        }
        return Mixed(stream, intervals)
    }

    /** Fill exactly [n] samples by cycling through [noise] clips — bounded memory (no giant concat). */
    private fun tile(noise: List<AudioSamples>, n: Int): FloatArray {
        if (noise.isEmpty() || noise.all { it.samples.isEmpty() }) return FloatArray(0)
        val out = FloatArray(n)
        var i = 0
        var clip = 0
        var pos = 0
        while (i < n) {
            val c = noise[clip].samples
            if (pos >= c.size) {
                clip = (clip + 1) % noise.size
                pos = 0
                continue
            }
            out[i++] = c[pos++]
        }
        return out
    }
}
