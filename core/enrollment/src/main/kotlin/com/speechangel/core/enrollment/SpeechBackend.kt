package com.speechangel.core.enrollment

import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.RejectionReason

/**
 * Backend-neutral recognition outcome. Deliberately carries NO template-centric fields
 * (`templateId`, DTW `distance`) and NO template-centric [RejectionReason] — a future language-dependent
 * backend (e.g. a Vosk grammar) has none of those. DTW detail is preserved separately, only by the
 * template engine (see [TemplateRecognition]).
 */
data class BackendResult(val commandId: CommandId?, val confidence: Float, val reason: BackendRejection?)

/** Neutral rejection reasons shared across backends; each backend maps its native reasons into these. */
enum class BackendRejection { NO_SPEECH, LOW_CONFIDENCE, BACKEND_UNAVAILABLE }

/** What a backend is/needs, so the app can offer modes without coupling to one engine. */
data class BackendCapabilities(val needsEnrollment: Boolean, val languageDependent: Boolean)

/**
 * The optional, additive recognition seam (Phase 2 "Path-A"). The speaker-dependent template engine is
 * the primary backend; a Vosk/sherpa intact-speech mode could implement the same interface WITHOUT
 * depending back into this core. Streaming backends are adapted behind this one-shot call for now.
 */
interface SpeechBackend {
    val capabilities: BackendCapabilities
    fun recognize(audio: AudioSamples): BackendResult
}

/** Template-engine-only detail kept out of the neutral [BackendResult]. */
data class TemplateRecognition(val result: BackendResult, val nearestCommandId: CommandId?, val bestDistance: Float)

/**
 * Adapts the speaker-dependent [Recognizer] to [SpeechBackend]. Stateful by design: it captures the
 * templates + per-command thresholds at construction, so the cross-backend method is a plain
 * `recognize(audio)` (the [Recognizer] itself stays pure).
 */
class TemplateSpeechBackend(
    private val recognizer: Recognizer,
    private val templates: List<com.speechangel.core.model.Template>,
    private val thresholds: Map<CommandId, Float> = emptyMap(),
) : SpeechBackend {

    override val capabilities = BackendCapabilities(needsEnrollment = true, languageDependent = false)

    override fun recognize(audio: AudioSamples): BackendResult = recognizeDetailed(audio).result

    /** Full result including the DTW-specific detail (template-engine only). */
    fun recognizeDetailed(audio: AudioSamples): TemplateRecognition = when (val r = recognizer.recognize(audio, templates, thresholds)) {
        is RecognitionResult.Match ->
            TemplateRecognition(BackendResult(r.commandId, r.confidence, null), r.commandId, r.distance)
        is RecognitionResult.NoMatch ->
            TemplateRecognition(BackendResult(null, 0f, mapReason(r.reason)), r.nearestCommandId, r.bestDistance)
    }

    private fun mapReason(reason: RejectionReason): BackendRejection = when (reason) {
        RejectionReason.SILENCE, RejectionReason.EMPTY_INPUT -> BackendRejection.NO_SPEECH
        RejectionReason.BELOW_CONFIDENCE -> BackendRejection.LOW_CONFIDENCE
        RejectionReason.NO_TEMPLATES -> BackendRejection.BACKEND_UNAVAILABLE
    }
}

/** Placeholder for the not-yet-integrated Path-A backend; always reports unavailable. */
class NoopPathABackend : SpeechBackend {
    override val capabilities = BackendCapabilities(needsEnrollment = false, languageDependent = true)
    override fun recognize(audio: AudioSamples): BackendResult =
        BackendResult(commandId = null, confidence = 0f, reason = BackendRejection.BACKEND_UNAVAILABLE)
}
