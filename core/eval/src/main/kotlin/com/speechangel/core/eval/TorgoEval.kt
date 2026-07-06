package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.dsp.NoiseReduction
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import java.io.File
import java.util.Locale

/**
 * Runs the [Evaluator] over a real TORGO speaker set, **speaker-dependent** and **k-fold within
 * speaker** ([TorgoCorpus]), and produces the first non-`SYNTHETIC` FRR + false-accept report.
 *
 * Aggregation is done at the [DistanceRow] level: every fold's enroll → distance rows are collected
 * (each tagged with its test fold) and a single [Analysis] is built per speaker and across all
 * speakers, so each utterance contributes exactly one test trial. `synthetic = false`.
 *
 * ## Held-out threshold selection (EVAL-002)
 * The headline FRR/FAR operating points are computed **leave-one-fold-out**: for each fold the
 * acceptance threshold(s) are fit on the *other* folds (train) and scored on the held-out fold, so no
 * trial's own row sets the threshold it is judged by. Both the global-threshold and the per-command
 * ([ThresholdCalibrator]) methods select their knob on train targeting FAR ≤ 5% and are then read at
 * their **realized held-out FAR** — a matched-FAR comparison (never FRRs across unequal FAR). The old
 * pooled in-sample sweep is retained only as an explicitly-labelled optimistic reference.
 */
class TorgoEval(
    val frontEnd: FeatureFrontEnd = FeatureFrontEnd("delta_delta", MfccConfig(deltaOrder = DeltaOrder.DELTA_DELTA)),
    val k: Int = 5,
    val minReps: Int = 2,
    val mic: String = "wav_headMic",
    private val matcherConfig: MatcherConfig = MatcherConfig(),
) {
    private val calibrator = ThresholdCalibrator(frontEnd, matcherConfig)

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
        /** In-sample pooled sweep FRR at FAR ≤ target — optimistic reference, NOT the headline. */
        val frrAtLowFarInSample: Double,
        val lowFarTarget: Double,
        /** Held-out global-threshold operating point (threshold fit on train folds). */
        val frrLowFarGlobalHeldOut: Double,
        val farLowFarGlobalHeldOut: Double,
        /** Held-out per-command operating point; (-1,-1) when not computed (cross-speaker aggregate). */
        val frrLowFarPerCmdHeldOut: Double,
        val farLowFarPerCmdHeldOut: Double,
        val emptyQueries: Int,
        val negativeAudioSeconds: Double,
        val distToTruthMedian: Double,
        val distToTruthP90: Double,
    )

    data class Result(
        val perSpeaker: List<Analysis>,
        val aggregate: Analysis,
        val deploymentSlice: Analysis?,
        val sliceSpeakerIds: List<String>,
        val speakerSet: String,
    )

    private data class SpeakerRows(val id: String, val commandCount: Int, val rows: List<DistanceRow>, val failures: Int)

    fun run(root: File): Result {
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val speakers = TorgoCorpus.scan(root, mic, minReps)
        val perSpeakerData = ArrayList<SpeakerRows>()
        for (spk in speakers) {
            if (spk.commands.isEmpty()) continue
            val spkRows = ArrayList<DistanceRow>()
            var spkFailures = 0
            for (fold in TorgoCorpus.folds(spk, k)) {
                if (fold.positives.isEmpty() && fold.negatives.isEmpty()) continue
                val corpus = TorgoCorpus.toCorpus(fold)
                val outcome = evaluator.enroll(corpus)
                spkFailures += outcome.failures.size
                spkRows += evaluator.distanceTable(corpus, outcome.templates).map { it.copy(fold = fold.index) }
            }
            perSpeakerData += SpeakerRows(spk.id, spk.commandCount, spkRows, spkFailures)
        }

        val perSpeaker = perSpeakerData.map { analyze(it.id, it.commandCount, it.rows, it.failures, perCommandHeldOut = true) }
        val allRows = perSpeakerData.flatMap { it.rows }
        val allCommands = perSpeakerData.sumOf { it.commandCount }
        val allFailures = perSpeakerData.sumOf { it.failures }
        val aggregate = analyze("ALL", allCommands, allRows, allFailures, perCommandHeldOut = false)

        // D2 — the deployment-relevant vocabulary slice (≤ 25 commands: the realistic-vocabulary regime,
        // stated a-priori; admits F01/F04, excludes the F03 77-word reading-passage tail). Reported, not tuned.
        val sliceData = perSpeakerData.filter { it.commandCount <= SLICE_MAX_COMMANDS }
        val sliceRows = sliceData.flatMap { it.rows }
        val slice = if (sliceRows.isEmpty()) {
            null
        } else {
            analyze("SLICE", sliceData.sumOf { it.commandCount }, sliceRows, sliceData.sumOf { it.failures }, perCommandHeldOut = false)
        }
        return Result(perSpeaker, aggregate, slice, sliceData.map { it.id }, root.name)
    }

    /** Winner command + its distance for a row (argmin over the per-command best distances). */
    private fun winner(row: DistanceRow): Pair<CommandId?, Float> {
        val e = row.bestByCommand.minByOrNull { it.value } ?: return null to Float.POSITIVE_INFINITY
        return e.key to e.value
    }

    /** A held-out operating point: false-reject rate and its realized false-accept rate. */
    data class HeldOutPoint(val frr: Double, val far: Double)

    /** Fraction of a row set's OOV negatives accepted under [thr] (default threshold for absent commands). */
    internal fun farOf(rows: List<DistanceRow>, thr: Map<CommandId, Float>): Double {
        val negs = rows.filter { it.truth == null }
        if (negs.isEmpty()) return 0.0
        val default = matcherConfig.defaultAcceptanceThreshold
        val fa = negs.count { r ->
            val (c, d) = winner(r)
            c != null && d <= (thr[c] ?: default)
        }
        return fa.toDouble() / negs.size
    }

    /**
     * Leave-one-fold-out held-out operating point: for each fold, fit thresholds on the OTHER folds via
     * [fit] and score this fold; pool accept/false-accept counts across folds. A positive is a hit only
     * when the nearest template is the true command AND within threshold; any accepted negative is an FA.
     */
    internal fun heldOut(rows: List<DistanceRow>, fit: (train: List<DistanceRow>) -> Map<CommandId, Float>): HeldOutPoint {
        val folds = rows.map { it.fold }.filter { it >= 0 }.toSortedSet()
        val default = matcherConfig.defaultAcceptanceThreshold
        var acc = 0
        var pos = 0
        var fa = 0
        var neg = 0
        for (f in folds) {
            val thr = fit(rows.filter { it.fold != f })
            for (r in rows.filter { it.fold == f }) {
                val (c, d) = winner(r)
                val accepted = c != null && d <= (thr[c] ?: default)
                if (r.truth != null) {
                    pos++
                    if (accepted && c == r.truth) acc++
                } else {
                    neg++
                    if (accepted) fa++
                }
            }
        }
        return HeldOutPoint(
            frr = if (pos == 0) 0.0 else 1.0 - acc.toDouble() / pos,
            far = if (neg == 0) 0.0 else fa.toDouble() / neg,
        )
    }

    /** Largest global scalar threshold whose TRAIN FAR ≤ [target] (min FRR within the FAR budget). */
    internal fun fitGlobal(train: List<DistanceRow>, commands: List<CommandId>, target: Double): Map<CommandId, Float> {
        val cands = train.flatMap { it.bestByCommand.values }.filter { it.isFinite() }.sorted().distinct()
        var best = (cands.firstOrNull() ?: 0f) - 1f // reject-all baseline → FAR 0 ≤ target always exists.
        for (t in cands) if (farOf(train, commands.associateWith { t }) <= target) best = t // ascending → last within budget.
        return commands.associateWith { best }
    }

    /**
     * Thresholds at the largest per-command FA budget whose TRAIN FAR ≤ [target]. TRAIN FAR is monotone
     * non-decreasing in the budget (more allowance → higher thresholds → more accepts), so this is a
     * **binary search** for the largest in-budget value — O(log cap) calibrations instead of O(cap),
     * which matters on well-separated corpora where a linear scan never breaks early.
     */
    internal fun fitPerCmd(train: List<DistanceRow>, commands: List<CommandId>, target: Double): Map<CommandId, Float> {
        val rejectAll = (train.flatMap { it.bestByCommand.values }.filter { it.isFinite() }.minOrNull() ?: 0f) - 1f
        var chosen = commands.associateWith { rejectAll } // budget 0 → FAR 0 baseline.
        var lo = 1
        var hi = maxOf(1, minOf(train.count { it.truth == null }, commands.size * 4))
        while (lo <= hi) {
            val mid = (lo + hi) / 2
            val thr = calibrator.calibrateFromRows(train, commands, mid)
            if (farOf(train, thr) <= target) {
                chosen = thr // in budget → this and everything below is feasible; try larger.
                lo = mid + 1
            } else {
                hi = mid - 1
            }
        }
        return chosen
    }

    private fun analyze(id: String, commandCount: Int, rows: List<DistanceRow>, failures: Int, perCommandHeldOut: Boolean): Analysis {
        val positives = rows.filter { it.truth != null }
        val negatives = rows.filter { it.truth == null }
        val commands = positives.mapNotNull { it.truth }.distinct()
        val emptyQueries = positives.count { it.bestByCommand.isEmpty() }

        val rank1hits = positives.count { winner(it).first == it.truth }
        val rank1 = if (positives.isEmpty()) 0.0 else rank1hits.toDouble() / positives.size

        // In-sample pooled sweep → EER + an optimistic low-FAR reference (NOT the headline; EVAL-002).
        val posWinner = positives.map { winner(it) }
        val negWinnerDist = negatives.map { winner(it).second }
        val candidates = (posWinner.map { it.second } + negWinnerDist).filter { it.isFinite() }.sorted().distinct()
        val target = LOW_FAR_TARGET
        var eerT = Float.POSITIVE_INFINITY
        var frrEer = 1.0
        var farEer = 0.0
        var bestGap = Double.MAX_VALUE
        var frrLowFarInSample = 1.0
        for (t in candidates) {
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
            if (far <= target) frrLowFarInSample = frr
        }

        // Held-out matched-FAR operating points (EVAL-002).
        val globalHO = heldOut(rows) { train -> fitGlobal(train, commands, target) }
        val perCmdHO = if (perCommandHeldOut) heldOut(rows) { train -> fitPerCmd(train, commands, target) } else HeldOutPoint(-1.0, -1.0)

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
            frrAtLowFarInSample = frrLowFarInSample,
            lowFarTarget = target,
            frrLowFarGlobalHeldOut = globalHO.frr,
            farLowFarGlobalHeldOut = globalHO.far,
            frrLowFarPerCmdHeldOut = perCmdHO.frr,
            farLowFarPerCmdHeldOut = perCmdHO.far,
            emptyQueries = emptyQueries,
            negativeAudioSeconds = negatives.sumOf { it.durationMs / 1000.0 },
            distToTruthMedian = pctl(0.5),
            distToTruthP90 = pctl(0.9),
        )
    }

    // ---- D3: front-end bake-off on real voices (held-out rank-1 grid) ----

    data class GridCell(
        val name: String,
        val order: DeltaOrder,
        val noise: NoiseReduction,
        val rank1: Double,
        val perSpeaker: List<Pair<String, Double>>,
    )

    /** Run the full k-fold TORGO eval once per {deltaOrder × noiseReduction} front-end and collect the
     *  **held-out rank-1** (threshold-free → no in-sample fitting). Expensive (one full run per cell). */
    fun frontEndGrid(root: File): List<GridCell> {
        val cells = ArrayList<GridCell>()
        for (order in listOf(DeltaOrder.NONE, DeltaOrder.DELTA, DeltaOrder.DELTA_DELTA)) {
            for (noise in listOf(NoiseReduction.NONE, NoiseReduction.SPECTRAL_SUBTRACTION)) {
                val name = order.name.lowercase(Locale.US) + if (noise == NoiseReduction.NONE) "" else "+nr"
                val fe = FeatureFrontEnd(name, MfccConfig(deltaOrder = order, noiseReduction = noise))
                val res = TorgoEval(fe, k, minReps, mic, matcherConfig).run(root)
                cells.add(GridCell(name, order, noise, res.aggregate.rank1, res.perSpeaker.map { it.id to it.rank1 }))
            }
        }
        return cells
    }

    fun renderFrontEndGrid(cells: List<GridCell>): String = buildString {
        appendLine("## Front-end bake-off (held-out rank-1, real voices)")
        appendLine()
        appendLine("Full {static, +Δ, +Δ+ΔΔ} × {noiseReduction off, on} grid. Metric is **held-out rank-1**")
        appendLine("(threshold-free, so no operating-point fitting). The full grid is shown — losing cells")
        appendLine("included — because reporting only the max would be a selection-biased overstatement.")
        appendLine()
        val speakerIds = cells.firstOrNull()?.perSpeaker?.map { it.first } ?: emptyList()
        appendLine("| Front-end | Aggregate rank-1 | ${speakerIds.joinToString(" | ")} |")
        appendLine("|---|---:|${speakerIds.joinToString("|") { "---:" }}|")
        for (c in cells) {
            val per = c.perSpeaker.joinToString(" | ") { pct(it.second) }
            appendLine("| `${c.name}` | ${pct(c.rank1)} | $per |")
        }
        appendLine()
        // Stated prior: highest aggregate held-out rank-1; ties → simpler front-end (fewer deltas, nr off).
        val simplicity = { c: GridCell -> c.order.ordinal * 2 + if (c.noise == NoiseReduction.NONE) 0 else 1 }
        val winner = cells.maxWithOrNull(compareBy<GridCell> { it.rank1 }.thenByDescending { simplicity(it) })
        if (winner != null) {
            appendLine(
                "**Winner by stated prior** (highest aggregate held-out rank-1; ties → simpler front-end): " +
                    "`${winner.name}` at ${pct(winner.rank1)}. This cell is **optimistically selected on this " +
                    "corpus** — it is not an independent test set, so treat it as best-of-grid, not a clean gain.",
            )
        }
        appendLine()
    }

    /** A full markdown report: methodology + aggregate + per-speaker table + deployment slice. */
    fun render(result: Result): String = buildString {
        appendLine("# Real FRR/FAR — TORGO (${result.speakerSet}), speaker-dependent")
        appendLine()
        appendLine("Produced by `TorgoEval` (`core:eval`) over the TORGO corpus — the first **real,")
        appendLine("non-synthetic** SpeechAngel recognizer measurement, with **held-out** (leave-one-fold-out)")
        appendLine("threshold selection (EVAL-002).")
        appendLine()
        renderMethodology(this)
        renderAggregate(this, result)
        renderPerSpeaker(this, result)
        renderSlice(this, result)
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
        appendLine("- **Held-out thresholds (EVAL-002):** the acceptance threshold (global) and the per-command")
        appendLine("  `ThresholdCalibrator` budget are **fit on the folds not under test** and scored on the")
        appendLine("  held-out fold. Both target FAR ≤ ${pct(LOW_FAR_TARGET)} on train and are read at their")
        appendLine("  **realized held-out FAR** — a matched-FAR comparison, never FRRs across unequal FAR. The")
        appendLine("  pooled in-sample sweep is retained only as an explicitly-labelled optimistic reference.")
        appendLine("- **Residual leak (disclosed):** folds share *enrollment* audio (a test row of fold f may")
        appendLine("  have been an enrollment template when scoring fold g), so calibration distances are not")
        appendLine("  fully independent of the test fold's audio — second-order (enrollment overlap, not")
        appendLine("  test-label overlap) and standard in k-fold threshold transfer.")
        appendLine("- **Vocabulary:** command = a ≤2-token lexical prompt (brackets stripped) with ≥$minReps")
        appendLine("  utterances for that speaker; TORGO `xxx` markers, picture prompts, and reading-passage")
        appendLine("  sentences excluded. Every remaining single-instance word → OOV negative (`truth=null`).")
        appendLine("- **Rank-1** (nearest enrolled template is the correct command) is the threshold-free")
        appendLine("  hypothesis headline; it is already held-out (scored vs other-fold templates only).")
        appendLine()
    }

    private fun renderAggregate(sb: StringBuilder, result: Result) = with(sb) {
        val agg = result.aggregate
        val eerT = String.format(Locale.US, "%.2f", agg.eerThreshold)
        val negS = String.format(Locale.US, "%.1f", agg.negativeAudioSeconds)
        val med = String.format(Locale.US, "%.1f", agg.distToTruthMedian)
        val p90 = String.format(Locale.US, "%.1f", agg.distToTruthP90)
        appendLine("## Aggregate (${result.perSpeaker.size} speakers)")
        appendLine(
            "- Positives: ${agg.positives} · OOV negatives: ${agg.negatives} · " +
                "Enrollment failures: ${agg.enrollmentFailures} · Empty-query (VAD-eaten): ${agg.emptyQueries}",
        )
        appendLine("- **Rank-1 accuracy: ${pct(agg.rank1)}** (nearest template is the correct command; held-out).")
        appendLine(
            "- **Held-out global-threshold operating point:** FRR **${pct(agg.frrLowFarGlobalHeldOut)}** " +
                "at realized FAR ${pct(agg.farLowFarGlobalHeldOut)} (target ≤ ${pct(agg.lowFarTarget)}).",
        )
        appendLine(
            "- _In-sample reference (optimistic, not the headline):_ FRR ${pct(agg.frrAtLowFarInSample)} at " +
                "FAR ≤ ${pct(agg.lowFarTarget)}; EER threshold $eerT (FRR ${pct(agg.frrAtEer)} / FAR ${pct(agg.farAtEer)}).",
        )
        appendLine("- OOV audio: $negS s. Distance-to-true-command: median $med, p90 $p90.")
        appendLine()
        appendLine("Per-command held-out calibration is reported per speaker (below), not pooled — commands are")
        appendLine("per-speaker, so a cross-speaker pooled per-command number would conflate distinct vocabularies.")
        appendLine()
        appendLine("Note: the aggregate blends different vocabulary sizes — read the per-speaker column too.")
        appendLine()
    }

    private fun renderPerSpeaker(sb: StringBuilder, result: Result) = with(sb) {
        appendLine("## Per speaker (held-out, matched FAR ≤ ${pct(LOW_FAR_TARGET)})")
        appendLine()
        appendLine("| Speaker | Commands | Pos | Rank-1 | Chance | FRR (global, HO) | FAR | FRR (per-cmd, HO) | FAR | FRR (in-sample) |")
        appendLine("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for (s in result.perSpeaker) {
            val chance = if (s.commandCount > 0) 1.0 / s.commandCount else 0.0
            appendLine(
                "| ${s.id} | ${s.commandCount} | ${s.positives} | ${pct(s.rank1)} | ${pct(chance)} | " +
                    "${pct(s.frrLowFarGlobalHeldOut)} | ${pct(s.farLowFarGlobalHeldOut)} | " +
                    "${pctOrDash(s.frrLowFarPerCmdHeldOut)} | ${pctOrDash(s.farLowFarPerCmdHeldOut)} | " +
                    "${pct(s.frrAtLowFarInSample)} |",
            )
        }
        appendLine()
        appendLine("`HO` = held-out (threshold fit on other folds). Both HO columns are read at the same")
        appendLine("realized-FAR line, so their FRRs are directly comparable; the in-sample column is the")
        appendLine("optimistic pooled-sweep reference for contrast. Where per-command does **not** beat the")
        appendLine("global threshold at matched FAR, that is the honest finding (sparse per-command negatives")
        appendLine("→ the `maxObserved+1` accept-all fallback inflates held-out FAR).")
        appendLine()
    }

    private fun renderSlice(sb: StringBuilder, result: Result) = with(sb) {
        val slice = result.deploymentSlice ?: return@with
        appendLine("## Deployment-relevant slice (≤ $SLICE_MAX_COMMANDS commands) — reported, not tuned")
        appendLine()
        appendLine("Speakers ${result.sliceSpeakerIds.joinToString(", ")} (the realistic ~10–25-command regime a")
        appendLine("real SpeechAngel deployment ships, vs the 77-word reading-passage tail). Cutoff stated")
        appendLine("a-priori, not fit to results.")
        appendLine(
            "- **Held-out global-threshold FRR ${pct(slice.frrLowFarGlobalHeldOut)}** at realized FAR " +
                "${pct(slice.farLowFarGlobalHeldOut)} (target ≤ ${pct(slice.lowFarTarget)}); rank-1 ${pct(slice.rank1)}.",
        )
        appendLine("- _In-sample reference:_ FRR ${pct(slice.frrAtLowFarInSample)} at FAR ≤ ${pct(slice.lowFarTarget)}.")
        appendLine()
    }

    private fun renderCaveats(sb: StringBuilder) = with(sb) {
        appendLine("## What this does and does not measure")
        appendLine("- **Measures:** speaker-dependent discrimination (rank-1) on real speech, and the")
        appendLine("  **held-out** FRR/OOV-FAR trade-off at a matched, train-calibrated operating point.")
        appendLine("- **Does NOT measure:** the Phase-0 exit's always-on **ambient** FAR/hour budget")
        appendLine("  (≤0.5 false accepts/hr on continuous audio). TORGO has no continuous ambient stream,")
        appendLine("  so the OOV FAR here is a per-utterance rate, not per-hour-of-listening.")
        appendLine("- **The matcher is 1-NN (min DTW), not a vote.** `TemplateMatcher.match` keeps the minimum")
        appendLine("  distance across a command's templates and thresholds it — there is no k-NN/majority vote")
        appendLine("  (a docs-vs-code correction, `docs/errors/2026-07/`). More enrolled templates per command")
        appendLine("  (nearest-neighbour), threshold calibration, and the QbE embedding are the improvement path.")
    }

    private fun pct(v: Double) = String.format(Locale.US, "%.1f%%", v * 100)
    private fun pctOrDash(v: Double) = if (v < 0) "—" else pct(v)

    private companion object {
        const val LOW_FAR_TARGET = 0.05 // an always-on assistant operates at low FAR, not the symmetric EER.
        const val SLICE_MAX_COMMANDS = 25 // a-priori realistic-vocabulary cutoff (admits F01/F04, excludes F03).
    }
}
