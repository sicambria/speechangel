package com.speechangel.core.enrollment

import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import kotlin.math.sqrt

/**
 * Query-by-example acoustic encoder (Phase 3, optional enhancement). Maps a variable-length
 * [FeatureSequence] to a fixed-length embedding so a few enrolled examples per command can be matched
 * by embedding similarity — the arXiv 2403.07802-style profile (~4 samples/class, ~24k params, <4 kB,
 * on-device). Its encoder is trained on **normal speech**, so QbE is a configurable enhancement for
 * milder impairment, **never** the default matcher (the raw-feature MFCC-DTW template engine stays the
 * default — safest for severe impairment). No trained encoder ships in-repo; [NoopQbeEncoder] keeps the
 * seam compiling and reports `available = false`.
 */
interface QbeEncoder {
    /** False until a real trained encoder is supplied; callers must fall back to the template engine. */
    val available: Boolean

    /** Embedding width; 0 when unavailable. */
    val dimensions: Int

    /** Encode one feature sequence into a fixed-length embedding (length == [dimensions]). */
    fun encode(features: FeatureSequence): FloatArray
}

/** Placeholder encoder: no model bundled. Always unavailable; [encode] yields an empty embedding. */
class NoopQbeEncoder : QbeEncoder {
    override val available: Boolean = false
    override val dimensions: Int = 0
    override fun encode(features: FeatureSequence): FloatArray = FloatArray(0)
}

/**
 * Few-shot QbE backend: classifies an utterance against per-command **prototype** embeddings (the mean
 * of that command's enrolled example embeddings) by cosine similarity, with an OOV reject below
 * [acceptSimilarity]. Maps to the neutral [BackendResult] — it never touches the template engine. When
 * the encoder is unavailable (the current state — no model shipped) it reports `BACKEND_UNAVAILABLE`,
 * which is exactly what makes it safe to leave wired but dormant.
 */
class QbeSpeechBackend(
    private val encoder: QbeEncoder,
    private val mfcc: MfccExtractor,
    private val vad: Vad,
    private val prototypes: Map<CommandId, FloatArray>,
    private val acceptSimilarity: Float = DEFAULT_ACCEPT_SIMILARITY,
) : SpeechBackend {

    override val capabilities = BackendCapabilities(needsEnrollment = true, languageDependent = false)

    /** True only when a real encoder is present and at least one command prototype is enrolled. */
    val available: Boolean get() = encoder.available && prototypes.isNotEmpty()

    override fun recognize(audio: AudioSamples): BackendResult {
        if (!available) return BackendResult(null, 0f, BackendRejection.BACKEND_UNAVAILABLE)
        if (audio.isEmpty) return BackendResult(null, 0f, BackendRejection.NO_SPEECH)
        val speech = vad.trim(audio)
        if (speech.isEmpty) return BackendResult(null, 0f, BackendRejection.NO_SPEECH)
        val features = mfcc.extract(speech)
        if (features.isEmpty) return BackendResult(null, 0f, BackendRejection.NO_SPEECH)

        val embedding = normalize(encoder.encode(features))
        var bestCommand: CommandId? = null
        var bestSimilarity = Float.NEGATIVE_INFINITY
        for ((command, prototype) in prototypes) {
            val sim = cosine(embedding, prototype)
            if (sim > bestSimilarity) {
                bestSimilarity = sim
                bestCommand = command
            }
        }
        val confidence = ((bestSimilarity + 1f) / 2f).coerceIn(0f, 1f)
        return if (bestCommand != null && bestSimilarity >= acceptSimilarity) {
            BackendResult(bestCommand, confidence, null)
        } else {
            BackendResult(null, confidence, BackendRejection.LOW_CONFIDENCE)
        }
    }

    companion object {
        const val DEFAULT_ACCEPT_SIMILARITY: Float = 0.6f

        /**
         * Build few-shot prototypes: for each command, the L2-normalised mean of its example
         * embeddings. Examples with no detectable speech are skipped; a command with no usable example
         * is omitted from the returned map.
         */
        fun enroll(
            encoder: QbeEncoder,
            mfcc: MfccExtractor,
            vad: Vad,
            examples: Map<CommandId, List<AudioSamples>>,
        ): Map<CommandId, FloatArray> {
            if (!encoder.available) return emptyMap()
            val out = LinkedHashMap<CommandId, FloatArray>()
            for ((command, samples) in examples) {
                val embeddings = samples.mapNotNull { embedOrNull(encoder, mfcc, vad, it) }
                meanNormalized(embeddings)?.let { out[command] = it }
            }
            return out
        }

        private fun embedOrNull(encoder: QbeEncoder, mfcc: MfccExtractor, vad: Vad, audio: AudioSamples): FloatArray? {
            if (audio.isEmpty) return null
            val speech = vad.trim(audio)
            if (speech.isEmpty) return null
            val features = mfcc.extract(speech)
            if (features.isEmpty) return null
            return normalize(encoder.encode(features))
        }

        private fun meanNormalized(embeddings: List<FloatArray>): FloatArray? {
            if (embeddings.isEmpty()) return null
            val dim = embeddings.first().size
            if (dim == 0) return null
            val acc = FloatArray(dim)
            for (e in embeddings) for (i in 0 until dim) acc[i] += e[i]
            for (i in 0 until dim) acc[i] /= embeddings.size
            return normalize(acc)
        }

        private fun normalize(v: FloatArray): FloatArray {
            var norm = 0.0
            for (x in v) norm += x.toDouble() * x
            norm = sqrt(norm)
            if (norm == 0.0) return v
            return FloatArray(v.size) { (v[it] / norm).toFloat() }
        }

        private fun cosine(a: FloatArray, b: FloatArray): Float {
            if (a.isEmpty() || b.isEmpty() || a.size != b.size) return -1f
            var dot = 0.0
            for (i in a.indices) dot += a[i].toDouble() * b[i]
            return dot.toFloat() // both inputs are pre-normalised, so dot == cosine
        }
    }
}

/** Which recognition backend the app is configured to use. Default is always [TEMPLATE]. */
enum class BackendChoice { TEMPLATE, QBE }

/**
 * Pure backend-selection logic, unit-testable in isolation. QbE is used only when it is explicitly
 * chosen **and** actually usable ([QbeSpeechBackend.available]); otherwise the speaker-dependent
 * template engine is returned. This is why the seam can be wired but stays dormant until a real
 * encoder exists — with [NoopQbeEncoder] the QbE branch is never selected.
 */
object SpeechBackendSelector {
    fun select(choice: BackendChoice, templateBackend: SpeechBackend, qbeBackend: QbeSpeechBackend?): SpeechBackend =
        if (choice == BackendChoice.QBE && qbeBackend != null && qbeBackend.available) qbeBackend else templateBackend
}
