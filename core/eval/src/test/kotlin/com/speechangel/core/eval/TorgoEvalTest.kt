package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * Runs the real TORGO evaluation when `-Dtorgo.dir=<extracted speaker-set root>` is supplied, and
 * writes the rendered report to `-Dtorgo.report=<path>` (default `build/torgo-report.md`).
 *
 * When `torgo.dir` is **unset** the test is skipped (JUnit `Assume`), so `:core:eval:test` stays
 * green on any host without the multi-GB corpus — the corpus is `[measure-only]` and never committed.
 */
class TorgoEvalTest {

    @Test
    fun `real TORGO run produces a non-synthetic FRR report`() {
        val dir = System.getProperty("torgo.dir")
        assumeTrue("set -Dtorgo.dir to run the real TORGO evaluation", dir != null && dir.isNotBlank())

        val root = File(dir)
        assertThat(root.isDirectory).isTrue()

        // Optional front-end override so the trusted path can be read on the SHIPPED static front-end
        // (`-Dtorgo.frontend=none`) — a cross-check against the per-speaker rejection machinery.
        val eval = when (System.getProperty("torgo.frontend")) {
            "none" -> TorgoEval(
                FeatureFrontEnd("none", com.speechangel.core.dsp.MfccConfig(deltaOrder = com.speechangel.core.dsp.DeltaOrder.NONE)),
            )
            "delta" -> TorgoEval(
                FeatureFrontEnd("delta", com.speechangel.core.dsp.MfccConfig(deltaOrder = com.speechangel.core.dsp.DeltaOrder.DELTA)),
            )
            else -> TorgoEval()
        }
        val result = eval.run(root)
        assertThat(result.perSpeaker).isNotEmpty()
        assertThat(result.aggregate.positives).isGreaterThan(0)
        assertThat(result.aggregate.rank1).isAtLeast(0.0)
        assertThat(result.aggregate.rank1).isAtMost(1.0)

        // Held-out realism check (EVAL-002): held-out FRR must not be optimistically BELOW the in-sample
        // reference by more than sampling noise (a large negative gap signals a leaked split).
        assertThat(result.aggregate.frrLowFarGlobalHeldOut)
            .isAtLeast(result.aggregate.frrAtLowFarInSample - 0.15)

        var report = eval.render(result)

        // D3 — front-end bake-off grid (opt-in: expensive, one full k-fold run per cell).
        if (System.getProperty("torgo.grid")?.toBoolean() == true) {
            report += "\n" + eval.renderFrontEndGrid(eval.frontEndGrid(root))
        }

        assertThat(report).doesNotContain("SYNTHETIC")

        val out = File(System.getProperty("torgo.report").orEmpty().ifBlank { "build/torgo-report.md" })
        out.parentFile?.mkdirs()
        out.writeText(report)
        println("TORGO report written to ${out.absolutePath}")
        println(report)
    }

    /**
     * Realistic-condition simulation + the pre-registered common-mode rejection adjudication, on the
     * SHIPPED front-end (`deltaOrder=NONE`). Opt-in via `-Dtorgo.reject=true`. `-Dtorgo.conditions=true`
     * additionally runs the (expensive) noise/reverb grid; `-Dambient.wav=<file>` swaps the synthetic
     * ambient proxy for a real recording. Writes to `-Dtorgo.sim.report` (default `build/sim-report.md`).
     */
    @Test
    fun `rejection-score and condition simulation on real TORGO`() {
        val dir = System.getProperty("torgo.dir")
        assumeTrue("set -Dtorgo.dir to run", dir != null && dir.isNotBlank())
        assumeTrue(
            "set -Dtorgo.reject=true to run the simulation + rejection adjudication",
            System.getProperty("torgo.reject")?.toBoolean() == true,
        )

        val root = File(dir)
        val runConditions = System.getProperty("torgo.conditions")?.toBoolean() == true
        val ambientWav = System.getProperty("ambient.wav")?.let { File(it) }

        val report = SimReport().render(root, runConditions = runConditions, ambientWav = ambientWav)
        assertThat(report).contains("McNemar")

        val out = File(System.getProperty("torgo.sim.report").orEmpty().ifBlank { "build/sim-report.md" })
        out.parentFile?.mkdirs()
        out.writeText(report)
        println("Sim report written to ${out.absolutePath}")
        println(report)
    }
}
