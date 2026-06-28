package com.speechangel.core.model

/**
 * Core domain model for SpeechAngel.
 *
 * The recognizer is *language-independent by construction*: it never models phonemes or words.
 * It compares the acoustic feature trajectory of the user's own enrolled samples ([Template])
 * against an incoming utterance. See `research/01_conceptual_findings.md` (Path C).
 */

/** A mono PCM buffer normalised to the range [-1, 1]. */
class AudioSamples(val samples: FloatArray, val sampleRateHz: Int) {
    val durationMs: Long get() = if (sampleRateHz <= 0) 0 else samples.size * 1000L / sampleRateHz
    val isEmpty: Boolean get() = samples.isEmpty()

    companion object {
        fun concat(frames: Collection<AudioSamples>): AudioSamples {
            require(frames.isNotEmpty())
            val out = FloatArray(frames.sumOf { it.samples.size })
            var off = 0
            for (f in frames) {
                f.samples.copyInto(out, off)
                off += f.samples.size
            }
            return AudioSamples(out, frames.first().sampleRateHz)
        }
    }
}

/**
 * An ordered sequence of feature frames (e.g. MFCC vectors), frame-major.
 * `frames[t]` is the coefficient vector at time step `t`; every frame has [coefficientCount] values.
 */
class FeatureSequence(val frames: List<FloatArray>) {
    val frameCount: Int get() = frames.size
    val coefficientCount: Int get() = frames.firstOrNull()?.size ?: 0
    val isEmpty: Boolean get() = frames.isEmpty()

    init {
        val width = coefficientCount
        require(frames.all { it.size == width }) { "All feature frames must have equal width ($width)" }
    }
}

/** Stable identifier for a user-defined command. */
@JvmInline
value class CommandId(val value: String) {
    init {
        require(value.isNotBlank()) { "CommandId must not be blank" }
    }
}

/** Stable identifier for a single enrolled template (one recording of one command). */
@JvmInline
value class TemplateId(val value: String) {
    init {
        require(value.isNotBlank()) { "TemplateId must not be blank" }
    }
}

/** Identifier of the deterministic device action a command maps to (resolved in the app layer). */
@JvmInline
value class ActionId(val value: String)

/**
 * The voice condition a template was recorded under. Capturing multiple conditions per command
 * is the primary robustness mechanism against voice drift (illness, fatigue, post-stroke change).
 */
enum class VoiceCondition { NORMAL, TIRED, ILL, OTHER }

/** A user-defined voice command and the deterministic action it triggers. */
data class VoiceCommand(val id: CommandId, val label: String, val action: ActionId)

/** One enrolled acoustic template: the feature trajectory of a single recording of a command. */
data class Template(
    val id: TemplateId,
    val commandId: CommandId,
    val features: FeatureSequence,
    val condition: VoiceCondition = VoiceCondition.NORMAL,
    val createdAtEpochMs: Long = 0L,
)

/** Why an utterance was not matched to any command. */
enum class RejectionReason { BELOW_CONFIDENCE, NO_TEMPLATES, SILENCE, EMPTY_INPUT }

/** Outcome of matching an utterance against the enrolled templates. */
sealed interface RecognitionResult {
    /** A confident match. [confidence] is in [0,1]; [distance] is the raw DTW cost (lower = closer). */
    data class Match(val commandId: CommandId, val templateId: TemplateId, val confidence: Float, val distance: Float) : RecognitionResult

    /** No command cleared its acceptance threshold. */
    data class NoMatch(
        val reason: RejectionReason,
        val bestDistance: Float = Float.POSITIVE_INFINITY,
        val nearestCommandId: CommandId? = null,
    ) : RecognitionResult
}
