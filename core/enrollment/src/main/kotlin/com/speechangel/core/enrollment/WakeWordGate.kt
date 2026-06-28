package com.speechangel.core.enrollment

import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.Template

/** Reserved command ids that are never user commands and must be excluded from Stage-2 matching. */
object ReservedCommands {
    val WAKE = CommandId("__wake__")

    /** Stage-2 candidate set: the user's command templates, with reserved (e.g. wake) ones removed. */
    fun commandTemplates(all: List<Template>): List<Template> = all.filter { it.commandId != WAKE }
}

/** Outcome of the Stage-1 wake check. */
sealed interface WakeDecision {
    data class Wake(val distance: Float) : WakeDecision
    data class NoWake(val reason: WakeReason) : WakeDecision
}

enum class WakeReason { NO_WAKE_ENROLLED, NO_SPEECH, BELOW_THRESHOLD }

/**
 * Stage-1 software wake word: matches a captured frame against the *wake* templates only, with a
 * dedicated tighter threshold, and decides Wake/NoWake. It gates Stage-2; it never triggers an action.
 *
 * The frame is assumed to already have passed a cheap energy gate (the running-floor gate, not the
 * per-utterance percentile VAD). Templates are passed in per call — the gate holds no repository.
 */
class WakeWordGate(private val mfcc: MfccExtractor, private val matcher: TemplateMatcher, private val wakeThreshold: Float) {
    fun evaluate(frame: AudioSamples, wakeTemplates: List<Template>): WakeDecision {
        if (wakeTemplates.isEmpty()) return WakeDecision.NoWake(WakeReason.NO_WAKE_ENROLLED)
        val features = mfcc.extract(frame)
        if (features.isEmpty) return WakeDecision.NoWake(WakeReason.NO_SPEECH)
        val wakeId = wakeTemplates.first().commandId
        return when (val r = matcher.match(features, wakeTemplates, mapOf(wakeId to wakeThreshold))) {
            is RecognitionResult.Match -> WakeDecision.Wake(r.distance)
            is RecognitionResult.NoMatch -> WakeDecision.NoWake(WakeReason.BELOW_THRESHOLD)
        }
    }
}
