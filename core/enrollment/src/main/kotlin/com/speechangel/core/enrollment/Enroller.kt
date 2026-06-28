package com.speechangel.core.enrollment

import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCondition

/** Result of an enrollment attempt; a quality failure is a first-class, user-facing outcome. */
sealed interface EnrollmentResult {
    data class Success(val template: Template) : EnrollmentResult
    data class Rejected(val reason: QualityIssue) : EnrollmentResult
}

/** Why a recording was not good enough to enroll (surfaced as a friendly thumbs-down in the UI). */
enum class QualityIssue { TOO_SHORT, SILENT, TOO_FEW_FRAMES }

/**
 * Turns a recording of a single command into a [Template]: VAD-trim → MFCC → wrap.
 * Capturing several templates per command, under different [VoiceCondition]s, is the primary
 * defence against voice drift (see `research/01_conceptual_findings.md` §C3).
 */
class Enroller(
    private val mfcc: MfccExtractor,
    private val vad: Vad,
    private val minSpeechFrames: Int = 8,
    private val idGenerator: () -> String,
    private val clock: () -> Long = { 0L },
) {
    fun enroll(audio: AudioSamples, commandId: CommandId, condition: VoiceCondition = VoiceCondition.NORMAL): EnrollmentResult {
        if (audio.isEmpty) return EnrollmentResult.Rejected(QualityIssue.TOO_SHORT)
        val speech = vad.trim(audio)
        if (speech.isEmpty) return EnrollmentResult.Rejected(QualityIssue.SILENT)
        val features = mfcc.extract(speech)
        if (features.frameCount < minSpeechFrames) {
            return EnrollmentResult.Rejected(QualityIssue.TOO_FEW_FRAMES)
        }
        return EnrollmentResult.Success(
            Template(
                id = TemplateId(idGenerator()),
                commandId = commandId,
                features = features,
                condition = condition,
                createdAtEpochMs = clock(),
            ),
        )
    }
}
