package com.speechangel.core.eval

import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition

/**
 * A named feature configuration under test in the bake-off. Both the enrolled templates and the query
 * features are extracted with this same [config] so their widths always match (a 13-dim template and a
 * 39-dim query would never match — see [Evaluator]).
 */
data class FeatureFrontEnd(val name: String, val config: MfccConfig)

/** One raw enrollment recording for a command — NOT a pre-extracted template. */
data class EnrollmentSample(val commandId: CommandId, val audio: AudioSamples, val condition: VoiceCondition = VoiceCondition.NORMAL)

/** One labeled test utterance. [truth] == null denotes a negative / out-of-vocabulary sample. */
data class LabeledUtterance(
    val audio: AudioSamples,
    val truth: CommandId?,
    val condition: VoiceCondition = VoiceCondition.NORMAL,
    val source: String = "synthetic",
)

/**
 * A labeled corpus of RAW audio. Storing audio (never pre-extracted [com.speechangel.core.model.Template]s)
 * is what lets a [FeatureFrontEnd] extract both the enrolled templates and the query features with the
 * SAME config — otherwise a cross-front-end run would mismatch widths and reject everything (FRR = 100%).
 */
data class Corpus(val enrollment: List<EnrollmentSample>, val utterances: List<LabeledUtterance>) {
    /** Distinct commands that have at least one enrollment sample. */
    val commands: List<CommandId> get() = enrollment.map { it.commandId }.distinct()
}
