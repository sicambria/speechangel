package com.speechangel.core.dsp

import kotlin.math.ln
import kotlin.math.log10

/**
 * Triangular mel-scale filter bank applied to a power spectrum.
 * Mel mapping: `mel(f) = 2595 * log10(1 + f/700)`.
 */
internal class MelFilterBank(
    private val numFilters: Int,
    private val fftSize: Int,
    private val sampleRateHz: Int,
    private val lowFreqHz: Double,
    private val highFreqHz: Double,
) {
    private val spectrumBins = fftSize / 2 + 1

    // For each filter, the [startBin, centerBin, endBin] triangle anchors.
    private val binPoints: IntArray = buildBinPoints()

    private fun melOf(freq: Double): Double = 2595.0 * log10(1.0 + freq / 700.0)
    private fun invMel(mel: Double): Double = 700.0 * (Math.pow(10.0, mel / 2595.0) - 1.0)

    private fun buildBinPoints(): IntArray {
        val lowMel = melOf(lowFreqHz)
        val highMel = melOf(highFreqHz)
        val points = IntArray(numFilters + 2)
        for (i in points.indices) {
            val mel = lowMel + (highMel - lowMel) * i / (numFilters + 1)
            val freq = invMel(mel)
            val bin = Math.floor((fftSize + 1) * freq / sampleRateHz).toInt()
            points[i] = bin.coerceIn(0, spectrumBins - 1)
        }
        return points
    }

    /** Returns [numFilters] log-compressed mel energies for the given [powerSpectrum]. */
    fun logEnergies(powerSpectrum: FloatArray): FloatArray {
        require(powerSpectrum.size == spectrumBins) {
            "power spectrum size ${powerSpectrum.size} != expected $spectrumBins"
        }
        val out = FloatArray(numFilters)
        for (m in 1..numFilters) {
            val left = binPoints[m - 1]
            val center = binPoints[m]
            val right = binPoints[m + 1]
            var energy = 0.0
            for (k in left until center) {
                if (center > left) energy += powerSpectrum[k] * (k - left).toDouble() / (center - left)
            }
            for (k in center until right) {
                if (right > center) energy += powerSpectrum[k] * (right - k).toDouble() / (right - center)
            }
            // Floor before log to avoid -inf on silent bands.
            out[m - 1] = ln(energy.coerceAtLeast(LOG_FLOOR)).toFloat()
        }
        return out
    }

    private companion object {
        const val LOG_FLOOR = 1e-10
    }
}
