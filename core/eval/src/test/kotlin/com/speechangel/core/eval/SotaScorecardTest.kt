package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * Two tests:
 *  1. [`band mapping reproduces the committed table`] — a corpus-free unit test that the metric→band
 *     function ([DomainBands.bandFor]) reproduces the hand-authored "Composite SOTA band map" for the
 *     unambiguous committed values (the EVAL-004-style fidelity check: the doc is ground truth for the
 *     mapping, so the scorer's bands must match it before its live numbers are trusted).
 *  2. [`automated SOTA scorecard on real TORGO`] — gated on `-Dtorgo.dir`; runs [SotaScorecard],
 *     asserts it reproduces the committed shipped-static numbers (rank-1 ~59%, FRR ~76%) and that the
 *     wall-dominated composite is `<600`, then writes the reports. Skips (JUnit `Assume`) with no corpus.
 */
class SotaScorecardTest {

    @Test
    fun `band mapping reproduces the committed table`() {
        // D1 rank-1 (higher better): committed 59.2% → 600; ladder rungs.
        assertThat(DomainBands.bandFor(1, 0.592)).isEqualTo(600)
        assertThat(DomainBands.bandFor(1, 0.85)).isEqualTo(900)
        assertThat(DomainBands.bandFor(1, 0.96)).isEqualTo(1000)
        assertThat(DomainBands.bandFor(1, 0.50)).isEqualTo(DomainBands.BELOW_FLOOR)

        // D2 FRR (lower better): committed 75.7% → <600; 5% → 900; 0.4% → 1000.
        assertThat(DomainBands.bandFor(2, 0.757)).isEqualTo(DomainBands.BELOW_FLOOR)
        assertThat(DomainBands.bandFor(2, 0.05)).isEqualTo(900)
        assertThat(DomainBands.bandFor(2, 0.004)).isEqualTo(1000)

        // D3 ambient FA/hr (lower better, absolute): committed ~82 → <600; 0.4/hr → 800.
        assertThat(DomainBands.bandFor(3, 82.0)).isEqualTo(DomainBands.BELOW_FLOOR)
        assertThat(DomainBands.bandFor(3, 0.4)).isEqualTo(800)

        // D4 noise @ 20 dB (higher better): committed 56.1% → 600.
        assertThat(DomainBands.bandFor(4, 0.561)).isEqualTo(600)

        // D8 dual-cascade rel FRR reduction (higher better): banked 49.5% → 900.
        assertThat(DomainBands.bandFor(8, 0.495)).isEqualTo(900)

        // D9 SSL ceiling rank-1 (higher better): WavLM 71.9% → 800 (≥70 rung; the 900 rung is ≥75).
        assertThat(DomainBands.bandFor(9, 0.719)).isEqualTo(800)

        // D15 guardrail coverage (count_of_5, higher better): 0 → 600, 2 → 800, 3 → 900.
        assertThat(DomainBands.bandFor(15, 0.0)).isEqualTo(600)
        assertThat(DomainBands.bandFor(15, 2.0)).isEqualTo(800)
        assertThat(DomainBands.bandFor(15, 3.0)).isEqualTo(900)

        assertThat(DomainBands.bandLabel(DomainBands.BELOW_FLOOR)).isEqualTo("<600")
        assertThat(DomainBands.bandLabel(900)).isEqualTo("900")
    }

    @Test
    fun `guardrail coverage counts hard-gated EVAL rules`() {
        // Hermetic: a fixture rules file with two hard-gated rules → count 2 → band 800.
        val tmp = File.createTempFile("active-dev-rules", ".md")
        tmp.writeText(
            """
            ### EVAL-001 — never report bare-threshold FRR
            - **Gate:** advisory; TorgoEval.kt reference.
            ### EVAL-003 — pre-register one hypothesis
            - **Gate:** **hard** — verify-sota-measurement.mjs check 1 (banked-vs-exploratory label).
            ### EVAL-004 — reproduce the whole pipeline
            - **Gate:** **hard** — verify-sota-measurement.mjs check 3 (fidelity statement).

            ### EVAL guardrail promotion ladder
            | EVAL-005 | hard | (this is a TABLE row, not a rule Gate line — must NOT be counted) |
            ### EVAL-005 — extreme operating points are high-variance
            - **Gate:** advisory; in_regime.py reference.
            """.trimIndent(),
        )
        val count = SotaScorecard().countHardGatedEvalRules(tmp)
        assertThat(count).isEqualTo(2) // EVAL-003 + EVAL-004 only; the ladder table row is not a Gate line.
        assertThat(DomainBands.bandFor(15, count.toDouble())).isEqualTo(800)
        tmp.delete()
    }

    @Test
    fun `automated SOTA scorecard on real TORGO`() {
        val dir = System.getProperty("torgo.dir")
        assumeTrue("set -Dtorgo.dir to run the automated SOTA scorecard", dir != null && dir.isNotBlank())
        val root = File(dir)
        assertThat(root.isDirectory).isTrue()

        val ssl = System.getProperty("sota.ssl")?.let { File(it) }
        val rules = System.getProperty("sota.rules")?.let { File(it) }
        val scorer = SotaScorecard()
        val sc = scorer.run(root, ssl, rules)

        val d1 = sc.domains.first { it.id == 1 }
        val d2 = sc.domains.first { it.id == 2 }

        // Fidelity: shipped static-MFCC reproduces the committed floor (rank-1 59.2%, FRR 75.7%).
        assertThat(d1.value!!).isAtLeast(0.55)
        assertThat(d1.value!!).isAtMost(0.63)
        assertThat(d1.band).isEqualTo(600)
        assertThat(d2.value!!).isAtLeast(0.70)
        assertThat(d2.value!!).isAtMost(0.82)
        assertThat(d2.band).isEqualTo(DomainBands.BELOW_FLOOR)

        // Wall-dominated composite is <600 (FRR / ambient walls), never inflated by strong domains.
        assertThat(sc.bindingLabel).isEqualTo("<600")
        assertThat(sc.compositeDomains).isNotEmpty()

        // D15 guardrail coverage: measured from the rules file (≥2 hard-gated → ≥800), but structural —
        // NOT in the wall-dominated composite, so it never inflates the <600 headline.
        if (rules != null && rules.isFile) {
            val d15 = sc.domains.first { it.id == 15 }
            assertThat(d15.status).isEqualTo(SotaScorecard.Status.MEASURED)
            assertThat(d15.band).isAtLeast(800)
            assertThat(d15.countsForComposite).isFalse()
            assertThat(sc.compositeDomains.map { it.id }).doesNotContain(15)
        }

        val md = scorer.renderMarkdown(sc)
        val json = scorer.renderJson(sc)
        assertThat(md).contains("wall-dominated composite: **<600**")
        assertThat(md).contains("SIMULATED channel")
        assertThat(json).contains("\"bindingBand\": \"<600\"")

        val mdOut = File(System.getProperty("sota.report").orEmpty().ifBlank { "build/sota-scorecard.md" })
        val jsonOut = File(System.getProperty("sota.json").orEmpty().ifBlank { "build/sota-score.json" })
        mdOut.parentFile?.mkdirs()
        mdOut.writeText(md)
        jsonOut.writeText(json)
        println("SOTA scorecard written to ${mdOut.absolutePath} (+ ${jsonOut.absolutePath})")
        println(md)
    }
}
