package com.speechangel.core.matching

import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template

/** How strongly a command pair is flagged as acoustically close. */
enum class DistinctnessSeverity { NUDGE, WARN }

/**
 * Two enrolled commands that a caregiver may want to make more distinct. [distance] is the smallest
 * length-normalised DTW distance found between any template of [a] and any template of [b] (lower =
 * more confusable). [a] and [b] are ordered by [CommandId.value] so a pair is reported once.
 */
data class ClosePair(val a: CommandId, val b: CommandId, val distance: Float, val severity: DistinctnessSeverity)

/**
 * Vocabulary-distinctness helper (Phase 3): warns at enrollment time when two commands are
 * acoustically close, so the caregiver can pick a more distinct word *before* the confusion shows up
 * in the field. It is purely advisory — it never blocks enrollment and never touches the matcher.
 *
 * The metric is **scale-relative**: the cross-command minimum DTW distance is compared against each
 * command's own intra-command spread (how much that command's own templates already vary), not an
 * absolute magic number — so it adapts to the speaker and the front-end. When a command has only one
 * template (no intra spread), an absolute fallback distance sets the scale.
 *
 * A light **shared-onset** check (the first frames only) additionally catches minimal pairs like
 * "call / carl" whose whole-utterance DTW is only moderate but whose onsets collide.
 */
object VocabularyDistinctness {

    /**
     * @param commands enrolled templates grouped by command (typically the full vocabulary).
     * @param matcher supplies the same length-normalised DTW distance the recogniser uses.
     * @param closeRatio a pair is flagged when its cross distance is below `closeRatio × spread`.
     * @param absoluteCloseDistance scale used when neither command has an intra-command spread.
     * @param onsetFrames number of leading frames compared for the shared-onset check.
     * @param onsetRatio the (tighter) ratio at which a shared onset alone flags a pair.
     * @return flagged pairs, most-confusable first (ascending [ClosePair.distance]), deterministic.
     */
    fun analyze(
        commands: Map<CommandId, List<Template>>,
        matcher: TemplateMatcher,
        closeRatio: Float = 0.6f,
        absoluteCloseDistance: Float = 4.0f,
        onsetFrames: Int = 8,
        onsetRatio: Float = 0.35f,
    ): List<ClosePair> {
        val ids = commands.keys.sortedBy { it.value }
        val intra = ids.associateWith { intraSpread(commands.getValue(it)) }
        val out = ArrayList<ClosePair>()

        for (i in ids.indices) {
            for (j in i + 1 until ids.size) {
                evaluatePair(ids[i], ids[j], commands, matcher, intra, closeRatio, absoluteCloseDistance, onsetFrames, onsetRatio)
                    ?.let { out += it }
            }
        }
        return out.sortedWith(compareBy({ it.distance }, { it.a.value }, { it.b.value }))
    }

    /** Evaluates one unordered command pair; returns a [ClosePair] when flagged, else null. */
    @Suppress("LongParameterList")
    private fun evaluatePair(
        idA: CommandId,
        idB: CommandId,
        commands: Map<CommandId, List<Template>>,
        matcher: TemplateMatcher,
        intra: Map<CommandId, Float?>,
        closeRatio: Float,
        absoluteCloseDistance: Float,
        onsetFrames: Int,
        onsetRatio: Float,
    ): ClosePair? {
        val tsA = commands.getValue(idA)
        val tsB = commands.getValue(idB)

        val cross = crossMin(tsA, tsB) { a, b -> safeDistance(matcher, a, b) }
        if (cross.isInfinite()) return null // no comparable (equal-width) template pair

        // Scale relative to how much these commands' own templates already vary; if neither has a
        // spread (both single-template), fall back to an absolute distance scale.
        val spreads = listOfNotNull(intra[idA], intra[idB])
        val reference = if (spreads.isNotEmpty()) spreads.average().toFloat() else absoluteCloseDistance / closeRatio

        val onset = crossMin(tsA, tsB) { a, b -> safeDistance(matcher, onset(a, onsetFrames), onset(b, onsetFrames)) }

        val crossFlags = cross < closeRatio * reference
        val onsetFlags = onset < onsetRatio * reference
        if (!crossFlags && !onsetFlags) return null

        val severity = if (crossFlags && cross < (closeRatio / 2f) * reference) {
            DistinctnessSeverity.WARN
        } else {
            DistinctnessSeverity.NUDGE
        }
        return ClosePair(idA, idB, cross, severity)
    }

    /** Mean pairwise DTW distance among a command's own templates; null when it has fewer than two. */
    private fun intraSpread(templates: List<Template>): Float? {
        if (templates.size < 2) return null
        var sum = 0.0
        var count = 0
        for (i in templates.indices) {
            for (j in i + 1 until templates.size) {
                val d = safeDistance(templates[i].features, templates[j].features)
                if (d.isFinite()) {
                    sum += d
                    count++
                }
            }
        }
        return if (count == 0) null else (sum / count).toFloat()
    }

    private inline fun crossMin(a: List<Template>, b: List<Template>, dist: (FeatureSequence, FeatureSequence) -> Float): Float {
        var best = Float.POSITIVE_INFINITY
        for (ta in a) {
            for (tb in b) {
                val d = dist(ta.features, tb.features)
                if (d < best) best = d
            }
        }
        return best
    }

    private fun onset(seq: FeatureSequence, frames: Int): FeatureSequence =
        if (seq.frameCount <= frames) seq else FeatureSequence(seq.frames.subList(0, frames))

    private fun safeDistance(matcher: TemplateMatcher, a: FeatureSequence, b: FeatureSequence): Float =
        if (a.coefficientCount != b.coefficientCount || a.isEmpty || b.isEmpty) {
            Float.POSITIVE_INFINITY
        } else {
            matcher.distance(a, b).toFloat()
        }

    // Intra-command spread uses the default band directly (no matcher needed for the private path).
    private fun safeDistance(a: FeatureSequence, b: FeatureSequence): Float =
        if (a.coefficientCount != b.coefficientCount || a.isEmpty || b.isEmpty) {
            Float.POSITIVE_INFINITY
        } else {
            Dtw.distance(a, b).toFloat()
        }
}
