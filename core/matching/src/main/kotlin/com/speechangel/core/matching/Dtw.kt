package com.speechangel.core.matching

import com.speechangel.core.model.FeatureSequence
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Dynamic Time Warping over feature sequences. Language-independent: it measures how well two
 * acoustic trajectories align, with no phoneme or word model. Distance is length-normalised so
 * utterances of different durations are comparable.
 */
object Dtw {

    private val INF = Double.POSITIVE_INFINITY

    /** Squared-then-rooted Euclidean distance between two equal-width frames. */
    fun euclidean(a: FloatArray, b: FloatArray): Double {
        var sum = 0.0
        for (i in a.indices) {
            val d = a[i] - b[i]
            sum += d.toDouble() * d
        }
        return sqrt(sum)
    }

    /**
     * Length-normalised DTW distance between [a] and [b]. Lower means more similar.
     *
     * @param bandRatio Sakoe–Chiba band as a fraction of the longer sequence (0 = unconstrained).
     *   A band both speeds matching and prevents pathological warps.
     */
    fun distance(
        a: FeatureSequence,
        b: FeatureSequence,
        bandRatio: Double = 0.1,
        local: (FloatArray, FloatArray) -> Double = ::euclidean,
    ): Double {
        val n = a.frameCount
        val m = b.frameCount
        if (n == 0 || m == 0) return INF
        require(a.coefficientCount == b.coefficientCount) {
            "feature width mismatch: ${a.coefficientCount} vs ${b.coefficientCount}"
        }

        val band = if (bandRatio <= 0.0) Int.MAX_VALUE else max(1, (bandRatio * max(n, m)).toInt())
        val ratio = m.toDouble() / n

        var prev = DoubleArray(m + 1) { INF }
        var curr = DoubleArray(m + 1) { INF }
        prev[0] = 0.0

        for (i in 1..n) {
            java.util.Arrays.fill(curr, INF)
            val center = ((i - 1) * ratio).toInt()
            val jStart = max(1, center - band + 1)
            val jEnd = (center + band).coerceAtMost(m)
            for (j in jStart..jEnd) {
                if (abs((i - 1) - ((j - 1) / ratio).toInt()) > band) continue
                val cost = local(a.frames[i - 1], b.frames[j - 1])
                val best = minOf(prev[j], curr[j - 1], prev[j - 1])
                if (best != INF) curr[j] = cost + best
            }
            val tmp = prev
            prev = curr
            curr = tmp
        }

        val accumulated = prev[m]
        return if (accumulated == INF) INF else accumulated / (n + m)
    }
}
