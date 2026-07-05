package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import org.junit.Test

class EvalReportTest {

    private val a = CommandId("A")
    private val b = CommandId("B")

    @Test
    fun `known inputs produce known FRR and false-accept counts`() {
        val rows = listOf(
            // positive A, correctly recognised (A is argmin, under the 8.0 default).
            DistanceRow(a, VoiceCondition.NORMAL, 700, mapOf(a to 1.0f, b to 5.0f)),
            // positive A, substituted to B (A=9 > 8 rejects A; B=5 wins) -> counted as false reject.
            DistanceRow(a, VoiceCondition.NORMAL, 700, mapOf(a to 9.0f, b to 5.0f)),
            // negative accepted as A (2 <= 8) -> false accept.
            DistanceRow(null, VoiceCondition.NORMAL, 700, mapOf(a to 2.0f)),
            // negative correctly rejected (12 > 8).
            DistanceRow(null, VoiceCondition.NORMAL, 700, mapOf(a to 12.0f)),
        )
        val r = EvalReport.from("static", rows, emptyMap(), defaultThreshold = 8.0f, enrollmentFailures = 0)

        assertThat(r.positives).isEqualTo(2)
        assertThat(r.negatives).isEqualTo(2)
        assertThat(r.falseRejects).isEqualTo(1)
        assertThat(r.frr).isWithin(1e-6).of(0.5)
        assertThat(r.falseAccepts).isEqualTo(1)
        assertThat(r.negativeAudioSeconds).isWithin(1e-6).of(1.4)
        assertThat(r.render()).contains("SYNTHETIC")
    }

    @Test
    fun `per-command threshold override changes the decision`() {
        val rows = listOf(
            // A=2 would be accepted at default 8, but a tight per-command threshold of 1 rejects it.
            DistanceRow(null, VoiceCondition.NORMAL, 700, mapOf(a to 2.0f)),
        )
        val loose = EvalReport.from("x", rows, emptyMap(), 8.0f, 0)
        val tight = EvalReport.from("x", rows, mapOf(a to 1.0f), 8.0f, 0)
        assertThat(loose.falseAccepts).isEqualTo(1)
        assertThat(tight.falseAccepts).isEqualTo(0)
    }
}

class SyntheticPipelineTest {

    private val corpus = SyntheticCorpus.build()

    @Test
    fun `synthetic enrollment samples all survive VAD and enroll under every front-end`() {
        for (fe in SyntheticCorpus.frontEnds()) {
            val outcome = Evaluator(fe).enroll(corpus)
            assertThat(outcome.failures).isEmpty()
            assertThat(outcome.templates).hasSize(corpus.enrollment.size)
        }
    }

    @Test
    fun `positives produce non-empty distance rows (guards the steady-tone trap)`() {
        val fe = SyntheticCorpus.frontEnds().first()
        val ev = Evaluator(fe)
        val rows = ev.distanceTable(corpus, ev.enroll(corpus).templates)
        val positives = rows.filter { it.truth != null }
        assertThat(positives).isNotEmpty()
        assertThat(positives.all { it.bestByCommand.isNotEmpty() }).isTrue()
    }

    @Test
    fun `bake-off produces a populated row per front-end (computes, does not assert a winner)`() {
        val report = FrontEndBakeoff(SyntheticCorpus.frontEnds()).run(corpus)
        assertThat(report.rows.map { it.name }).containsExactly("static", "delta", "delta_delta")
        assertThat(report.rows.all { it.frr in 0.0..1.0 }).isTrue()
        assertThat(report.render()).contains("bake-off")
    }

    @Test
    fun `noise-robust bake-off computes baseline vs spectral-subtraction (no winner asserted)`() {
        val report = FrontEndBakeoff(SyntheticCorpus.noiseRobustFrontEnds()).run(corpus)
        assertThat(report.rows.map { it.name }).containsExactly("baseline", "spectral_subtraction")
        assertThat(report.rows.all { it.frr in 0.0..1.0 }).isTrue()
        // Both columns are populated; which one wins is a Bucket-B, real-audio decision, not asserted.
    }

    @Test
    fun `calibration returns a threshold per command and never increases false accepts`() {
        val fe = SyntheticCorpus.frontEnds().first()
        val cal = ThresholdCalibrator(fe).calibrate(corpus)
        assertThat(cal.thresholds.keys).containsExactlyElementsIn(corpus.commands)
        assertThat(cal.budgetFalseAccepts).isAtLeast(1)
        val default = Evaluator(fe).evaluate(corpus)
        assertThat(cal.report.falseAccepts).isAtMost(default.falseAccepts)
    }
}
