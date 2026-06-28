package com.speechangel.core.matching

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.FeatureSequence
import org.junit.Test

class DtwTest {

    private fun seq(vararg frames: FloatArray) = FeatureSequence(frames.toList())

    @Test
    fun `identical sequences have zero distance`() {
        val a = seq(floatArrayOf(1f, 2f), floatArrayOf(3f, 4f), floatArrayOf(5f, 6f))
        assertThat(Dtw.distance(a, a)).isWithin(1e-6).of(0.0)
    }

    @Test
    fun `time-warped version of the same trajectory is closer than a different one`() {
        val base = seq(floatArrayOf(0f), floatArrayOf(1f), floatArrayOf(2f), floatArrayOf(3f))
        // Same shape, stretched in time (duplicated frames) -> DTW should align well.
        val warped = seq(
            floatArrayOf(0f),
            floatArrayOf(0f),
            floatArrayOf(1f),
            floatArrayOf(2f),
            floatArrayOf(3f),
            floatArrayOf(3f),
        )
        val different = seq(floatArrayOf(3f), floatArrayOf(2f), floatArrayOf(1f), floatArrayOf(0f))

        val dWarped = Dtw.distance(base, warped, bandRatio = 0.5)
        val dDifferent = Dtw.distance(base, different, bandRatio = 0.5)
        assertThat(dWarped).isLessThan(dDifferent)
    }

    @Test
    fun `empty sequence yields infinite distance`() {
        val a = seq(floatArrayOf(1f))
        val empty = FeatureSequence(emptyList())
        assertThat(Dtw.distance(a, empty)).isPositiveInfinity()
    }

    @Test
    fun `distance is symmetric`() {
        val a = seq(floatArrayOf(1f, 1f), floatArrayOf(2f, 0f), floatArrayOf(0f, 2f))
        val b = seq(floatArrayOf(1f, 1f), floatArrayOf(2f, 1f), floatArrayOf(1f, 2f), floatArrayOf(0f, 2f))
        val ab = Dtw.distance(a, b, bandRatio = 1.0)
        val ba = Dtw.distance(b, a, bandRatio = 1.0)
        assertThat(ab).isWithin(1e-6).of(ba)
    }
}
