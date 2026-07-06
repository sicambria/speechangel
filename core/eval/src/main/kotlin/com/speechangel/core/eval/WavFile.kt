package com.speechangel.core.eval

import com.speechangel.core.model.AudioSamples
import java.io.File

/**
 * A dependency-free reader for canonical PCM WAV files → [AudioSamples]. Supports 8/16/24/32-bit
 * integer PCM and 32-bit IEEE float, mono or multi-channel (channels are down-mixed to mono by
 * averaging). This exists to feed a real labeled corpus (TORGO) through the [Evaluator]; keeping it
 * inside `core:eval` with no external dependency matches the repo's dependency-free convention.
 *
 * Only the RIFF/WAVE container is parsed — `fmt ` + `data`, skipping any other chunks (`LIST`,
 * `fact`, …). Anything it cannot decode throws [WavFormatException] with a specific message rather
 * than returning silent garbage (a mis-decoded file would poison an FRR number invisibly).
 */
object WavFile {

    /** Read [file] as mono [AudioSamples] normalised to roughly [-1, 1]. */
    fun read(file: File): AudioSamples = read(file.readBytes())

    fun read(bytes: ByteArray): AudioSamples {
        require(bytes.size >= 44) { "WAV too small: ${bytes.size} bytes" }
        if (tag(bytes, 0) != "RIFF") fail("missing RIFF header")
        if (tag(bytes, 8) != "WAVE") fail("missing WAVE header")

        var audioFormat = -1
        var channels = 0
        var sampleRate = 0
        var bitsPerSample = 0
        var dataOffset = -1
        var dataLength = 0

        // Walk sub-chunks from offset 12. Each: 4-byte id + 4-byte little-endian size + payload
        // (payload padded to an even byte boundary).
        var p = 12
        while (p + 8 <= bytes.size) {
            val id = tag(bytes, p)
            val size = le32(bytes, p + 4)
            val payload = p + 8
            when (id) {
                "fmt " -> {
                    if (payload + 16 > bytes.size) fail("truncated fmt chunk")
                    audioFormat = le16(bytes, payload)
                    channels = le16(bytes, payload + 2)
                    sampleRate = le32(bytes, payload + 4)
                    bitsPerSample = le16(bytes, payload + 14)
                }
                "data" -> {
                    dataOffset = payload
                    // Clamp to the actual bytes present (some encoders write a slightly-off size).
                    dataLength = minOf(size, bytes.size - payload)
                }
            }
            if (id == "data") break
            p = payload + size + (size and 1) // pad to even
        }

        if (dataOffset < 0) fail("missing data chunk")
        if (channels <= 0 || sampleRate <= 0) fail("invalid fmt (channels=$channels, rate=$sampleRate)")

        val bytesPerSample = bitsPerSample / 8
        if (bytesPerSample <= 0) fail("unsupported bitsPerSample=$bitsPerSample")
        val frameBytes = bytesPerSample * channels
        val frames = dataLength / frameBytes
        val out = FloatArray(frames)

        for (f in 0 until frames) {
            var acc = 0.0
            val base = dataOffset + f * frameBytes
            for (c in 0 until channels) {
                acc += sampleAt(bytes, base + c * bytesPerSample, audioFormat, bitsPerSample)
            }
            out[f] = (acc / channels).toFloat()
        }
        return AudioSamples(out, sampleRate)
    }

    /** One channel sample at [off], normalised to [-1, 1] (float PCM passes through). */
    private fun sampleAt(b: ByteArray, off: Int, audioFormat: Int, bits: Int): Double {
        // audioFormat: 1 = integer PCM, 3 = IEEE float, 0xFFFE = WAVE_FORMAT_EXTENSIBLE (treat by bits).
        if (audioFormat == 3) {
            return when (bits) {
                32 -> Float.fromBits(le32(b, off)).toDouble()
                64 -> Double.fromBits(le64bits(b, off))
                else -> fail("unsupported float width=$bits")
            }
        }
        return when (bits) {
            8 -> ((b[off].toInt() and 0xFF) - 128) / 128.0 // 8-bit PCM is unsigned
            16 -> le16signed(b, off) / 32768.0
            24 -> le24signed(b, off) / 8_388_608.0
            32 -> le32(b, off) / 2_147_483_648.0
            else -> fail("unsupported PCM width=$bits")
        }
    }

    private fun fail(msg: String): Nothing = throw WavFormatException(msg)

    private fun tag(b: ByteArray, o: Int) = String(b, o, 4, Charsets.US_ASCII)
    private fun le16(b: ByteArray, o: Int) = (b[o].toInt() and 0xFF) or ((b[o + 1].toInt() and 0xFF) shl 8)
    private fun le16signed(b: ByteArray, o: Int) = le16(b, o).toShort().toInt()
    private fun le24signed(b: ByteArray, o: Int): Int {
        val v = (b[o].toInt() and 0xFF) or ((b[o + 1].toInt() and 0xFF) shl 8) or ((b[o + 2].toInt() and 0xFF) shl 16)
        return if (v and 0x800000 != 0) v or -0x1000000 else v // sign-extend 24→32
    }
    private fun le32(b: ByteArray, o: Int) = (b[o].toInt() and 0xFF) or ((b[o + 1].toInt() and 0xFF) shl 8) or
        ((b[o + 2].toInt() and 0xFF) shl 16) or ((b[o + 3].toInt() and 0xFF) shl 24)
    private fun le64bits(b: ByteArray, o: Int): Long {
        var v = 0L
        for (i in 0 until 8) v = v or ((b[o + i].toLong() and 0xFF) shl (8 * i))
        return v
    }
}

class WavFormatException(message: String) : Exception(message)
