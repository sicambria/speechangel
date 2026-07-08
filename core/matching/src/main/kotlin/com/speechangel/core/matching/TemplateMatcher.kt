package com.speechangel.core.matching

import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.RejectionReason
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId

/**
 * Tuning for [TemplateMatcher].
 *
 * @property defaultAcceptanceThreshold Maximum length-normalised DTW distance to accept a match.
 *   This is feature-scaling dependent and MUST be calibrated per deployment (Phase 0: measure
 *   FRR/FAR — see `research/04_build_and_reuse_plan.md`). Per-command overrides are supported.
 *   The scale is set by [Dtw.distance]'s `(n + m)` normalization — changing that divisor invalidates
 *   this threshold (audit 2026-06-28_dtw-length-normalization-convention).
 * @property bandRatio Sakoe–Chiba band passed to [Dtw].
 * @property marginWeight How much the gap to the runner-up command contributes to confidence.
 */
data class MatcherConfig(
    val defaultAcceptanceThreshold: Float = 8.0f,
    val bandRatio: Double = 0.1,
    val marginWeight: Float = 0.4f,
    /** Local frame distance: "euclidean" (default) or "cosine". */
    val localDistance: String = "euclidean",
    /**
     * E02-08: Dual-filter cascade — reject DTW matches where the alignment path length deviates
     * more than this fraction from the expected length. 0.0 = disabled (default).
     * e.g. 0.3 means reject if |pathLen - expectedLen| / expectedLen > 0.3.
     */
    val dualFilterTolerance: Double = 0.0,
    /**
     * E02-05: k-NN matching — number of nearest templates per command to average distances for.
     * k=1 (default) is min-DTW. k=3 averages top-3 distances.
     */
    val kNN: Int = 1,
    /**
     * E09-08: Hysteresis zone width as fraction of threshold. 0.0 = disabled (default).
     * e.g. 0.2 means accept if distance < 0.8*threshold, reject if > 1.2*threshold,
     * and use runner-up margin in between.
     */
    val hysteresisZone: Double = 0.0,
)

/**
 * Speaker-dependent, language-independent command matcher.
 *
 * For each command it keeps the *best* (minimum) DTW distance across all of that command's enrolled
 * templates — the multi-template robustness mechanism for voice drift. It accepts only if the best
 * distance clears the (per-command) acceptance threshold, otherwise it rejects (OOV / garbage),
 * which is essential for always-on use where most audio is *not* a command.
 */
class TemplateMatcher(private val config: MatcherConfig = MatcherConfig()) {

    fun match(
        query: FeatureSequence,
        templates: List<Template>,
        perCommandThresholds: Map<CommandId, Float> = emptyMap(),
    ): RecognitionResult {
        if (query.isEmpty) return RecognitionResult.NoMatch(RejectionReason.EMPTY_INPUT)
        if (templates.isEmpty()) return RecognitionResult.NoMatch(RejectionReason.NO_TEMPLATES)

        val enhanced = config.dualFilterTolerance > 0.0 || config.kNN > 1 || config.hysteresisZone > 0.0

        // Fast path: original 1-NN min-DTW logic.
        if (!enhanced) {
            val bestPerCommand = HashMap<CommandId, Best>()
            for (template in templates) {
                if (template.features.coefficientCount != query.coefficientCount) continue
                val dist = Dtw.distance(query, template.features, config.bandRatio, localFn()).toFloat()
                val current = bestPerCommand[template.commandId]
                if (current == null || dist < current.distance) {
                    bestPerCommand[template.commandId] = Best(template.id, dist)
                }
            }
            if (bestPerCommand.isEmpty()) return RecognitionResult.NoMatch(RejectionReason.NO_TEMPLATES)

            val ranked = bestPerCommand.entries.sortedBy { it.value.distance }
            val winner = ranked.first()
            val winnerCommand = winner.key
            val winnerBest = winner.value
            val runnerUp = ranked.getOrNull(1)?.value?.distance

            val threshold = perCommandThresholds[winnerCommand] ?: config.defaultAcceptanceThreshold
            if (winnerBest.distance > threshold) {
                return RecognitionResult.NoMatch(RejectionReason.BELOW_CONFIDENCE, winnerBest.distance, winnerCommand)
            }
            return RecognitionResult.Match(
                winnerCommand,
                winnerBest.templateId,
                confidenceOf(winnerBest.distance, runnerUp, threshold),
                winnerBest.distance,
            )
        }

        // Enhanced path: dual-filter, k-NN, and/or hysteresis.
        return enhancedMatch(query, templates, perCommandThresholds)
    }

    private data class TmplDist(val templateId: TemplateId, val distance: Float)

    /** Dual-filter (E02-08) distance, or null if the template is rejected/incompatible. */
    private fun dualFilteredDistance(query: FeatureSequence, template: Template, ln: (FloatArray, FloatArray) -> Double): Float? {
        val r = Dtw.withPath(query, template.features, config.bandRatio, ln)
        if (r.pathLength <= 0) return null
        val selfR = Dtw.withPath(template.features, template.features, config.bandRatio, ln)
        val expectedLen = if (selfR.pathLength > 0) selfR.pathLength.toDouble() else r.pathLength.toDouble()
        val deviation = kotlin.math.abs(r.pathLength - expectedLen) / expectedLen
        if (deviation > config.dualFilterTolerance) return null
        return r.distance.toFloat()
    }

    private fun distanceOrNull(query: FeatureSequence, template: Template, ln: (FloatArray, FloatArray) -> Double): Float? =
        if (config.dualFilterTolerance > 0.0) {
            dualFilteredDistance(query, template, ln)
        } else {
            Dtw.distance(query, template.features, config.bandRatio, ln).toFloat()
        }

    private fun distsPerCommand(query: FeatureSequence, templates: List<Template>): LinkedHashMap<CommandId, MutableList<TmplDist>> {
        val ln = localFn()
        val distsPerCommand = LinkedHashMap<CommandId, MutableList<TmplDist>>()
        for (template in templates) {
            if (template.features.coefficientCount != query.coefficientCount) continue
            val dist = distanceOrNull(query, template, ln)
            if (dist != null && dist.isFinite()) {
                distsPerCommand.getOrPut(template.commandId) { mutableListOf() }.add(TmplDist(template.id, dist))
            }
        }
        return distsPerCommand
    }

    private fun bestPerCommandAndTemplate(
        distsPerCommand: Map<CommandId, List<TmplDist>>,
    ): Pair<LinkedHashMap<CommandId, Float>, HashMap<CommandId, TemplateId>> {
        val bestPerCommand = LinkedHashMap<CommandId, Float>()
        val bestTemplate = HashMap<CommandId, TemplateId>()
        for ((cmd, tds) in distsPerCommand) {
            val sorted = tds.sortedBy { it.distance }
            bestTemplate[cmd] = sorted.first().templateId
            bestPerCommand[cmd] = sorted.take(config.kNN).map { it.distance }.average().toFloat()
        }
        return bestPerCommand to bestTemplate
    }

    private fun decideHysteresis(
        wCmd: CommandId,
        wDist: Float,
        rDist: Float?,
        threshold: Float,
        templateId: TemplateId,
    ): RecognitionResult {
        val tH = threshold * (1.0f + config.hysteresisZone.toFloat())
        val tL = threshold * (1.0f - config.hysteresisZone.toFloat())
        return when {
            wDist <= tL -> RecognitionResult.Match(wCmd, templateId, confidenceOf(wDist, rDist, threshold), wDist)
            wDist > tH -> RecognitionResult.NoMatch(RejectionReason.BELOW_CONFIDENCE, wDist, wCmd)
            else -> {
                val margin = if (rDist != null && rDist > 0f) (rDist - wDist) / rDist else 0f
                if (margin > 0.1f) {
                    RecognitionResult.Match(wCmd, templateId, confidenceOf(wDist, rDist, threshold), wDist)
                } else {
                    RecognitionResult.NoMatch(RejectionReason.BELOW_CONFIDENCE, wDist, wCmd)
                }
            }
        }
    }

    private fun enhancedMatch(
        query: FeatureSequence,
        templates: List<Template>,
        perCommandThresholds: Map<CommandId, Float>,
    ): RecognitionResult {
        val dists = distsPerCommand(query, templates)
        if (dists.isEmpty()) return RecognitionResult.NoMatch(RejectionReason.NO_TEMPLATES)

        val (bestPerCommand, bestTemplate) = bestPerCommandAndTemplate(dists)
        val ranked = bestPerCommand.entries.sortedBy { it.value }
        val winner = ranked.first()
        val wCmd = winner.key
        val wDist = winner.value
        val rDist = ranked.getOrNull(1)?.value
        val threshold = perCommandThresholds[wCmd] ?: config.defaultAcceptanceThreshold
        val templateId = bestTemplate[wCmd] ?: TemplateId("knn")

        if (config.hysteresisZone > 0.0) {
            return decideHysteresis(wCmd, wDist, rDist, threshold, templateId)
        }
        if (wDist > threshold) return RecognitionResult.NoMatch(RejectionReason.BELOW_CONFIDENCE, wDist, wCmd)
        return RecognitionResult.Match(wCmd, templateId, confidenceOf(wDist, rDist, threshold), wDist)
    }

    fun distance(a: FeatureSequence, b: FeatureSequence): Double = Dtw.distance(a, b, config.bandRatio, localFn())

    private data class Best(val templateId: TemplateId, val distance: Float)

    private fun localFn(): (FloatArray, FloatArray) -> Double = when (config.localDistance) {
        "cosine" -> Dtw::cosine
        else -> Dtw::euclidean
    }

    private fun confidenceOf(best: Float, runnerUp: Float?, threshold: Float): Float {
        val base = (1f - best / threshold).coerceIn(0f, 1f)
        val margin = if (runnerUp != null && runnerUp > 0f) {
            ((runnerUp - best) / runnerUp).coerceIn(0f, 1f)
        } else {
            1f
        }
        return ((1f - config.marginWeight) * base + config.marginWeight * margin).coerceIn(0f, 1f)
    }
}
