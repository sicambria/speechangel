package com.speechangel.core.eval

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.EnrollmentResult
import com.speechangel.core.matching.Dtw
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.VoiceCondition

/** Per-utterance best DTW distance to each command (min over that command's templates). */
data class DistanceRow(
    val truth: CommandId?,
    val condition: VoiceCondition,
    val durationMs: Long,
    val bestByCommand: Map<CommandId, Float>,
) {
    /** Replicates the matcher: the argmin command is accepted iff its distance ≤ its threshold. */
    fun decide(thresholds: Map<CommandId, Float>, default: Float): CommandId? {
        val winner = bestByCommand.minByOrNull { it.value } ?: return null
        val t = thresholds[winner.key] ?: default
        return if (winner.value <= t) winner.key else null
    }
}

/** A recording that could not be enrolled (e.g. too short / silent) under a given front-end. */
data class EnrollmentFailure(val commandId: CommandId, val condition: VoiceCondition, val reason: String)

data class EnrollmentOutcome(val templates: List<Template>, val failures: List<EnrollmentFailure>)

/**
 * Scores a [Corpus] through one [FeatureFrontEnd]. Both enrollment templates and query features are
 * extracted with the *same* config, so widths always match. Pure + deterministic (no clock/RNG).
 */
class Evaluator(
    val frontEnd: FeatureFrontEnd,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val minSpeechFrames: Int = 8,
    private val vad: Vad = EnergyVad(),
) {
    private val mfcc = MfccExtractor(frontEnd.config)

    /** Enroll templates from the corpus's raw audio using THIS front-end's config. */
    fun enroll(corpus: Corpus): EnrollmentOutcome {
        var counter = 0L
        val enroller = Enroller(
            mfcc = mfcc,
            vad = vad,
            minSpeechFrames = minSpeechFrames,
            idGenerator = { "eval-$counter" },
            clock = { counter },
        )
        val templates = ArrayList<Template>()
        val failures = ArrayList<EnrollmentFailure>()
        for (s in corpus.enrollment) {
            counter++
            when (val r = enroller.enroll(s.audio, s.commandId, s.condition)) {
                is EnrollmentResult.Success -> templates.add(r.template)
                is EnrollmentResult.Rejected -> failures.add(EnrollmentFailure(s.commandId, s.condition, r.reason.name))
            }
        }
        return EnrollmentOutcome(templates, failures)
    }

    /** Best DTW distance per command for each utterance (VAD-trim → MFCC → min DTW over templates). */
    fun distanceTable(corpus: Corpus, templates: List<Template>): List<DistanceRow> {
        val byCommand = templates.groupBy { it.commandId }
        return corpus.utterances.map { u ->
            val speech = vad.trim(u.audio)
            val q = if (speech.isEmpty) null else mfcc.extract(speech).takeIf { !it.isEmpty }
            val best = HashMap<CommandId, Float>()
            if (q != null) {
                for ((cmd, temps) in byCommand) {
                    var min = Float.POSITIVE_INFINITY
                    for (t in temps) {
                        if (t.features.coefficientCount != q.coefficientCount) continue
                        val d = Dtw.distance(q, t.features, matcherConfig.bandRatio).toFloat()
                        if (d < min) min = d
                    }
                    if (min.isFinite()) best[cmd] = min
                }
            }
            DistanceRow(u.truth, u.condition, u.audio.durationMs, best)
        }
    }

    /** Full pass: enroll → distance table → [EvalReport] under the given per-command thresholds. */
    fun evaluate(corpus: Corpus, thresholds: Map<CommandId, Float> = emptyMap(), synthetic: Boolean = true): EvalReport {
        val outcome = enroll(corpus)
        val rows = distanceTable(corpus, outcome.templates)
        return EvalReport.from(
            frontEndName = frontEnd.name,
            rows = rows,
            thresholds = thresholds,
            defaultThreshold = matcherConfig.defaultAcceptanceThreshold,
            enrollmentFailures = outcome.failures.size,
            synthetic = synthetic,
        )
    }
}
