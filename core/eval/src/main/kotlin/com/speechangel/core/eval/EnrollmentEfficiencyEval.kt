package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import java.io.File
import kotlin.random.Random

/**
 * **SOTA Domain 13 — enrollment efficiency.** How much of the fully-enrolled (saturation) accuracy the
 * system already reaches from a *single* enrollment recording — the effort-per-command axis that matters
 * most for the target population (`docs/product/2026-07-08_sota-domain-bands.md` §"Domain 13").
 *
 * ## Protocol (real TORGO, shipped `none` front-end)
 * A Monte-Carlo enrollment-count sweep on the same speaker-dependent k-fold split [TorgoEval] uses. For
 * each template count `t ∈ 1..[maxTemplates]`, every fold's enrollment set is randomly sub-sampled to at
 * most `t` utterances **per command word** (seeded [Random], so the run is deterministic), templates are
 * enrolled through the real [Evaluator], and closed-set rank-1 is scored on that fold's held-out
 * positives. Averaged over [iterations] random sub-samples and all speakers/folds.
 *
 * The closed set is preserved at every `t`: each command word keeps ≥1 template (the fold split
 * guarantees a query's word has ≥1 enrollment rep in its train folds), so a lower `t` never removes a
 * command — it only thins its template pool, which is exactly the enrollment-effort variable under test.
 *
 * ## Metric
 * `efficiency = rank1(t=1) / rank1(saturation)` where `rank1(saturation) = max over t of rank1(t)` — the
 * domain-bands "1-shot as % of saturation" fraction, expressed on the threshold-free rank-1 axis so it
 * reuses the existing [Evaluator]/[TorgoCorpus] machinery (no new threshold calibration). `saturationCount`
 * is the smallest `t` whose rank-1 is within 2% of the saturation value.
 *
 * This is a **real MEASURED** domain on the shipped front-end and counts for the wall-dominated composite.
 */
class EnrollmentEfficiencyEval(
    private val frontEnd: FeatureFrontEnd = FeatureFrontEnd("none", MfccConfig(deltaOrder = DeltaOrder.NONE)),
    private val k: Int = 5,
    private val minReps: Int = 2,
    private val mic: String = "wav_headMic",
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val maxTemplates: Int = 5,
    private val iterations: Int = 3,
    private val seed: Long = 1L,
) {
    data class SweepPoint(val templateCount: Int, val rank1: Double, val queries: Int)

    data class Result(val points: List<SweepPoint>, val saturationCount: Int, val efficiency: Double, val corpus: String) {
        val oneShotRank1: Double get() = points.first { it.templateCount == 1 }.rank1
        val saturationRank1: Double get() = points.maxOf { it.rank1 }
    }

    fun run(root: File): Result {
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val speakers = TorgoCorpus.scan(root, mic, minReps).filter { it.commands.isNotEmpty() }
        val points = (1..maxTemplates).map { t -> sweepPoint(t, speakers, evaluator) }
        val saturationRank1 = points.maxOf { it.rank1 }
        val efficiency = if (saturationRank1 <= 0.0) 0.0 else points.first { it.templateCount == 1 }.rank1 / saturationRank1
        val saturationCount = points.firstOrNull { it.rank1 >= SATURATION_FRACTION * saturationRank1 }?.templateCount ?: maxTemplates
        return Result(points, saturationCount, efficiency, root.name)
    }

    private fun sweepPoint(t: Int, speakers: List<TorgoCorpus.SpeakerData>, evaluator: Evaluator): SweepPoint {
        var hits = 0
        var total = 0
        for (iter in 0 until iterations) {
            val rng = Random(seed + iter * 1_000L + t)
            val folds = speakers.flatMap { TorgoCorpus.folds(it, k) }
            for (fold in folds) {
                val (foldHits, foldTotal) = scoreFold(fold, t, rng, evaluator)
                hits += foldHits
                total += foldTotal
            }
        }
        return SweepPoint(t, if (total == 0) 0.0 else hits.toDouble() / total, total)
    }

    /** Score one fold with the enrollment capped to [t] templates/command; returns (rank-1 hits, queries). */
    private fun scoreFold(fold: TorgoCorpus.Fold, t: Int, rng: Random, evaluator: Evaluator): Pair<Int, Int> {
        if (fold.positives.isEmpty()) return 0 to 0
        val cappedEnroll = fold.enroll
            .groupBy { it.word }
            .flatMap { (_, utts) -> utts.shuffled(rng).take(t) }
        if (cappedEnroll.isEmpty()) return 0 to 0
        val corpus = Corpus(
            enrollment = cappedEnroll.map { EnrollmentSample(CommandId(it.word), WavFile.read(it.wav)) },
            utterances = fold.positives.map {
                LabeledUtterance(WavFile.read(it.wav), CommandId(it.word), source = "torgo:${it.speaker}")
            },
        )
        val templates = evaluator.enroll(corpus).templates
        if (templates.isEmpty()) return 0 to 0
        val positives = evaluator.distanceTable(corpus, templates).filter { it.truth != null }
        val hits = positives.count { it.bestByCommand.minByOrNull { e -> e.value }?.key == it.truth }
        return hits to positives.size
    }

    private companion object {
        /** A `t` counts as "at saturation" once its rank-1 is within 2% of the best observed. */
        const val SATURATION_FRACTION = 0.98
    }
}
