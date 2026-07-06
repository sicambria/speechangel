package com.speechangel.core.eval

import java.util.Locale
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.sqrt

/**
 * Held-out (leave-one-fold-out) evaluation of an accept/reject decision under a [RejectionScore],
 * matched-FAR (EVAL-002). Thresholds are fit **per speaker per fold** (never pooling distinct
 * vocabularies) and only the final accept/reject **counts** are pooled across speakers for the
 * aggregate — a small tightening over `TorgoEval`'s pooled-threshold aggregate.
 *
 * This is the machinery that adjudicates the pre-registered hypothesis H1 (`RejectionScore.CommonMode`)
 * vs the baseline (`RejectionScore.RawDistance`) via a paired **McNemar** test on the positives, and
 * emits the exploratory full-family table. See
 * `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`.
 */
class RejectionEval(private val target: Double = 0.05) {
    /** Pooled accept/reject counts → FRR (on positives) and realized FAR (on negatives). */
    data class Counts(val posHits: Int, val positives: Int, val faAccepts: Int, val negatives: Int) {
        val frr: Double get() = if (positives == 0) 0.0 else 1.0 - posHits.toDouble() / positives
        val far: Double get() = if (negatives == 0) 0.0 else faAccepts.toDouble() / negatives
        operator fun plus(o: Counts) =
            Counts(posHits + o.posHits, positives + o.positives, faAccepts + o.faAccepts, negatives + o.negatives)
    }

    /** Fraction of a row set's OOV negatives accepted at scalar score-threshold [thr]. */
    private fun farOf(rows: List<DistanceRow>, thr: Float, score: RejectionScore): Double {
        val negs = rows.filter { it.truth == null }
        if (negs.isEmpty()) return 0.0
        val fa = negs.count { r -> RejectionScore.winnerCommand(r) != null && (score.score(r)?.let { it <= thr } ?: false) }
        return fa.toDouble() / negs.size
    }

    /** Largest scalar score-threshold whose TRAIN FAR ≤ [target] (min FRR within budget). */
    private fun fitGlobal(train: List<DistanceRow>, score: RejectionScore): Float {
        val cands = train.mapNotNull { score.score(it) }.filter { it.isFinite() }.sorted().distinct()
        var best = (cands.firstOrNull() ?: 0f) - 1f // reject-all baseline → FAR 0 ≤ target always feasible.
        for (t in cands) if (farOf(train, t, score) <= target) best = t
        return best
    }

    /** Held-out counts for ONE speaker's fold-tagged rows under [score]. */
    fun heldOutSpeaker(rows: List<DistanceRow>, score: RejectionScore): Counts {
        val folds = rows.map { it.fold }.filter { it >= 0 }.toSortedSet()
        var c = Counts(0, 0, 0, 0)
        for (f in folds) {
            val thr = fitGlobal(rows.filter { it.fold != f }, score)
            for (r in rows.filter { it.fold == f }) {
                val w = RejectionScore.winnerCommand(r)
                val accepted = w != null && (score.score(r)?.let { it <= thr } ?: false)
                c = if (r.truth != null) {
                    Counts(c.posHits + if (accepted && w == r.truth) 1 else 0, c.positives + 1, c.faAccepts, c.negatives)
                } else {
                    Counts(c.posHits, c.positives, c.faAccepts + if (accepted) 1 else 0, c.negatives + 1)
                }
            }
        }
        return c
    }

    /**
     * A single in-sample operating threshold on [rows] under [score] (largest with FAR ≤ target). Used to
     * pick the ambient proxy's operating point — labelled in-sample where it is reported.
     */
    fun operatingThreshold(rows: List<DistanceRow>, score: RejectionScore): Float = fitGlobal(rows, score)

    /** Pooled held-out counts across speakers (per-speaker thresholds, pooled counts). */
    fun pooled(rowsBySpeaker: List<Pair<String, List<DistanceRow>>>, score: RejectionScore): Counts =
        rowsBySpeaker.map { heldOutSpeaker(it.second, score) }.fold(Counts(0, 0, 0, 0)) { a, b -> a + b }

    // ---- Pre-registered paired adjudication: McNemar on positives ----

    data class McNemar(
        val baseLabel: String,
        val hypLabel: String,
        val n01: Int, // base wrong, hyp right (hyp improvements)
        val n10: Int, // base right, hyp wrong (hyp regressions)
        val chiSq: Double,
        val pApprox: Double,
        val base: Counts,
        val hyp: Counts,
    ) {
        val significantAt05: Boolean get() = chiSq >= 3.841 // χ²(df=1), p=0.05
        val direction: String get() = when {
            n01 == n10 -> "no net change"
            n01 > n10 -> "hypothesis better"
            else -> "hypothesis worse"
        }
    }

    /**
     * Paired McNemar of [hypothesis] vs [baseline] on the POSITIVE trials, thresholds fit per
     * speaker-per-fold at FAR ≤ [target] for each scorer independently (so realized FARs may differ —
     * both target the same budget; interpret at approximately-matched FAR). A positive is "correct" iff
     * its winner is the true command AND accepted under that scorer's held-out threshold.
     */
    fun mcNemar(rowsBySpeaker: List<Pair<String, List<DistanceRow>>>, baseline: RejectionScore, hypothesis: RejectionScore): McNemar {
        var n01 = 0
        var n10 = 0
        for ((_, rows) in rowsBySpeaker) {
            val folds = rows.map { it.fold }.filter { it >= 0 }.toSortedSet()
            for (f in folds) {
                val train = rows.filter { it.fold != f }
                val thrB = fitGlobal(train, baseline)
                val thrH = fitGlobal(train, hypothesis)
                for (r in rows.filter { it.fold == f && it.truth != null }) {
                    val w = RejectionScore.winnerCommand(r)
                    val baseOk = w == r.truth && (baseline.score(r)?.let { it <= thrB } ?: false)
                    val hypOk = w == r.truth && (hypothesis.score(r)?.let { it <= thrH } ?: false)
                    if (!baseOk && hypOk) n01++
                    if (baseOk && !hypOk) n10++
                }
            }
        }
        val n = n01 + n10
        val chiSq = if (n == 0) 0.0 else (abs(n01 - n10) - 1.0).coerceAtLeast(0.0).let { it * it / n }
        return McNemar(
            baseLabel = baseline.label,
            hypLabel = hypothesis.label,
            n01 = n01,
            n10 = n10,
            chiSq = chiSq,
            pApprox = chiSquarePValueDf1(chiSq),
            base = pooled(rowsBySpeaker, baseline),
            hyp = pooled(rowsBySpeaker, hypothesis),
        )
    }

    // ---- Exploratory full family (NOT banked) ----

    data class ScorerRow(val label: String, val perSpeaker: List<Pair<String, Counts>>, val pooled: Counts)

    fun family(rowsBySpeaker: List<Pair<String, List<DistanceRow>>>, scorers: List<RejectionScore>): List<ScorerRow> = scorers.map { s ->
        val per = rowsBySpeaker.map { it.first to heldOutSpeaker(it.second, s) }
        ScorerRow(s.label, per, per.map { it.second }.fold(Counts(0, 0, 0, 0)) { a, b -> a + b })
    }

    fun render(mc: McNemar, family: List<ScorerRow>, corpus: String): String = buildString {
        appendLine("## Rejection-score adjudication — held-out, matched FAR ≤ ${pct(target)} ($corpus)")
        appendLine()
        appendLine("**Pre-registered hypothesis H1:** `${mc.hypLabel}` lowers held-out FRR@FAR vs the shipped")
        appendLine("`${mc.baseLabel}` decision, winner = argmin d1 unchanged (rank-1 invariant). McNemar on the")
        appendLine("positive trials, thresholds fit per speaker-per-fold. Everything else below is **exploratory,")
        appendLine("not banked** (a family reported to avoid best-of-grid selection bias — the D3/EVAL-002 rule).")
        appendLine()
        appendLine("| Metric | `${mc.baseLabel}` (baseline) | `${mc.hypLabel}` (H1) |")
        appendLine("|---|---:|---:|")
        appendLine("| Held-out FRR | ${pct(mc.base.frr)} | ${pct(mc.hyp.frr)} |")
        appendLine("| Realized FAR | ${pct(mc.base.far)} | ${pct(mc.hyp.far)} |")
        appendLine("| Positives | ${mc.base.positives} | ${mc.hyp.positives} |")
        appendLine()
        appendLine(
            "**McNemar:** H1 rescued **${mc.n01}** positives the baseline rejected; regressed **${mc.n10}**. " +
                "χ²(df=1, cc) = ${fmt(mc.chiSq)}, p ≈ ${fmt(mc.pApprox)} → **${verdict(mc)}** (${mc.direction}).",
        )
        appendLine()
        appendLine("_Caveat:_ the two scorers each target FAR ≤ ${pct(target)} on train; their realized held-out")
        appendLine("FARs (above) differ slightly, so the FRR contrast is at *approximately*-matched FAR.")
        appendLine()
        val ids = family.firstOrNull()?.perSpeaker?.map { it.first } ?: emptyList()
        appendLine("### Exploratory full family (NOT banked)")
        appendLine()
        appendLine("| Scorer | Pooled FRR | Pooled FAR | ${ids.joinToString(" | ") { "$it FRR" }} |")
        appendLine("|---|---:|---:|${ids.joinToString("|") { "---:" }}|")
        for (row in family) {
            val per = row.perSpeaker.joinToString(" | ") { pct(it.second.frr) }
            appendLine("| `${row.label}` | ${pct(row.pooled.frr)} | ${pct(row.pooled.far)} | $per |")
        }
        appendLine()
        appendLine("Only H1-vs-baseline is significance-tested; the other rows are shown in full (losing cells")
        appendLine("included) precisely so no reader — or author — can retro-fit \"the winner\" from this table.")
        appendLine()
    }

    private fun verdict(mc: McNemar): String = when {
        mc.significantAt05 && mc.n01 > mc.n10 -> "H1 CONFIRMED (significant FRR reduction)"
        mc.significantAt05 && mc.n10 > mc.n01 -> "H1 REFUTED (significant regression)"
        else -> "H1 NOT SUPPORTED (no significant difference — honest negative result)"
    }

    private fun pct(v: Double) = String.format(Locale.US, "%.1f%%", v * 100)
    private fun fmt(v: Double) = String.format(Locale.US, "%.3f", v)

    private companion object {
        /** erfc-based upper tail of χ²(df=1): p = erfc(sqrt(x/2)). A&S 7.1.26 erfc approximation. */
        fun chiSquarePValueDf1(x: Double): Double {
            if (x <= 0.0) return 1.0
            val z = sqrt(x / 2.0)
            val t = 1.0 / (1.0 + 0.3275911 * z)
            val poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
            return (poly * exp(-z * z)).coerceIn(0.0, 1.0)
        }
    }
}
