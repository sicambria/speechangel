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

    /** Result of a DTW computation, carrying both the distance and the alignment path length. */
    data class Result(val distance: Double, val pathLength: Int)

    /** Squared-then-rooted Euclidean distance between two equal-width frames. */
    fun euclidean(a: FloatArray, b: FloatArray): Double {
        var sum = 0.0
        for (i in a.indices) {
            val d = a[i] - b[i]
            sum += d.toDouble() * d
        }
        return sqrt(sum)
    }

    /** Cosine distance (1 - cosine similarity) between two equal-width frames, in [0, 2]. */
    fun cosine(a: FloatArray, b: FloatArray): Double {
        var dot = 0.0
        var normA = 0.0
        var normB = 0.0
        for (i in a.indices) {
            dot += a[i].toDouble() * b[i].toDouble()
            normA += a[i].toDouble() * a[i].toDouble()
            normB += b[i].toDouble() * b[i].toDouble()
        }
        val denom = sqrt(normA) * sqrt(normB)
        return if (denom < 1e-12) 1.0 else (1.0 - dot / denom).coerceIn(0.0, 2.0)
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
    ): Double = withPath(a, b, bandRatio, local).distance

    /**
     * DTW that returns both the normalised distance AND the raw path length (number of steps in the
     * optimal alignment). The path length enables dual-filter cascade rejection (see [TemplateMatcher]).
     */
    fun withPath(
        a: FeatureSequence,
        b: FeatureSequence,
        bandRatio: Double = 0.1,
        local: (FloatArray, FloatArray) -> Double = ::euclidean,
    ): Result {
        val n = a.frameCount
        val m = b.frameCount
        if (n == 0 || m == 0) return Result(INF, 0)
        require(a.coefficientCount == b.coefficientCount) {
            "feature width mismatch: ${a.coefficientCount} vs ${b.coefficientCount}"
        }

        val band = if (bandRatio <= 0.0) Int.MAX_VALUE else max(1, (bandRatio * max(n, m)).toInt())
        val ratio = m.toDouble() / n

        var prev = DoubleArray(m + 1) { INF }
        var curr = DoubleArray(m + 1) { INF }
        var prevLen = IntArray(m + 1) { 0 }
        var currLen = IntArray(m + 1) { 0 }
        prev[0] = 0.0

        for (i in 1..n) {
            java.util.Arrays.fill(curr, INF)
            java.util.Arrays.fill(currLen, 0)
            val center = ((i - 1) * ratio).toInt()
            val jStart = max(1, center - band + 1)
            val jEnd = (center + band).coerceAtMost(m)
            for (j in jStart..jEnd) {
                if (abs((i - 1) - ((j - 1) / ratio).toInt()) > band) continue
                val cost = local(a.frames[i - 1], b.frames[j - 1])
                val dDiag = prev[j - 1]
                val dUp = prev[j]
                val dLeft = curr[j - 1]
                // Prefer diagonal → yields shorter paths.
                val bestDist: Double
                val bestLen: Int
                when {
                    dDiag <= dUp && dDiag <= dLeft -> {
                        bestDist = dDiag
                        bestLen = prevLen[j - 1]
                    }
                    dUp <= dLeft -> {
                        bestDist = dUp
                        bestLen = prevLen[j]
                    }
                    else -> {
                        bestDist = dLeft
                        bestLen = currLen[j - 1]
                    }
                }
                if (bestDist != INF) {
                    curr[j] = cost + bestDist
                    currLen[j] = bestLen + 1
                }
            }
            val tmp = prev
            prev = curr
            curr = tmp
            val tmpLen = prevLen
            prevLen = currLen
            currLen = tmpLen
        }

        val accumulated = prev[m]
        val pathLen = prevLen[m]
        return if (accumulated == INF) {
            Result(INF, 0)
        } else {
            Result(accumulated / (n + m), pathLen)
        }
    }
}
