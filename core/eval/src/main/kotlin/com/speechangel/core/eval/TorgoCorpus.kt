package com.speechangel.core.eval

import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import java.io.File

/**
 * Builds a **speaker-dependent** [Corpus] from the TORGO dysarthric-speech corpus for a *real*
 * (non-`SYNTHETIC`) FRR/FAR run through the [Evaluator].
 *
 * ## Why speaker-dependent
 * SpeechAngel is a per-user template matcher — each user teaches it *their own* voice. So enrollment
 * and test utterances are always drawn from the **same speaker**; a cross-speaker split would measure
 * a use case the product does not have and manufacture a false-negative FRR.
 *
 * ## Vocabulary rule (documented so the number is meaningful)
 * TORGO prompts are heterogeneous — bracketed instructions (`[say Ah-P-Eee repeatedly]`), single
 * words (`stick`), words with clarifiers (`tear [as in tear up that paper]`), and full reading-passage
 * sentences. A *command candidate* is the prompt with bracketed clarifiers stripped, reduced to ≤2
 * lexical tokens, excluding TORGO's `xxx` non-scorable marker and picture-description prompts. Within
 * a speaker: words with **≥ [minReps] utterances** become commands; every remaining single-instance
 * word becomes an **OOV negative** (`truth = null`, which the matcher rejects on) for the false-accept
 * measurement.
 *
 * ## Split
 * Real per-speaker repetition depth is thin (many words repeat only 2–3×), so a fixed enroll/test
 * split would waste most data. [folds] does **k-fold within speaker**: every utterance is a test query
 * exactly once and an enrollment template in the other folds — never trained on the utterance it is
 * tested on. Where a word spans multiple sessions the round-robin naturally mixes sessions, matching
 * the enroll-once-use-later product reality.
 *
 * Filesystem access is confined to [scan]; [normalize] and [folds] are pure and unit-tested on a
 * fixture directory without the multi-GB corpus.
 */
object TorgoCorpus {

    /** One head-mic (default) recording: a prompt word with the wav file that realises it. */
    data class Utt(val speaker: String, val word: String, val session: String, val wav: File)

    /** All of one speaker's command words (≥ minReps) and OOV negatives (single-instance words). */
    data class SpeakerData(val id: String, val commands: Map<String, List<Utt>>, val negatives: List<Utt>) {
        val commandCount: Int get() = commands.size
        val positiveCount: Int get() = commands.values.sumOf { it.size }
    }

    /** One cross-validation fold: enroll templates + labeled test queries. */
    data class Fold(val index: Int, val enroll: List<Utt>, val positives: List<Utt>, val negatives: List<Utt>)

    private val WORD = Regex("^[a-z][a-z'-]*( [a-z'-]+)?$")

    /**
     * Reduce a raw prompt to a command-word key, or `null` if it is not a short lexical command
     * candidate (instruction, sentence, non-scorable marker, or picture prompt).
     */
    fun normalize(prompt: String): String? {
        var t = prompt.trim()
        if (t.isEmpty()) return null
        t = t.replace(Regex("\\[[^]]*]"), " ").replace(Regex("\\s+"), " ").trim()
        if (t.isEmpty()) return null // pure instruction like [say Ah-P-Eee repeatedly]
        t = t.lowercase().replace(Regex("[.,;:!?\"]"), "").trim()
        if (t.isEmpty() || t == "xxx") return null
        if (t.contains('/') || t.contains("jpg") || t.contains("input")) return null // picture prompts
        if (t.split(' ').size > 2) return null // reading-passage sentences
        return if (WORD.matches(t)) t else null
    }

    /** Walk a TORGO speaker-set root (dir of `F01`, `F03`, … speaker dirs). */
    fun scan(root: File, mic: String = "wav_headMic", minReps: Int = 2): List<SpeakerData> {
        val speakers = root.listFiles { f -> f.isDirectory && f.name.matches(Regex("[FM]C?\\d\\d")) }
            ?.sortedBy { it.name } ?: emptyList()
        return speakers.map { spkDir ->
            val byWord = LinkedHashMap<String, MutableList<Utt>>()
            val sessions = spkDir.listFiles { f -> f.isDirectory && f.name.startsWith("Session") }
                ?.sortedBy { it.name } ?: emptyList()
            for (ses in sessions) {
                val pdir = File(ses, "prompts")
                val wdir = File(ses, mic)
                if (!pdir.isDirectory || !wdir.isDirectory) continue
                val prompts = pdir.listFiles { f -> f.extension == "txt" }?.sortedBy { it.name } ?: emptyList()
                for (pf in prompts) {
                    val wav = File(wdir, "${pf.nameWithoutExtension}.wav")
                    val word = if (wav.isFile) normalize(pf.readText()) else null
                    if (word != null) {
                        byWord.getOrPut(word) { ArrayList() }.add(Utt(spkDir.name, word, ses.name, wav))
                    }
                }
            }
            val commands = LinkedHashMap<String, List<Utt>>()
            val negatives = ArrayList<Utt>()
            for ((word, utts) in byWord) {
                if (utts.size >= minReps) commands[word] = utts else negatives.addAll(utts)
            }
            SpeakerData(spkDir.name, commands, negatives)
        }
    }

    /**
     * k-fold assignment within one speaker. Each command word's utterances are spread round-robin
     * across folds (index i → fold i mod k), guaranteeing that whenever a word has a test rep in a
     * fold it also has ≥1 enrollment rep in that fold's train set. Negatives are round-robined so each
     * is tested exactly once across all folds. Pure — no filesystem access.
     */
    fun folds(speaker: SpeakerData, k: Int): List<Fold> {
        require(k >= 2) { "k must be >= 2" }
        val positivesByFold = Array(k) { ArrayList<Utt>() }
        val enrollByFold = Array(k) { ArrayList<Utt>() }
        for (utts in speaker.commands.values) {
            utts.forEachIndexed { i, u ->
                val fold = i % k
                positivesByFold[fold].add(u)
                for (f in 0 until k) if (f != fold) enrollByFold[f].add(u)
            }
        }
        val negByFold = Array(k) { ArrayList<Utt>() }
        speaker.negatives.forEachIndexed { i, u -> negByFold[i % k].add(u) }
        return (0 until k).map { f -> Fold(f, enrollByFold[f], positivesByFold[f], negByFold[f]) }
    }

    /** Materialise a [Fold] into a [Corpus], loading each wav via [WavFile]. */
    fun toCorpus(fold: Fold, condition: VoiceCondition = VoiceCondition.NORMAL): Corpus {
        val enrollment = fold.enroll.map { EnrollmentSample(CommandId(it.word), WavFile.read(it.wav), condition) }
        val positives = fold.positives.map {
            LabeledUtterance(WavFile.read(it.wav), CommandId(it.word), condition, source = "torgo:${it.speaker}")
        }
        val negatives = fold.negatives.map {
            LabeledUtterance(WavFile.read(it.wav), truth = null, condition = condition, source = "torgo:${it.speaker}:oov")
        }
        return Corpus(enrollment, positives + negatives)
    }
}
