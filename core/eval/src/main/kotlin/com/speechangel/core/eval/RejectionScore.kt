package com.speechangel.core.eval

import com.speechangel.core.model.CommandId

/**
 * The scalar an accept/reject decision thresholds. **Lower = more command-like** (accept iff
 * `score(row) ≤ threshold`), matching the raw-distance convention so the sweep direction is unchanged.
 *
 * The winning command is ALWAYS `argmin d1` (see [winnerCommand]); a [RejectionScore] only changes the
 * quantity the *acceptance* of that winner is judged on — so rank-1 (which command wins) is invariant by
 * construction and the scorer moves only the open-set FRR/FAR trade-off. This is the exact lever for the
 * ~34-point gap between rank-1 error and FRR@FAR on TORGO
 * (`docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`).
 *
 * This is genuinely NOT the "voting" no-op (`docs/errors/2026-07/…voting-claim-vs-code.md`): the shipped
 * decision (`Evaluator.DistanceRow.decide`, `TemplateMatcher.match`) thresholds `d1` alone; [CommonMode]
 * thresholds a quantity — the per-trial cohort offset — that the current decision ignores.
 */
fun interface RejectionScore {
    /** Score for [row]'s argmin winner, or null when the row has no finite candidate. */
    fun score(row: DistanceRow): Float?

    /** Human name for reports. */
    val label: String get() = "score"

    companion object {
        /** The winner command for a row (argmin over per-command min-DTW distances) — scorer-independent. */
        fun winnerCommand(row: DistanceRow): CommandId? = row.bestByCommand.minByOrNull { it.value }?.key

        /** The winner's raw distance `d1`, or null. */
        fun winnerDistance(row: DistanceRow): Float? = row.bestByCommand.minByOrNull { it.value }?.value

        private fun median(values: List<Float>): Float {
            if (values.isEmpty()) return 0f
            val s = values.sorted()
            val m = s.size / 2
            return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) / 2f
        }

        /** Baseline: threshold the winner's raw min-DTW distance `d1` (what ships today). */
        val RawDistance: RejectionScore = object : RejectionScore {
            override val label = "raw"
            override fun score(row: DistanceRow) = winnerDistance(row)
        }

        /**
         * **Pre-registered hypothesis H1.** Common-mode (cohort) normalization:
         * `s = d1 − median{ d_c : c ≠ winner }`. Subtracts the per-trial "how far is this audio from
         * *everything*" offset. A true command is close to its own template AND far from the others
         * (very negative → accept); generic OOV audio is ~equidistant from all commands (`s ≈ 0` →
         * reject). Rescues "far-from-everything" positives that a runner-up margin cannot, and needs NO
         * per-command negative data — so it is orthogonal to why per-command calibration (D1) failed.
         * With <2 commands the cohort is empty and it degrades to [RawDistance].
         */
        val CommonMode: RejectionScore = object : RejectionScore {
            override val label = "common_mode"
            override fun score(row: DistanceRow): Float? {
                val winner = row.bestByCommand.minByOrNull { it.value } ?: return null
                val others = row.bestByCommand.filterKeys { it != winner.key }.values.filter { it.isFinite() }
                if (others.isEmpty()) return winner.value
                return winner.value - median(others)
            }
        }

        /**
         * Exploratory (NOT banked): runner-up margin penalty `s = d1 − λ·(d2 − d1)`. Reported alongside
         * H1 in the full-family table only; the pre-registration adjudicates H1 vs [RawDistance] alone.
         */
        fun margin(lambda: Float = 1.0f): RejectionScore = object : RejectionScore {
            override val label = "margin(λ=$lambda)"
            override fun score(row: DistanceRow): Float? {
                val ranked = row.bestByCommand.values.filter { it.isFinite() }.sorted()
                val d1 = ranked.getOrNull(0) ?: return null
                val d2 = ranked.getOrNull(1) ?: return d1
                return d1 - lambda * (d2 - d1)
            }
        }

        /** Exploratory (NOT banked): cohort ratio `s = d1 / mean(other-command distances)`. */
        val Ratio: RejectionScore = object : RejectionScore {
            override val label = "ratio"
            override fun score(row: DistanceRow): Float? {
                val winner = row.bestByCommand.minByOrNull { it.value } ?: return null
                val others = row.bestByCommand.filterKeys { it != winner.key }.values.filter { it.isFinite() }
                if (others.isEmpty()) return winner.value
                val mean = others.average().toFloat()
                return if (mean <= 0f) winner.value else winner.value / mean
            }
        }
    }
}
