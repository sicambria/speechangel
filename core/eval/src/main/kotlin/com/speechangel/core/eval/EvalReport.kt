package com.speechangel.core.eval

import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition

/**
 * The outcome of evaluating a corpus through one front-end at one threshold operating point.
 *
 * Accuracy is reported as **FRR** plus a **false-accept count with the negative-audio duration that
 * produced it** — never a bare percentage. [farPerHour] is derived but is only meaningful when
 * [negativeAudioSeconds] is large; the renderer states the caveat.
 *
 * Convention: a positive whose top command is wrong (a *substitution*) is counted as a false reject
 * (the command was not correctly recognised); the [confusion] map preserves the detail.
 */
data class EvalReport(
    val frontEndName: String,
    val positives: Int,
    val negatives: Int,
    val falseRejects: Int,
    val falseAccepts: Int,
    val negativeAudioSeconds: Double,
    val perCommandFrr: Map<CommandId, Double>,
    val perConditionFrr: Map<VoiceCondition, Double>,
    val confusion: Map<String, Map<String, Int>>,
    val enrollmentFailures: Int,
    val synthetic: Boolean = true,
) {
    val frr: Double get() = if (positives > 0) falseRejects.toDouble() / positives else 0.0

    /** False accepts per hour — only meaningful with enough negative audio; see [negativeAudioSeconds]. */
    val farPerHour: Double get() = if (negativeAudioSeconds > 0) falseAccepts / (negativeAudioSeconds / 3600.0) else 0.0

    fun render(): String = buildString {
        if (synthetic) {
            appendLine("> **SYNTHETIC — illustrative only, NOT the real measurement.** Real FRR/FAR")
            appendLine("> requires a labeled corpus of real (incl. dysarthric) voices; see")
            appendLine("> `docs/testing/frr-far-report-template.md`.")
            appendLine()
        }
        appendLine("# Recognizer evaluation — front-end `$frontEndName`")
        appendLine()
        appendLine("- Positives: $positives · Negatives: $negatives · Enrollment failures: $enrollmentFailures")
        appendLine("- **FRR: ${pct(frr)}** ($falseRejects/$positives rejected or substituted)")
        appendLine(
            "- **False accepts: $falseAccepts** over ${"%.1f".format(negativeAudioSeconds)} s of negative audio " +
                "(≈ ${"%.2f".format(farPerHour)}/hr — only meaningful with sufficient negative audio)",
        )
        appendLine()
        appendLine("## FRR by command")
        for ((c, v) in perCommandFrr) appendLine("- `${c.value}`: ${pct(v)}")
        appendLine()
        appendLine("## FRR by voice condition")
        for ((c, v) in perConditionFrr) appendLine("- $c: ${pct(v)}")
    }

    companion object {
        private fun pct(v: Double) = "%.1f%%".format(v * 100)

        fun from(
            frontEndName: String,
            rows: List<DistanceRow>,
            thresholds: Map<CommandId, Float>,
            defaultThreshold: Float,
            enrollmentFailures: Int,
        ): EvalReport {
            val positives = rows.filter { it.truth != null }
            val negatives = rows.filter { it.truth == null }

            var falseRejects = 0
            var falseAccepts = 0
            val perCmdTotal = HashMap<CommandId, Int>()
            val perCmdFR = HashMap<CommandId, Int>()
            val perCondTotal = HashMap<VoiceCondition, Int>()
            val perCondFR = HashMap<VoiceCondition, Int>()
            val confusion = HashMap<String, HashMap<String, Int>>()

            for (row in positives) {
                val truth = row.truth!!
                val predicted = row.decide(thresholds, defaultThreshold)
                perCmdTotal.merge(truth, 1, Int::plus)
                perCondTotal.merge(row.condition, 1, Int::plus)
                val correct = predicted == truth
                if (!correct) {
                    falseRejects++
                    perCmdFR.merge(truth, 1, Int::plus)
                    perCondFR.merge(row.condition, 1, Int::plus)
                }
                bump(confusion, truth.value, predicted?.value ?: "REJECT")
            }
            for (row in negatives) {
                val predicted = row.decide(thresholds, defaultThreshold)
                if (predicted != null) falseAccepts++
                bump(confusion, "OOV", predicted?.value ?: "REJECT")
            }

            val perCommandFrr = perCmdTotal.mapValues { (c, total) -> (perCmdFR[c] ?: 0).toDouble() / total }
            val perConditionFrr = perCondTotal.mapValues { (c, total) -> (perCondFR[c] ?: 0).toDouble() / total }
            val negSeconds = negatives.sumOf { it.durationMs / 1000.0 }

            return EvalReport(
                frontEndName = frontEndName,
                positives = positives.size,
                negatives = negatives.size,
                falseRejects = falseRejects,
                falseAccepts = falseAccepts,
                negativeAudioSeconds = negSeconds,
                perCommandFrr = perCommandFrr,
                perConditionFrr = perConditionFrr,
                confusion = confusion.mapValues { it.value.toMap() },
                enrollmentFailures = enrollmentFailures,
            )
        }

        private fun bump(m: HashMap<String, HashMap<String, Int>>, truth: String, predicted: String) {
            m.getOrPut(truth) { HashMap() }.merge(predicted, 1, Int::plus)
        }
    }
}
