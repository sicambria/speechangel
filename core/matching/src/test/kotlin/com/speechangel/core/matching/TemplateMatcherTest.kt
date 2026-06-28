package com.speechangel.core.matching

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.RejectionReason
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import org.junit.Test

class TemplateMatcherTest {

    private val matcher = TemplateMatcher(MatcherConfig(defaultAcceptanceThreshold = 5f))

    private fun seq(vararg frames: FloatArray) = FeatureSequence(frames.toList())

    private fun template(id: String, cmd: String, features: FeatureSequence) =
        Template(TemplateId(id), CommandId(cmd), features)

    private val commandA = seq(floatArrayOf(1f, 0f), floatArrayOf(1f, 0f), floatArrayOf(1f, 0f))
    private val commandB = seq(floatArrayOf(0f, 1f), floatArrayOf(0f, 1f), floatArrayOf(0f, 1f))

    private val templates = listOf(
        template("a1", "A", commandA),
        template("b1", "B", commandB),
    )

    @Test
    fun `query matching command A is recognised as A with high confidence`() {
        val result = matcher.match(commandA, templates)
        assertThat(result).isInstanceOf(RecognitionResult.Match::class.java)
        val match = result as RecognitionResult.Match
        assertThat(match.commandId).isEqualTo(CommandId("A"))
        assertThat(match.distance).isWithin(1e-5f).of(0f)
        assertThat(match.confidence).isGreaterThan(0.5f)
    }

    @Test
    fun `query matching command B is recognised as B`() {
        val result = matcher.match(commandB, templates)
        assertThat((result as RecognitionResult.Match).commandId).isEqualTo(CommandId("B"))
    }

    @Test
    fun `an out-of-vocabulary utterance is rejected, not forced onto a command`() {
        val garbage = seq(floatArrayOf(9f, 9f), floatArrayOf(9f, 9f), floatArrayOf(9f, 9f))
        val result = matcher.match(garbage, templates)
        assertThat(result).isInstanceOf(RecognitionResult.NoMatch::class.java)
        assertThat((result as RecognitionResult.NoMatch).reason).isEqualTo(RejectionReason.BELOW_CONFIDENCE)
    }

    @Test
    fun `no enrolled templates yields NO_TEMPLATES`() {
        val result = matcher.match(commandA, emptyList())
        assertThat((result as RecognitionResult.NoMatch).reason).isEqualTo(RejectionReason.NO_TEMPLATES)
    }

    @Test
    fun `empty query yields EMPTY_INPUT`() {
        val result = matcher.match(FeatureSequence(emptyList()), templates)
        assertThat((result as RecognitionResult.NoMatch).reason).isEqualTo(RejectionReason.EMPTY_INPUT)
    }

    @Test
    fun `multiple templates per command keep the best (closest) match`() {
        // A poor and a perfect template for command A; the perfect one must win.
        val poorA = template("a_poor", "A", seq(floatArrayOf(2f, 0f), floatArrayOf(2f, 0f), floatArrayOf(2f, 0f)))
        val perfectA = template("a_perfect", "A", commandA)
        val result = matcher.match(commandA, listOf(poorA, perfectA, template("b1", "B", commandB)))
        val match = result as RecognitionResult.Match
        assertThat(match.commandId).isEqualTo(CommandId("A"))
        assertThat(match.templateId).isEqualTo(TemplateId("a_perfect"))
    }

    @Test
    fun `per-command threshold override can tighten acceptance`() {
        // Global threshold accepts, but a strict per-command threshold rejects a non-perfect match.
        val nearA = seq(floatArrayOf(1.5f, 0f), floatArrayOf(1.5f, 0f), floatArrayOf(1.5f, 0f))
        val strict = mapOf(CommandId("A") to 0.1f)
        val result = matcher.match(nearA, templates, perCommandThresholds = strict)
        assertThat(result).isInstanceOf(RecognitionResult.NoMatch::class.java)
    }
}
