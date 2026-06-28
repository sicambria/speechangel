package com.speechangel.core.enrollment

import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId

/** What confirmation-gated adaptation should do: add the confirmed example, remove any displaced ones. */
data class AdaptationDecision(val toAdd: Template, val toRemove: List<TemplateId>)

/**
 * Pure, deterministic decision for confirmation-gated re-enrollment (Phase 2). Always adds [candidate].
 * If that would exceed [maxPerCommand], removes exactly one template from [existing] (the just-added
 * candidate is NEVER eligible), chosen ONLY from a `VoiceCondition` bucket with ≥ 2 members — so a
 * condition's sole example is never evicted, preserving voice-drift robustness.
 *
 * Selection: the **most redundant** template = smallest minimum pairwise [distance] to its siblings.
 * Tie-break: oldest `createdAtEpochMs`, then `TemplateId.value` (a total order → fully deterministic).
 *
 * `require(maxPerCommand >= 4)` guarantees that with ≤ 4 conditions a ≥ 2 bucket always exists once the
 * cap is exceeded (pigeonhole over `existing.size = maxPerCommand` items), so a victim is always found.
 */
fun decideAdaptation(
    existing: List<Template>,
    candidate: Template,
    maxPerCommand: Int = 5,
    distance: (FeatureSequence, FeatureSequence) -> Double,
): AdaptationDecision {
    require(maxPerCommand >= 4) { "maxPerCommand must be >= 4 so a sole-condition example is never evicted" }
    if (existing.size + 1 <= maxPerCommand) return AdaptationDecision(candidate, emptyList())

    val bucketSize = existing.groupingBy { it.condition }.eachCount()
    val eligible = existing.filter { (bucketSize[it.condition] ?: 0) >= 2 }

    val victim = eligible.minWithOrNull(
        compareBy(
            { t -> minPairwiseDistance(t, existing, distance) },
            { t -> t.createdAtEpochMs },
            { t -> t.id.value },
        ),
    )
    return AdaptationDecision(candidate, victim?.let { listOf(it.id) } ?: emptyList())
}

/** Smallest DTW distance from [t] to any other template in [all] (a redundancy score; lower = more redundant). */
private fun minPairwiseDistance(t: Template, all: List<Template>, distance: (FeatureSequence, FeatureSequence) -> Double): Double =
    all.asSequence()
        .filter { it.id != t.id }
        .map { distance(t.features, it.features) }
        .minOrNull() ?: Double.MAX_VALUE
