package com.speechangel.core.enrollment

import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.RejectionReason
import com.speechangel.core.model.Template

/**
 * The Stage-2 recognition pipeline: VAD endpointing → MFCC feature extraction → template matching.
 * Pure and deterministic so it can be unit-tested end to end without a device.
 */
class Recognizer(
    private val mfcc: MfccExtractor,
    private val vad: Vad,
    private val matcher: TemplateMatcher,
) {
    fun recognize(
        audio: AudioSamples,
        templates: List<Template>,
        perCommandThresholds: Map<CommandId, Float> = emptyMap(),
    ): RecognitionResult {
        if (audio.isEmpty) return RecognitionResult.NoMatch(RejectionReason.EMPTY_INPUT)
        val speech = vad.trim(audio)
        if (speech.isEmpty) return RecognitionResult.NoMatch(RejectionReason.SILENCE)
        val features = mfcc.extract(speech)
        if (features.isEmpty) return RecognitionResult.NoMatch(RejectionReason.SILENCE)
        return matcher.match(features, templates, perCommandThresholds)
    }
}
