package com.speechangel.core.enrollment

import com.speechangel.core.model.AudioSamples

/**
 * Outcome of a batch dictation pass: free text, not a command. Deliberately separate from
 * [BackendResult] — dictation returns a transcript string, so forcing it through the command-oriented
 * [SpeechBackend] (whose result carries a `commandId`) would mean fabricating a command it never
 * produced.
 */
data class DictationResult(val transcript: String, val confidence: Float, val reason: DictationRejection?)

/** Neutral dictation rejection reasons. */
enum class DictationRejection { NO_SPEECH, BACKEND_UNAVAILABLE }

/** What a dictation engine is/needs, so the app can offer it without coupling to one implementation. */
data class DictationCapabilities(val languageDependent: Boolean, val streaming: Boolean)

/**
 * Optional, opt-in batch dictation seam (Phase 3). A whisper.cpp (MIT) backend would implement this to
 * transcribe a captured clip into a text field. It is **never** part of the always-on command path —
 * the deterministic command→action loop runs entirely through [Recognizer]/[SpeechBackend] and does not
 * know this interface exists. No native model ships in-repo; [NoopDictationBackend] keeps the seam
 * compiling and reports unavailable.
 */
interface DictationBackend {
    val capabilities: DictationCapabilities

    /** Transcribe a captured (non-streaming) audio clip into text. */
    fun transcribe(audio: AudioSamples): DictationResult
}

/** Placeholder dictation backend: no model bundled. Always reports unavailable. */
class NoopDictationBackend : DictationBackend {
    override val capabilities = DictationCapabilities(languageDependent = true, streaming = false)
    override fun transcribe(audio: AudioSamples): DictationResult =
        DictationResult(transcript = "", confidence = 0f, reason = DictationRejection.BACKEND_UNAVAILABLE)
}
