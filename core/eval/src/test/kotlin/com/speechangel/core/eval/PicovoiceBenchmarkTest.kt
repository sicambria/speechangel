package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * Runs the SpeechAngel placement on the Picovoice wake-word-benchmark when
 * `-Dpicovoice.dir=<root>` points at a tree provisioned by `scripts/eval/fetch-picovoice-benchmark.sh`.
 * Writes the report to `-Dpicovoice.report` (default `build/picovoice-report.md`).
 *
 * Optional props: `-Dpicovoice.bgSeconds` (background per keyword, default 900),
 * `-Dpicovoice.enroll` (enroll takes/keyword, default 10), `-Dpicovoice.held` (held-out cap, default 40),
 * `-Dpicovoice.dump=<dir>` writes each `<keyword>_speech.wav` + `_label.txt` for the PocketSphinx anchor.
 *
 * **Experiment knobs (sweep surface):** `-Dpicovoice.windowMs` (1500), `-Dpicovoice.hopMs` (500),
 * `-Dpicovoice.snrDb` (10), `-Dpicovoice.frontend` (`none`|`delta`), `-Dpicovoice.deltaOrder`
 * (`NONE`|`DELTA`|`DELTA_DELTA`), `-Dpicovoice.targetFaPerHour` (0.1). Each **unset prop falls back to the
 * exact ctor default that produced the committed report** (`docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`),
 * so a no-override run is byte-reproducible. Sweeping any of these is an EVAL-003 exploratory, **NOT-banked**
 * family — never headline a mined variant as an FRR/FAR win without a fresh, pre-registered, FAR-matched confirmation.
 *
 * Unset `-Dpicovoice.dir` ⇒ skipped (JUnit `Assume`), so `:core:eval:test` stays green with no corpus.
 */
class PicovoiceBenchmarkTest {

    @Test
    fun `real Picovoice benchmark produces an FA-per-hour + miss-rate report`() {
        val dir = System.getProperty("picovoice.dir")
        assumeTrue("set -Dpicovoice.dir to run the Picovoice benchmark", dir != null && dir.isNotBlank())

        val root = File(dir)
        assertThat(root.isDirectory).isTrue()

        val enroll = System.getProperty("picovoice.enroll")?.toIntOrNull() ?: 10
        val held = System.getProperty("picovoice.held")?.toIntOrNull() ?: 40
        val bg = System.getProperty("picovoice.bgSeconds")?.toDoubleOrNull() ?: 900.0

        val data = PicovoiceCorpus.load(root, enrollPerKeyword = enroll, maxHeldOut = held)
        assumeTrue("prepared/ has no usable keyword + background data (run the fetch script)", data.ok)

        // Experiment knobs — each falls back to the PicovoiceBenchmark ctor default (the committed-report config).
        val windowMs = System.getProperty("picovoice.windowMs")?.toIntOrNull() ?: 1500
        val hopMs = System.getProperty("picovoice.hopMs")?.toIntOrNull() ?: 500
        val snrDb = System.getProperty("picovoice.snrDb")?.toDoubleOrNull() ?: 10.0
        val targetFaPerHour = System.getProperty("picovoice.targetFaPerHour")?.toDoubleOrNull() ?: 0.1

        val dumpDir = System.getProperty("picovoice.dump")?.takeIf { it.isNotBlank() }?.let { File(it) }
        val report = PicovoiceBenchmark(
            frontEnd = pickFrontEnd(),
            windowMs = windowMs,
            hopMs = hopMs,
            backgroundSeconds = bg,
            snrDb = snrDb,
            targetFaPerHour = targetFaPerHour,
        ).run(data, dumpDir)

        assertThat(report).contains("always-on false-alarm rate")
        assertThat(report).contains("Miss-rate vs FA/hour curve")

        val out = File(System.getProperty("picovoice.report").orEmpty().ifBlank { "build/picovoice-report.md" })
        out.parentFile?.mkdirs()
        out.writeText(report)
        println("Picovoice report written to ${out.absolutePath}")
        println(report)
    }

    /**
     * Resolve the front-end from `-Dpicovoice.frontend` (`none`|`delta`) and/or `-Dpicovoice.deltaOrder`
     * (`NONE`|`DELTA`|`DELTA_DELTA`), mirroring the `TorgoEvalTest` idiom. Unset ⇒ the shipped static
     * front-end (`none`, `deltaOrder=NONE`), which is the committed-report baseline. `deltaOrder` wins if
     * both are given (it is the finer knob).
     */
    private fun pickFrontEnd(): FeatureFrontEnd {
        val explicitDelta = System.getProperty("picovoice.deltaOrder")?.let {
            runCatching { DeltaOrder.valueOf(it.uppercase()) }.getOrNull()
        }
        val order = explicitDelta ?: when (System.getProperty("picovoice.frontend")?.lowercase()) {
            "delta" -> DeltaOrder.DELTA
            else -> DeltaOrder.NONE
        }
        val name = if (order == DeltaOrder.NONE) "none" else order.name.lowercase()
        return FeatureFrontEnd(name, MfccConfig(deltaOrder = order))
    }
}
