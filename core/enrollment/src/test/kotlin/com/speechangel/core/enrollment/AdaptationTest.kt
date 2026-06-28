package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCondition
import org.junit.Test

class AdaptationTest {

    private val cmd = CommandId("c")

    // 1-D feature so a simple absolute-difference stands in for DTW distance.
    private fun tmpl(id: String, condition: VoiceCondition, value: Float, created: Long): Template =
        Template(TemplateId(id), cmd, FeatureSequence(listOf(floatArrayOf(value))), condition, created)

    private val dist: (FeatureSequence, FeatureSequence) -> Double = { a, b ->
        kotlin.math.abs(a.frames[0][0] - b.frames[0][0]).toDouble()
    }

    @Test
    fun `under the cap nothing is removed`() {
        val existing = listOf(tmpl("a", VoiceCondition.NORMAL, 0f, 1))
        val decision = decideAdaptation(existing, tmpl("new", VoiceCondition.NORMAL, 1f, 2), maxPerCommand = 5, distance = dist)
        assertThat(decision.toRemove).isEmpty()
        assertThat(decision.toAdd.id.value).isEqualTo("new")
    }

    @Test
    fun `at the cap the most redundant template in a multi-member bucket is pruned`() {
        // NORMAL bucket has the near-duplicate pair (0.0, 0.1); TIRED, ILL, OTHER are sole-condition.
        val existing = listOf(
            tmpl("n1", VoiceCondition.NORMAL, 0.0f, 10),
            tmpl("n2", VoiceCondition.NORMAL, 0.1f, 20),
            tmpl("tired", VoiceCondition.TIRED, 5.0f, 30),
            tmpl("ill", VoiceCondition.ILL, 9.0f, 40),
            tmpl("other", VoiceCondition.OTHER, 13.0f, 45),
        )
        val decision = decideAdaptation(existing, tmpl("new", VoiceCondition.NORMAL, 0.05f, 50), maxPerCommand = 5, distance = dist)
        // The redundant pair tie (both min-pairwise 0.1) breaks to the oldest -> n1.
        assertThat(decision.toRemove).containsExactly(TemplateId("n1"))
    }

    @Test
    fun `pruning never evicts a sole-condition example`() {
        val existing = listOf(
            tmpl("n1", VoiceCondition.NORMAL, 0.0f, 10),
            tmpl("n2", VoiceCondition.NORMAL, 0.1f, 20),
            tmpl("n3", VoiceCondition.NORMAL, 0.2f, 30),
            tmpl("ill", VoiceCondition.ILL, 9.0f, 40),
            tmpl("tired", VoiceCondition.TIRED, 5.0f, 45),
        )
        repeat(20) {
            val decision = decideAdaptation(existing, tmpl("new", VoiceCondition.NORMAL, 0.05f, 50), maxPerCommand = 5, distance = dist)
            assertThat(decision.toRemove).doesNotContain(TemplateId("ill"))
            assertThat(decision.toRemove).doesNotContain(TemplateId("tired"))
        }
    }

    @Test
    fun `maxPerCommand at or below the number of conditions is rejected`() {
        val existing = listOf(tmpl("a", VoiceCondition.NORMAL, 0f, 1))
        // maxPerCommand == VoiceCondition count is unsafe: N templates in N distinct conditions can't
        // be pruned without evicting a sole example, so it must be rejected (the latent-bug boundary).
        for (bad in listOf(3, VoiceCondition.entries.size)) {
            try {
                decideAdaptation(existing, tmpl("new", VoiceCondition.NORMAL, 1f, 2), maxPerCommand = bad, distance = dist)
                error("expected IllegalArgumentException for maxPerCommand=$bad")
            } catch (e: IllegalArgumentException) {
                assertThat(e).hasMessageThat().contains("maxPerCommand")
            }
        }
    }

    @Test
    fun `at the cap with every condition distinct a victim is always found`() {
        // Regression guard for the off-by-one: spread templates as thinly as possible across all
        // conditions at the cap. Pigeonhole still forces one bucket to >=2, so a victim MUST exist and
        // the cap MUST hold -- under the old `>= 4` guard with distinct conditions this returned empty.
        val conditions = VoiceCondition.entries
        val maxPerCommand = conditions.size + 1
        val existing = (0 until maxPerCommand).map { i ->
            tmpl("t$i", conditions[i % conditions.size], i.toFloat(), i.toLong())
        }
        val decision =
            decideAdaptation(existing, tmpl("new", VoiceCondition.NORMAL, 0.5f, 999), maxPerCommand = maxPerCommand, distance = dist)
        assertThat(decision.toRemove).hasSize(1)
        assertThat(existing.size + 1 - decision.toRemove.size).isAtMost(maxPerCommand)
    }
}
