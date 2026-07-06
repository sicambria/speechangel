package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import java.io.ByteArrayOutputStream

class WavFileTest {

    /** Build a canonical 16-bit mono PCM WAV around [samples] (each in [-1,1]). */
    private fun wav16(sampleRate: Int, samples: FloatArray): ByteArray {
        val dataLen = samples.size * 2
        val out = ByteArrayOutputStream()
        fun str(s: String) = out.write(s.toByteArray(Charsets.US_ASCII))
        fun le16(v: Int) {
            out.write(v and 0xFF)
            out.write((v shr 8) and 0xFF)
        }
        fun le32(v: Int) {
            out.write(v and 0xFF)
            out.write((v shr 8) and 0xFF)
            out.write((v shr 16) and 0xFF)
            out.write(
                (v shr 24) and 0xFF,
            )
        }
        str("RIFF")
        le32(36 + dataLen)
        str("WAVE")
        str("fmt ")
        le32(16)
        le16(1)
        le16(1)
        le32(sampleRate)
        le32(sampleRate * 2)
        le16(2)
        le16(16)
        str("data")
        le32(dataLen)
        for (s in samples) {
            val q = (s * 32767).toInt().coerceIn(-32768, 32767)
            le16(q and 0xFFFF)
        }
        return out.toByteArray()
    }

    @Test
    fun `round-trips a 16-bit mono PCM WAV`() {
        val samples = floatArrayOf(0f, 0.5f, -0.5f, 1f, -1f, 0.25f)
        val decoded = WavFile.read(wav16(16_000, samples))

        assertThat(decoded.sampleRateHz).isEqualTo(16_000)
        assertThat(decoded.samples.size).isEqualTo(samples.size)
        // 16-bit quantisation error is < 1/32767.
        for (i in samples.indices) {
            assertThat(decoded.samples[i]).isWithin(1e-3f).of(samples[i])
        }
    }

    @Test
    fun `skips an unknown chunk before data`() {
        // Splice a LIST chunk between fmt and data; the reader must skip it and still find data.
        val base = wav16(16_000, floatArrayOf(0.1f, -0.2f, 0.3f))
        val dataIdx = indexOf(base, "data")
        val list = ByteArrayOutputStream().apply {
            write("LIST".toByteArray(Charsets.US_ASCII))
            // size = 4, one even payload
            write(byteArrayOf(4, 0, 0, 0))
            write("INFO".toByteArray(Charsets.US_ASCII))
        }.toByteArray()
        val spliced = base.copyOfRange(0, dataIdx) + list + base.copyOfRange(dataIdx, base.size)

        val decoded = WavFile.read(spliced)
        assertThat(decoded.samples.size).isEqualTo(3)
        assertThat(decoded.samples[0]).isWithin(1e-3f).of(0.1f)
    }

    @Test
    fun `rejects a non-RIFF blob`() {
        val bad = ByteArray(64) { 0 }
        try {
            WavFile.read(bad)
            throw AssertionError("expected WavFormatException")
        } catch (e: WavFormatException) {
            assertThat(e).hasMessageThat().contains("RIFF")
        }
    }

    private fun indexOf(b: ByteArray, tag: String): Int {
        val t = tag.toByteArray(Charsets.US_ASCII)
        outer@ for (i in 0..b.size - t.size) {
            for (j in t.indices) if (b[i + j] != t[j]) continue@outer
            return i
        }
        error("tag $tag not found")
    }
}
