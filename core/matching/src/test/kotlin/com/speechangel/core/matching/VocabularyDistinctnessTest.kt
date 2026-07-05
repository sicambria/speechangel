package com.speechangel.core.matching

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import org.junit.Test

class VocabularyDistinctnessTest {

    private val matcher = TemplateMatcher()

    private fun seq(vararg frames: FloatArray) = FeatureSequence(frames.toList())
    private fun t(id: String, cmd: String, s: FeatureSequence) = Template(TemplateId(id), CommandId(cmd), s)

    // A command whose two templates vary a little (so it has a real intra-command spread).
    private fun commandX(cmd: String, base: Float) = listOf(
        t("$cmd-1", cmd, seq(floatArrayOf(base, 0f), floatArrayOf(base, 0f))),
        t("$cmd-2", cmd, seq(floatArrayOf(base + 1f, 0f), floatArrayOf(base + 1f, 0f))),
    )

    @Test
    fun `two acoustically close commands are flagged`() {
        // "X" around 0 and "Y" around 0.1 — nearly the same trajectory; well inside X's own spread (~1).
        val commands = mapOf(
            CommandId("X") to commandX("X", 0f),
            CommandId("Y") to listOf(t("Y-1", "Y", seq(floatArrayOf(0.1f, 0f), floatArrayOf(0.1f, 0f)))),
        )
        val pairs = VocabularyDistinctness.analyze(commands, matcher)
        assertThat(pairs).hasSize(1)
        assertThat(setOf(pairs[0].a, pairs[0].b)).containsExactly(CommandId("X"), CommandId("Y"))
        assertThat(pairs[0].severity).isEqualTo(DistinctnessSeverity.WARN)
    }

    @Test
    fun `two well-separated commands are not flagged`() {
        val commands = mapOf(
            CommandId("Near") to commandX("Near", 0f),
            CommandId("Far") to listOf(t("Far-1", "Far", seq(floatArrayOf(20f, 20f), floatArrayOf(20f, 20f)))),
        )
        assertThat(VocabularyDistinctness.analyze(commands, matcher)).isEmpty()
    }

    @Test
    fun `empty vocabulary and a single command yield no pairs`() {
        assertThat(VocabularyDistinctness.analyze(emptyMap(), matcher)).isEmpty()
        val single = mapOf(CommandId("Only") to commandX("Only", 0f))
        assertThat(VocabularyDistinctness.analyze(single, matcher)).isEmpty()
    }

    @Test
    fun `results are deterministic and ordered most-confusable first`() {
        val commands = mapOf(
            CommandId("A") to commandX("A", 0f),
            CommandId("B") to listOf(t("B-1", "B", seq(floatArrayOf(0.2f, 0f), floatArrayOf(0.2f, 0f)))),
            CommandId("C") to listOf(t("C-1", "C", seq(floatArrayOf(0.05f, 0f), floatArrayOf(0.05f, 0f)))),
        )
        val first = VocabularyDistinctness.analyze(commands, matcher)
        val second = VocabularyDistinctness.analyze(commands, matcher)
        assertThat(first).isEqualTo(second)
        // Ascending by distance.
        val distances = first.map { it.distance }
        assertThat(distances).isEqualTo(distances.sorted())
    }

    @Test
    fun `a shared-onset minimal pair is flagged even when tails diverge`() {
        // Both start with the same onset frames, then diverge. Give each two templates so a spread
        // exists; the onset check should surface the collision.
        val m = listOf(
            t("M-1", "M", seq(floatArrayOf(3f, 0f), floatArrayOf(3f, 0f), floatArrayOf(0f, 1f), floatArrayOf(0f, 1f))),
            t("M-2", "M", seq(floatArrayOf(3f, 0f), floatArrayOf(3f, 0f), floatArrayOf(0f, 2f), floatArrayOf(0f, 2f))),
        )
        val n = listOf(
            t("N-1", "N", seq(floatArrayOf(3f, 0f), floatArrayOf(3f, 0f), floatArrayOf(0f, 9f), floatArrayOf(0f, 9f))),
            t("N-2", "N", seq(floatArrayOf(3f, 0f), floatArrayOf(3f, 0f), floatArrayOf(9f, 0f), floatArrayOf(9f, 0f))),
        )
        val commands = mapOf(CommandId("M") to m, CommandId("N") to n)
        val pairs = VocabularyDistinctness.analyze(commands, matcher, onsetFrames = 2)
        assertThat(pairs.map { setOf(it.a, it.b) }).contains(setOf(CommandId("M"), CommandId("N")))
    }
}
