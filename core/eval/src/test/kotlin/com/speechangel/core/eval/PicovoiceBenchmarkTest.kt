package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
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

        val dumpDir = System.getProperty("picovoice.dump")?.takeIf { it.isNotBlank() }?.let { File(it) }
        val report = PicovoiceBenchmark(backgroundSeconds = bg).run(data, dumpDir)

        assertThat(report).contains("always-on false-alarm rate")
        assertThat(report).contains("Miss-rate vs FA/hour curve")

        val out = File(System.getProperty("picovoice.report").orEmpty().ifBlank { "build/picovoice-report.md" })
        out.parentFile?.mkdirs()
        out.writeText(report)
        println("Picovoice report written to ${out.absolutePath}")
        println(report)
    }
}
