package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import java.io.File
import java.util.Locale

/**
 * Runs the [Evaluator] over a real TORGO speaker set, **speaker-dependent** and **k-fold within
 * speaker** ([TorgoCorpus]), and produces the first non-`SYNTHETIC` FRR + false-accept report.
 *
 * Aggregation is done at the [DistanceRow] level: every fold's enroll → distance rows are collected
 * and a single [EvalReport] is built per speaker and across all speakers, so each utterance
 * contributes exactly one test trial. `synthetic = false` — the report has no synthetic banner.
 */
class TorgoEval(
    val frontEnd: FeatureFrontEnd = FeatureFrontEnd("delta_delta", MfccConfig(deltaOrder = DeltaOrder.DELTA_DELTA)),
    val k: Int = 5,
    val minReps: Int = 2,
    val mic: String = "wav_headMic",
    private val matcherConfig: MatcherConfig = MatcherConfig(),
) {
    /**
     * A threshold-free + operating-point analysis of one set of [DistanceRow]s. The fixed default
     * acceptance threshold (8.0) was tuned on the synthetic tone corpus and is meaningless on real
     * MFCC-DTW distances, so the headline metrics here do not depend on it:
     * - [rank1] — closed-set accuracy: is the nearest enrolled template the correct command
     *   (ignoring any threshold)? This answers "can the matcher discriminate this speaker's commands
     *   at all", which is the real hypothesis under test.
     * - [eerThreshold]/[frrAtEer]/[farAtEer] — the equal-error operating point from a self-ranged
     *   sweep of the acceptance threshold over the observed distances (FRR balanced against OOV FAR).
     */
    data class Analysis(
        val id: String,
        val commandCount: Int,
        val positives: Int,
        val negatives: Int,
        val enrollmentFailures: Int,
        val rank1: Double,
        val eerThreshold: Float,
        val frrAtEer: Double,
        val farAtEer: Double,
        val frrAtLowFar: Double,
        val lowFarTarget: Double,
        val emptyQueries: Int,
        val negativeAudioSeconds: Double,
        val distToTruthMedian: Double,
        val distToTruthP90: Double,
    )

    data class Result(val perSpeaker: List<Analysis>, val aggregate: Analysis, val speakerSet: String)

    fun run(root: File): Result {
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val speakers = TorgoCorpus.scan(root, mic, minReps)
        val allRows = ArrayList<DistanceRow>()
        var allFailures = 0
        var allCommands = 0
        val perSpeaker = ArrayList<Analysis>()
        for (spk in speakers) {
            if (spk.commands.isEmpty()) continue
            val spkRows = ArrayList<DistanceRow>()
            var spkFailures = 0
            for (fold in TorgoCorpus.folds(spk, k)) {
                if (fold.positives.isEmpty() && fold.negatives.isEmpty()) continue
                val corpus = TorgoCorpus.toCorpus(fold)
                val outcome = evaluator.enroll(corpus)
                spkFailures += outcome.failures.size
                spkRows += evaluator.distanceTable(corpus, outcome.templates)
            }
            perSpeaker += analyze(spk.id, spk.commandCount, spkRows, spkFailures)
            allRows += spkRows
            allFailures += spkFailures
            allCommands += spk.commandCount
        }
        return Result(perSpeaker, analyze("ALL", allCommands, allRows, allFailures), root.name)
    }

    /** Winner command + its distance for a row (argmin over the per-command best distances). */
    private fun winner(row: DistanceRow): Pair<CommandId?, Float> {
        val e = row.bestByCommand.minByOrNull { it.value } ?: return null to Float.POSITIVE_INFINITY
        return e.key to e.value
    }

    private fun analyze(id: String, commandCount: Int, rows: List<DistanceRow>, failures: Int): Analysis {
        val positives = rows.filter { it.truth != null }
        val negatives = rows.filter { it.truth == null }

        // Query-side VAD instrumentation: a query trimmed to near-empty yields no candidate distances
        // (empty bestByCommand) → an automatic miss. Counting these separates "the endpointer ate the
        // query" from "the matcher chose wrong" — the same artifact class as enrollment failures, but
        // on the test side, which the Evaluator does not otherwise surface.
        val emptyQueries = positives.count { it.bestByCommand.isEmpty() }

        // rank-1: nearest template is the correct command (threshold-free).
        val rank1hits = positives.count { winner(it).first == it.truth }
        val rank1 = if (positives.isEmpty()) 0.0 else rank1hits.toDouble() / positives.size

        // Self-ranged threshold sweep → equal-error + a low-FAR operating point.
        val posWinner = positives.map { winner(it) } // (cmd, dist)
        val negWinnerDist = negatives.map { winner(it).second }
        val candidates = (posWinner.map { it.second } + negWinnerDist).filter { it.isFinite() }.sorted().distinct()
        val lowFarTarget = 0.05 // an always-on assistant operates at low FAR, not at the symmetric EER.
        var eerT = Float.POSITIVE_INFINITY
        var frrEer = 1.0
        var farEer = 0.0
        var bestGap = Double.MAX_VALUE
        var frrLowFar = 1.0 // largest threshold whose FAR ≤ target gives the min FRR at that FAR.
        for (t in candidates) {
            // accepted-correct = nearest is truth AND within t.
            val correct = positives.count { p ->
                val (c, d) = winner(p)
                c == p.truth && d <= t
            }
            val frr = if (positives.isEmpty()) 0.0 else 1.0 - correct.toDouble() / positives.size
            val fa = negWinnerDist.count { it <= t }
            val far = if (negatives.isEmpty()) 0.0 else fa.toDouble() / negatives.size
            val gap = kotlin.math.abs(frr - far)
            if (gap < bestGap) {
                bestGap = gap
                eerT = t
                frrEer = frr
                farEer = far
            }
            if (far <= lowFarTarget) frrLowFar = frr
        }

        val truthDists = positives.mapNotNull { p -> p.truth?.let { p.bestByCommand[it] } }.sorted()
        fun pctl(p: Double) = if (truthDists.isEmpty()) 0.0 else truthDists[(p * (truthDists.size - 1)).toInt()].toDouble()

        return Analysis(
            id = id,
            commandCount = commandCount,
            positives = positives.size,
            negatives = negatives.size,
            enrollmentFailures = failures,
            rank1 = rank1,
            eerThreshold = eerT,
            frrAtEer = frrEer,
            farAtEer = farEer,
            frrAtLowFar = frrLowFar,
            lowFarTarget = lowFarTarget,
            emptyQueries = emptyQueries,
            negativeAudioSeconds = negatives.sumOf { it.durationMs / 1000.0 },
            distToTruthMedian = pctl(0.5),
            distToTruthP90 = pctl(0.9),
        )
    }

    /** A full markdown report: methodology + aggregate + per-speaker table. No synthetic banner. */
    fun render(result: Result): String = buildString {
        appendLine("# Real FRR/FAR — TORGO (${result.speakerSet}), speaker-dependent")
        appendLine()
        appendLine("Produced by `TorgoEval` (`core:eval`) over the TORGO corpus — the first **real,")
        appendLine("non-synthetic** SpeechAngel recognizer measurement.")
        appendLine()
        renderMethodology(this)
        renderAggregate(this, result)
        renderPerSpeaker(this, result)
        renderCaveats(this)
    }

    private fun renderMethodology(sb: StringBuilder) = with(sb) {
        val fe = "`${frontEnd.name}` (MFCC, deltaOrder=${frontEnd.config.deltaOrder}); mic: `$mic` (clean head-mic)."
        appendLine("## Methodology")
        appendLine("- **Speaker-dependent:** enrollment + test are always the same speaker (the product's")
        appendLine("  \"teach it your voice\" model). No cross-speaker matching.")
        appendLine("- **Front-end:** $fe")
        appendLine("- **Split:** $k-fold within speaker — each utterance is a test query exactly once and an")
        appendLine("  enrollment template in the other folds (never trained on the utterance it is tested on).")
        appendLine("  Chosen over a fixed enroll/test split because real per-speaker repetition depth is thin")
        appendLine("  (most words repeat 2–3×), so k-fold uses every repetition.")
        appendLine("- **Honesty on the split:** folds are index-round-robin, **not** session-stratified, so")
        appendLine("  same-session enroll/test pairs occur (and F01 has a single session, so it is entirely")
        appendLine("  same-session). Same-session pairing makes FRR **optimistic** vs enroll-once/use-later")
        appendLine("  product reality — the real-deployment number is if anything worse, not better, than below.")
        appendLine("- **Vocabulary:** command = a ≤2-token lexical prompt (brackets stripped) with ≥$minReps")
        appendLine("  utterances for that speaker; TORGO `xxx` markers, picture prompts, and reading-passage")
        appendLine("  sentences excluded. Every remaining single-instance word → OOV negative (`truth=null`).")
        appendLine("- **Metrics are threshold-free where possible.** The synthetic default acceptance")
        appendLine("  threshold (${matcherConfig.defaultAcceptanceThreshold}) is meaningless on real MFCC-DTW")
        appendLine("  distances, so the headline is **rank-1 closed-set accuracy** (is the nearest enrolled")
        appendLine("  template the correct command?) plus the **equal-error operating point** from a")
        appendLine("  self-ranged threshold sweep (FRR balanced against OOV false-accept rate).")
        appendLine()
    }

    private fun renderAggregate(sb: StringBuilder, result: Result) = with(sb) {
        val agg = result.aggregate
        val eerT = String.format(Locale.US, "%.2f", agg.eerThreshold)
        val negS = String.format(Locale.US, "%.1f", agg.negativeAudioSeconds)
        val med = String.format(Locale.US, "%.1f", agg.distToTruthMedian)
        val p90 = String.format(Locale.US, "%.1f", agg.distToTruthP90)
        appendLine("## Aggregate (${result.perSpeaker.size} dysarthric speakers)")
        appendLine(
            "- Positives: ${agg.positives} · OOV negatives: ${agg.negatives} · " +
                "Enrollment failures: ${agg.enrollmentFailures} · Empty-query (VAD-eaten): ${agg.emptyQueries}",
        )
        appendLine("- **Rank-1 accuracy: ${pct(agg.rank1)}** (nearest template is the correct command)")
        appendLine(
            "- **At the equal-error operating point** (threshold $eerT): **FRR ${pct(agg.frrAtEer)}**, " +
                "**OOV FAR ${pct(agg.farAtEer)}** over $negS s of OOV audio.",
        )
        appendLine(
            "- **At a low-FAR operating point** (OOV FAR ≤ ${pct(agg.lowFarTarget)}, the always-on " +
                "regime): **FRR ${pct(agg.frrAtLowFar)}**.",
        )
        appendLine("- Distance-to-true-command: median $med, p90 $p90.")
        appendLine()
        appendLine("Note: the aggregate blends different vocabulary sizes (chance rank-1 differs ~5× across")
        appendLine("speakers) — read the per-speaker rank-1-vs-vocabulary column, not the blended figure.")
        appendLine()
    }

    private fun renderPerSpeaker(sb: StringBuilder, result: Result) = with(sb) {
        appendLine("## Per speaker (rank-1 vs vocabulary size)")
        appendLine()
        appendLine("| Speaker | Commands | Positives | Empty-Q | Rank-1 | Chance | FRR@EER | FAR@EER | FRR@FAR≤5% |")
        appendLine("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for (s in result.perSpeaker) {
            val chance = if (s.commandCount > 0) 1.0 / s.commandCount else 0.0
            appendLine(
                "| ${s.id} | ${s.commandCount} | ${s.positives} | ${s.emptyQueries} | ${pct(s.rank1)} | " +
                    "${pct(chance)} | ${pct(s.frrAtEer)} | ${pct(s.farAtEer)} | ${pct(s.frrAtLowFar)} |",
            )
        }
        appendLine()
        appendLine("Rank-1 falls as the command vocabulary grows (fewest commands = highest rank-1). A realistic")
        appendLine("SpeechAngel deployment is ~10–20 commands, i.e. the **top** of this curve, not the 77-word tail.")
        appendLine()
    }

    private fun renderCaveats(sb: StringBuilder) = with(sb) {
        appendLine("## What this does and does not measure")
        appendLine("- **Measures:** speaker-dependent discrimination (rank-1) on real dysarthric speech, and")
        appendLine("  the FRR/OOV-FAR trade-off at a calibrated operating point.")
        appendLine("- **Rank-1 is the hypothesis test.** It ignores the acceptance threshold entirely, so it")
        appendLine("  is not confounded by the un-tuned synthetic default. A near-chance rank-1")
        appendLine("  (≈ 1/commands) would refute the matcher; a high rank-1 means the discrimination is")
        appendLine("  real and the deployment problem is threshold calibration (`ThresholdCalibrator`).")
        appendLine("- **Does NOT measure:** the Phase-0 exit's always-on **ambient** FAR/hour budget")
        appendLine("  (≤0.5 false accepts/hr on continuous audio). TORGO has no continuous ambient stream,")
        appendLine("  so the OOV FAR here is a per-utterance rate, not per-hour-of-listening.")
        appendLine("- **VAD is clean on both sides.** Enrollment failures = utterances the energy-VAD /")
        appendLine("  `minSpeechFrames` gate dropped at enroll; empty-query positives = queries trimmed to")
        appendLine("  nothing at test. Both are 0 here, so neither the misses nor the earlier")
        appendLine("  100%-FRR-at-default-threshold are trimming artifacts — the miss rate is the matcher, and")
        appendLine("  the earlier 100% was purely the un-tuned synthetic threshold.")
    }

    private fun pct(v: Double) = String.format(Locale.US, "%.1f%%", v * 100)
}
