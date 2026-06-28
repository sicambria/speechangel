package com.speechangel.core.enrollment

import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCondition

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
 * `require(maxPerCommand > VoiceCondition.entries.size)` is what makes the contract satisfiable: only
 * when the cap strictly exceeds the number of conditions does pigeonhole guarantee that, at the cap,
 * some condition bucket has ≥ 2 members — so a non-sole victim always exists. (A `>= 4` bound was a
 * latent off-by-one: 4 templates in 4 distinct conditions at `maxPerCommand = 4` left `eligible`
 * empty and silently exceeded the cap.) The trailing `check` is a defence-in-depth tripwire so any
 * future weakening of the precondition fails loudly instead of silently growing the template set.
 */
fun decideAdaptation(
    existing: List<Template>,
    candidate: Template,
    maxPerCommand: Int = 5,
    distance: (FeatureSequence, FeatureSequence) -> Double,
): AdaptationDecision {
    require(maxPerCommand > VoiceCondition.entries.size) {
        "maxPerCommand ($maxPerCommand) must exceed the number of VoiceConditions " +
            "(${VoiceCondition.entries.size}) so a non-sole victim always exists at the cap"
    }
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
    val decision = AdaptationDecision(candidate, victim?.let { listOf(it.id) } ?: emptyList())
    check(existing.size + 1 - decision.toRemove.size <= maxPerCommand) {
        "adaptation would exceed cap $maxPerCommand: ${existing.size} existing + candidate, " +
            "${decision.toRemove.size} removed (no eligible ≥2 bucket found)"
    }
    return decision
}

/** Smallest DTW distance from [t] to any other template in [all] (a redundancy score; lower = more redundant). */
private fun minPairwiseDistance(t: Template, all: List<Template>, distance: (FeatureSequence, FeatureSequence) -> Double): Double =
    all.asSequence()
        .filter { it.id != t.id }
        .map { distance(t.features, it.features) }
        .minOrNull() ?: Double.MAX_VALUE
