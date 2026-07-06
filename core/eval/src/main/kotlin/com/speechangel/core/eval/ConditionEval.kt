package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.matching.MatcherConfig
import java.io.File
import java.util.Locale

/**
 * Runs the held-out TORGO eval across a grid of simulated [Conditions], degrading test **queries** while
 * enrollment templates stay clean (the real deployment asymmetry). For each condition it reports
 * threshold-free rank-1 plus the held-out FRR@FAR under both the shipped baseline decision
 * (`RejectionScore.RawDistance`) and the pre-registered common-mode hypothesis — so "does the winner's
 * gain survive noise/reverb?" is answered by data.
 *
 * **Honesty banner (emitted in [render]):** real speech, *simulated* channel — a controlled robustness
 * probe, NOT a field far-field measurement. See
 * `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`.
 */
class ConditionEval(
    private val frontEnd: FeatureFrontEnd = FeatureFrontEnd("none", MfccConfig(deltaOrder = DeltaOrder.NONE)),
    private val k: Int = 5,
    private val minReps: Int = 2,
    private val mic: String = "wav_headMic",
    private val target: Double = 0.05,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    /** Bound the grid to small-vocabulary (deployment-slice) speakers so the 8× re-scan is affordable. */
    private val maxCommands: Int = 25,
) {
    data class ConditionResult(
        val name: String,
        val rank1: Double,
        val positives: Int,
        val negatives: Int,
        val rawFrr: Double,
        val rawFar: Double,
        val commonModeFrr: Double,
        val commonModeFar: Double,
    )

    fun run(root: File, conditions: List<Condition> = Conditions.standard): List<ConditionResult> {
        val torgo = TorgoEval(frontEnd, k, minReps, mic, matcherConfig)
        val rejection = RejectionEval(target)
        return conditions.map { cond ->
            val bySpeaker = torgo.collectSpeakerRows(root, cond.transform, maxCommands).map { it.id to it.rows }
            val allRows = bySpeaker.flatMap { it.second }
            val positives = allRows.filter { it.truth != null }
            val rank1hits = positives.count { RejectionScore.winnerCommand(it) == it.truth }
            val raw = rejection.pooled(bySpeaker, RejectionScore.RawDistance)
            val cm = rejection.pooled(bySpeaker, RejectionScore.CommonMode)
            ConditionResult(
                name = cond.name,
                rank1 = if (positives.isEmpty()) 0.0 else rank1hits.toDouble() / positives.size,
                positives = positives.size,
                negatives = allRows.count { it.truth == null },
                rawFrr = raw.frr,
                rawFar = raw.far,
                commonModeFrr = cm.frr,
                commonModeFar = cm.far,
            )
        }
    }

    fun render(results: List<ConditionResult>, corpus: String): String = buildString {
        appendLine("## Realistic-condition grid — real speech, SIMULATED channel ($corpus)")
        appendLine()
        appendLine("Queries degraded (enrollment clean) through simulated additive noise / room reverb /")
        appendLine("mic band-limiting. **This is a controlled robustness probe, NOT a field far-field")
        appendLine("recording** — see the plan's honesty gate. Metrics are held-out (leave-one-fold-out),")
        appendLine("FRR read at matched FAR ≤ ${pct(target)}; rank-1 is threshold-free. Bounded to the")
        appendLine("deployment-slice speakers (≤ $maxCommands commands) to keep the 8× re-scan affordable.")
        appendLine()
        appendLine("| Condition | Rank-1 | FRR (raw) | FAR | FRR (common-mode H1) | FAR |")
        appendLine("|---|---:|---:|---:|---:|---:|")
        for (r in results) {
            appendLine(
                "| `${r.name}` | ${pct(r.rank1)} | ${pct(r.rawFrr)} | ${pct(r.rawFar)} | " +
                    "${pct(r.commonModeFrr)} | ${pct(r.commonModeFar)} |",
            )
        }
        appendLine()
        appendLine("The `clean` row reproduces the headline operating point (identity transform). Reading down")
        appendLine("a column shows graceful (or not) degradation as the simulated channel worsens; comparing")
        appendLine("the two FRR columns shows whether the common-mode gain (if any) survives the condition.")
        appendLine()
    }

    private fun pct(v: Double) = String.format(Locale.US, "%.1f%%", v * 100)
}
