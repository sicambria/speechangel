package com.speechangel.core.eval

import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId

/**
 * Picks per-command acceptance thresholds against an explicit false-accept budget (Phase 2
 * "FAR-budget threshold tuning per command").
 *
 * Budget: aggregate ≤ 1 false-accept per [budgetSecondsPerFalseAccept] (default 1800 s = 30 min) of
 * negative audio — the synthetic operating target. (The real goal is ≤ 0.5 FA/hr, which is not
 * resolvable from short synthetic negatives.) Allotment is split equally across commands with
 * cumulative rounding so the per-command allowances always sum to the total budget. Because a higher
 * per-command threshold monotonically lowers that command's FRR and raises its false-accepts, the
 * "highest threshold within budget" both bounds false-accepts and minimises FRR.
 */
class ThresholdCalibrator(
    private val frontEnd: FeatureFrontEnd,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val budgetSecondsPerFalseAccept: Double = 1800.0,
) {
    data class Calibration(
        val thresholds: Map<CommandId, Float>,
        val budgetFalseAccepts: Int,
        val report: EvalReport,
        /** Negative-audio duration below which the budget cannot resolve even one expected FA. */
        val minMeaningfulNegativeSeconds: Double,
    )

    fun calibrate(corpus: Corpus): Calibration {
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val outcome = evaluator.enroll(corpus)
        val rows = evaluator.distanceTable(corpus, outcome.templates)
        val commands = corpus.commands

        val negatives = rows.filter { it.truth == null }
        val negSeconds = negatives.sumOf { it.durationMs / 1000.0 }
        val budgetFA = maxOf(1, Math.round(negSeconds / budgetSecondsPerFalseAccept).toInt())

        // Equal split with cumulative rounding: allowances sum exactly to budgetFA.
        val n = commands.size.coerceAtLeast(1)
        val allowance = HashMap<CommandId, Int>()
        commands.forEachIndexed { i, c ->
            allowance[c] = Math.floorDiv((i + 1) * budgetFA, n) - Math.floorDiv(i * budgetFA, n)
        }

        // Group each negative by the command that would win it (argmin), collect those distances.
        val negDistByWinner = HashMap<CommandId, MutableList<Float>>()
        for (row in negatives) {
            val winner = row.bestByCommand.minByOrNull { it.value } ?: continue
            negDistByWinner.getOrPut(winner.key) { ArrayList() }.add(winner.value)
        }
        val maxObserved = rows.flatMap { it.bestByCommand.values }.maxOrNull() ?: matcherConfig.defaultAcceptanceThreshold

        val thresholds = HashMap<CommandId, Float>()
        for (c in commands) {
            val dists = (negDistByWinner[c] ?: emptyList()).sorted()
            val allow = allowance[c] ?: 0
            thresholds[c] = if (allow < dists.size) {
                // Just below the (allow+1)-th smallest negative distance → exactly `allow` accepted.
                dists[allow] - EPS
            } else {
                // No negative constrains this command within budget → accept across the observed range.
                maxObserved + 1f
            }
        }

        val report = EvalReport.from(frontEnd.name, rows, thresholds, matcherConfig.defaultAcceptanceThreshold, outcome.failures.size)
        return Calibration(
            thresholds = thresholds,
            budgetFalseAccepts = budgetFA,
            report = report,
            minMeaningfulNegativeSeconds = budgetSecondsPerFalseAccept,
        )
    }

    private companion object {
        const val EPS = 1e-4f
    }
}
