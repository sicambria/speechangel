package com.speechangel.data

import com.speechangel.core.model.FeatureSequence
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Compact, deterministic (de)serialisation of a [FeatureSequence] to a blob for Room storage. */
internal object FeatureCodec {

    fun encode(sequence: FeatureSequence): ByteArray {
        val frameCount = sequence.frameCount
        val coeffCount = sequence.coefficientCount
        val buffer = ByteBuffer
            .allocate(Int.SIZE_BYTES * 2 + frameCount * coeffCount * Float.SIZE_BYTES)
            .order(ByteOrder.LITTLE_ENDIAN)
        buffer.putInt(frameCount)
        buffer.putInt(coeffCount)
        for (frame in sequence.frames) for (value in frame) buffer.putFloat(value)
        return buffer.array()
    }

    fun decode(bytes: ByteArray): FeatureSequence {
        if (bytes.size < Int.SIZE_BYTES * 2) return FeatureSequence(emptyList())
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val frameCount = buffer.int
        val coeffCount = buffer.int
        val frames = ArrayList<FloatArray>(frameCount)
        repeat(frameCount) {
            val frame = FloatArray(coeffCount)
            for (i in 0 until coeffCount) frame[i] = buffer.float
            frames.add(frame)
        }
        return FeatureSequence(frames)
    }
}
