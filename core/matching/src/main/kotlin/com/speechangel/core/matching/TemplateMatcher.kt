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
data class MatcherConfig(val defaultAcceptanceThreshold: Float = 8.0f, val bandRatio: Double = 0.1, val marginWeight: Float = 0.4f)

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

        // Best template (min distance) for each command.
        val bestPerCommand = HashMap<CommandId, Best>()
        for (template in templates) {
            if (template.features.coefficientCount != query.coefficientCount) continue
            val dist = Dtw.distance(query, template.features, config.bandRatio).toFloat()
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
            return RecognitionResult.NoMatch(
                reason = RejectionReason.BELOW_CONFIDENCE,
                bestDistance = winnerBest.distance,
                nearestCommandId = winnerCommand,
            )
        }

        return RecognitionResult.Match(
            commandId = winnerCommand,
            templateId = winnerBest.templateId,
            confidence = confidenceOf(winnerBest.distance, runnerUp, threshold),
            distance = winnerBest.distance,
        )
    }

    fun distance(a: FeatureSequence, b: FeatureSequence): Double = Dtw.distance(a, b, config.bandRatio)

    private fun confidenceOf(best: Float, runnerUp: Float?, threshold: Float): Float {
        val base = (1f - best / threshold).coerceIn(0f, 1f)
        val margin = if (runnerUp != null && runnerUp > 0f) {
            ((runnerUp - best) / runnerUp).coerceIn(0f, 1f)
        } else {
            1f
        }
        return ((1f - config.marginWeight) * base + config.marginWeight * margin).coerceIn(0f, 1f)
    }

    private data class Best(val templateId: TemplateId, val distance: Float)
}
