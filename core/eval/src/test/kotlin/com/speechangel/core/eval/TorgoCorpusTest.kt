package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.file.Files

class TorgoCorpusTest {

    @Test
    fun `normalize keeps short words, strips clarifiers, drops instructions and sentences`() {
        assertThat(TorgoCorpus.normalize("stick")).isEqualTo("stick")
        assertThat(TorgoCorpus.normalize("tear [as in tear up that paper]")).isEqualTo("tear")
        assertThat(TorgoCorpus.normalize("[say Ah-P-Eee repeatedly]")).isNull()
        assertThat(TorgoCorpus.normalize("[relax your mouth in its normal position]")).isNull()
        assertThat(TorgoCorpus.normalize("Except in the winter when the ooze or snow or ice prevents,")).isNull()
        assertThat(TorgoCorpus.normalize("xxx")).isNull()
        assertThat(TorgoCorpus.normalize("input/images/kitchen.jpg")).isNull()
        assertThat(TorgoCorpus.normalize("")).isNull()
    }

    @Test
    fun `scan groups by word into commands vs single-instance OOV negatives`() {
        val root = fixture(
            "F01",
            "Session1",
            listOf("up", "up", "down", "down", "solo", "[say blah]"),
        )
        val speakers = TorgoCorpus.scan(root, minReps = 2)
        assertThat(speakers).hasSize(1)
        val f01 = speakers.single()
        assertThat(f01.id).isEqualTo("F01")
        assertThat(f01.commands.keys).containsExactly("up", "down")
        assertThat(f01.commands["up"]).hasSize(2)
        // "solo" appears once -> OOV negative; the bracket instruction is dropped entirely.
        assertThat(f01.negatives.map { it.word }).containsExactly("solo")
    }

    @Test
    fun `k-fold tests every positive once and never enrolls the tested utterance`() {
        val root = fixture("F01", "Session1", listOf("up", "up", "up", "down", "down"))
        val f01 = TorgoCorpus.scan(root, minReps = 2).single()
        val folds = TorgoCorpus.folds(f01, k = 2)

        val allTested = folds.flatMap { it.positives }
        assertThat(allTested).hasSize(5) // 3 up + 2 down, each tested exactly once
        for (fold in folds) {
            for (p in fold.positives) {
                assertThat(fold.enroll).doesNotContain(p)
                // the tested word still has >=1 enrollment template in this fold
                assertThat(fold.enroll.any { it.word == p.word }).isTrue()
            }
        }
    }

    // --- fixture helpers -------------------------------------------------------------------------

    /** Create a TORGO-shaped dir: <root>/<spk>/<session>/{prompts,wav_headMic} with one wav per prompt. */
    private fun fixture(spk: String, session: String, prompts: List<String>): File {
        val root = Files.createTempDirectory("torgo-fixture").toFile()
        val pdir = File(root, "$spk/$session/prompts").apply { mkdirs() }
        val wdir = File(root, "$spk/$session/wav_headMic").apply { mkdirs() }
        prompts.forEachIndexed { i, text ->
            val id = "%04d".format(i + 1)
            File(pdir, "$id.txt").writeText(text)
            File(wdir, "$id.wav").writeBytes(wav16(floatArrayOf(0.1f, -0.1f, 0.2f, -0.2f)))
        }
        return root
    }

    private fun wav16(samples: FloatArray): ByteArray {
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
        le32(16_000)
        le32(32_000)
        le16(2)
        le16(16)
        str("data")
        le32(dataLen)
        for (s in samples) le16(((s * 32767).toInt().coerceIn(-32768, 32767)) and 0xFFFF)
        return out.toByteArray()
    }
}
