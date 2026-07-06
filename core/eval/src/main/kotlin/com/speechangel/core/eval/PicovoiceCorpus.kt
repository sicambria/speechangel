package com.speechangel.core.eval

import java.io.File

/**
 * Builds SpeechAngel's view of the [Picovoice wake-word-benchmark](https://github.com/Picovoice/wake-word-benchmark)
 * data, provisioned by `scripts/eval/fetch-picovoice-benchmark.sh` into `<root>/prepared/`:
 *
 * ```
 * <root>/prepared/audio/<keyword>/<n>.wav   keyword takes (16 kHz mono s16)
 * <root>/prepared/librispeech/<id>.wav      test-clean utterances (background + OOV negatives)
 * <root>/prepared/noise/<ENV>.wav           DEMAND ch01 per environment
 * ```
 *
 * ## Speaker regime (read this before trusting any number)
 * The benchmark's keyword takes come from **50+ speakers with no speaker labels**, and the engines it
 * was built for (Porcupine/PocketSphinx) are **speaker-independent** universal detectors. SpeechAngel is
 * **speaker-dependent / few-shot** — it matches *the enroller's* voice. So the only runnable framing here
 * is *cross-speaker generalization* (enroll on some speakers' takes, test on others'), a regime the
 * matcher is **not designed for**. The detection miss-rate this yields is therefore an explicitly-labelled
 * **out-of-regime lower bound**, never a headline "SpeechAngel vs engine" number (see [PicovoiceBenchmark]).
 *
 * The **false-alarm rate** on the LibriSpeech+DEMAND background is a different story — whether random
 * background speech false-fires an enrolled template does **not** depend on matching the enroller's voice,
 * so that metric is *in-regime and speaker-agnostic*, and is the headline this harness reports.
 *
 * Filesystem access is confined to [load]; [split] is pure.
 */
object PicovoiceCorpus {

    /** One keyword: enrollment takes (build templates) and held-out takes (streamed as true positives). */
    data class KeywordData(val id: String, val enroll: List<File>, val heldOut: List<File>) {
        val takeCount: Int get() = enroll.size + heldOut.size
    }

    /** The whole prepared benchmark: per-keyword takes + shared background speech + noise clips. */
    data class Data(val root: File, val keywords: List<KeywordData>, val background: List<File>, val noise: List<File>) {
        val ok: Boolean get() = keywords.any { it.enroll.isNotEmpty() && it.heldOut.isNotEmpty() } && background.isNotEmpty()
    }

    private fun wavsIn(dir: File): List<File> = dir.listFiles { f -> f.isFile && f.extension.equals("wav", ignoreCase = true) }
        ?.sortedBy { it.name } ?: emptyList()

    /**
     * Scan `<root>/prepared`. [enrollPerKeyword] takes become enrollment templates; the next
     * [maxHeldOut] become streamed positives (capped so the mixed stream stays affordable). Deterministic:
     * files are name-sorted, first slice enrolls, next slice tests.
     */
    fun load(root: File, enrollPerKeyword: Int = 10, maxHeldOut: Int = 40): Data {
        val prep = File(root, "prepared").takeIf { it.isDirectory } ?: root
        val audioRoot = File(prep, "audio")
        val keywords = (audioRoot.listFiles { f -> f.isDirectory }?.sortedBy { it.name } ?: emptyList())
            .map { d -> split(d.name, wavsIn(d), enrollPerKeyword, maxHeldOut) }
            .filter { it.takeCount > 0 }
        return Data(
            root = root,
            keywords = keywords,
            background = wavsIn(File(prep, "librispeech")),
            noise = wavsIn(File(prep, "noise")),
        )
    }

    /** Pure enroll/held-out split for one keyword's name-sorted takes. */
    fun split(id: String, takes: List<File>, enrollPerKeyword: Int, maxHeldOut: Int): KeywordData {
        val enroll = takes.take(enrollPerKeyword)
        val heldOut = takes.drop(enrollPerKeyword).take(maxHeldOut)
        return KeywordData(id, enroll, heldOut)
    }
}
