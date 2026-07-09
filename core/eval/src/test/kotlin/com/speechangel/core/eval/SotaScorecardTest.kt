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

        // D7 in-regime detection (higher better): 0.90 rung → 950; floor 0.50 → 600; below → <600.
        assertThat(DomainBands.bandFor(7, 0.9375)).isEqualTo(950)
        assertThat(DomainBands.bandFor(7, 0.50)).isEqualTo(600)
        assertThat(DomainBands.bandFor(7, 0.49)).isEqualTo(DomainBands.BELOW_FLOOR)

        // D11 latency P50 ms (lower better): 150 → 900; 1000 → 600; 40 → 1000; 1001 → <600.
        assertThat(DomainBands.bandFor(11, 150.0)).isEqualTo(900)
        assertThat(DomainBands.bandFor(11, 1000.0)).isEqualTo(600)
        assertThat(DomainBands.bandFor(11, 40.0)).isEqualTo(1000)
        assertThat(DomainBands.bandFor(11, 1001.0)).isEqualTo(DomainBands.BELOW_FLOOR)

        // D12 battery %/hr (lower better): 2 → 1000; 8 → 900; 30 → 600; 31 → <600.
        assertThat(DomainBands.bandFor(12, 2.0)).isEqualTo(1000)
        assertThat(DomainBands.bandFor(12, 8.0)).isEqualTo(900)
        assertThat(DomainBands.bandFor(12, 30.0)).isEqualTo(600)
        assertThat(DomainBands.bandFor(12, 31.0)).isEqualTo(DomainBands.BELOW_FLOOR)

        // D13 enrollment efficiency (higher better): 0.60 → 600; 0.86 → 900; 1.0 → 1000; 0.59 → <600.
        assertThat(DomainBands.bandFor(13, 0.60)).isEqualTo(600)
        assertThat(DomainBands.bandFor(13, 0.86)).isEqualTo(900)
        assertThat(DomainBands.bandFor(13, 1.0)).isEqualTo(1000)
        assertThat(DomainBands.bandFor(13, 0.59)).isEqualTo(DomainBands.BELOW_FLOOR)

        assertThat(DomainBands.bandLabel(DomainBands.BELOW_FLOOR)).isEqualTo("<600")
        assertThat(DomainBands.bandLabel(900)).isEqualTo("900")
    }

    @Test
    fun `battery model is a deterministic first-principles function of decide latency`() {
        val model = BatteryModel()
        // Zero compute → baseline-only draw = P_BASELINE_W / BATTERY_WH × 100.
        val idle = model.estimate(0.0)
        assertThat(idle.dutyCycle).isEqualTo(0.0)
        assertThat(idle.pctPerHour).isWithin(0.05).of(BatteryModel.P_BASELINE_W / BatteryModel.BATTERY_WH * 100.0)
        // A real-time decide (RTF=1 over the avg utterance) adds P_ACTIVE_W × SPEECH_DUTY.
        val busy = model.estimate(BatteryModel.AVG_UTTERANCE_MS)
        assertThat(busy.dutyCycle).isWithin(1e-9).of(BatteryModel.SPEECH_DUTY)
        val expectedW = BatteryModel.P_BASELINE_W + BatteryModel.P_ACTIVE_W * BatteryModel.SPEECH_DUTY
        assertThat(busy.pctPerHour).isWithin(0.05).of(expectedW / BatteryModel.BATTERY_WH * 100.0)
        // Monotonic in latency; band lands in the plausible on-device range (not <600).
        assertThat(busy.pctPerHour).isGreaterThan(idle.pctPerHour)
        assertThat(DomainBands.bandFor(12, busy.pctPerHour)).isAtLeast(600)
    }

    @Test
    fun `automated SOTA scorecard on real TORGO`() {
        val dir = System.getProperty("torgo.dir")
        assumeTrue("set -Dtorgo.dir to run the automated SOTA scorecard", dir != null && dir.isNotBlank())
        val root = File(dir)
        assertThat(root.isDirectory).isTrue()

        val ssl = System.getProperty("sota.ssl")?.let { File(it) }
        val scorer = SotaScorecard()
        val sc = scorer.run(root, ssl)

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

        // D11/D12/D13 now land a band from JVM harnesses (no device, no torch).
        val d11 = sc.domains.first { it.id == 11 }
        val d12 = sc.domains.first { it.id == 12 }
        val d13 = sc.domains.first { it.id == 13 }
        assertThat(d11.value).isNotNull()
        assertThat(d11.status).isEqualTo(SotaScorecard.Status.SIMULATED_DEVICE)
        assertThat(d12.value).isNotNull()
        assertThat(d12.status).isEqualTo(SotaScorecard.Status.SIMULATED_DEVICE)
        assertThat(d13.value).isNotNull()
        assertThat(d13.status).isEqualTo(SotaScorecard.Status.MEASURED)

        // Counting invariant: only measurement-backed domains set the wall. Host-scaled/derived
        // (D11/D12) and confounded (D14) are excluded; D13 (real TORGO sweep) counts.
        val compositeIds = sc.compositeDomains.map { it.id }.toSet()
        assertThat(compositeIds).containsNoneOf(11, 12, 14)
        assertThat(compositeIds).contains(13)

        // D10 stays NOT_MEASURED — single-read Common Voice yields no valid rank-1 proxy (advisor-gated);
        // language independence is argued by-construction in the docs, never banded from noise.
        val d10 = sc.domains.first { it.id == 10 }
        assertThat(d10.status).isEqualTo(SotaScorecard.Status.NOT_MEASURED)
        assertThat(d10.value).isNull()
        assertThat(compositeIds).doesNotContain(10)

        val md = scorer.renderMarkdown(sc)
        val json = scorer.renderJson(sc)
        assertThat(md).contains("wall-dominated composite: **<600**")
        assertThat(md).contains("SIMULATED channel")
        assertThat(md).contains("excluded from the composite")
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
