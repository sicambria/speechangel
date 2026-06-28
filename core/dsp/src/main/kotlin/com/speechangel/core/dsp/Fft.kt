package com.speechangel.core.dsp

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** Iterative radix-2 Cooley–Tukey FFT, used to obtain the power spectrum of a frame. */
internal object Fft {

    /** Returns true when [n] is a power of two (FFT precondition). */
    fun isPowerOfTwo(n: Int): Boolean = n > 0 && (n and (n - 1)) == 0

    /** Smallest power of two >= [n]. */
    fun nextPowerOfTwo(n: Int): Int {
        var p = 1
        while (p < n) p = p shl 1
        return p
    }

    /**
     * Power spectrum of a real [frame], zero-padded to [fftSize].
     * Returns `fftSize/2 + 1` non-negative bins (DC .. Nyquist), normalised by [fftSize].
     */
    fun powerSpectrum(frame: FloatArray, fftSize: Int): FloatArray {
        require(isPowerOfTwo(fftSize)) { "fftSize must be a power of two, was $fftSize" }
        require(frame.size <= fftSize) { "frame (${frame.size}) longer than fftSize ($fftSize)" }
        val re = DoubleArray(fftSize)
        val im = DoubleArray(fftSize)
        for (i in frame.indices) re[i] = frame[i].toDouble()
        transform(re, im)
        val half = fftSize / 2 + 1
        val out = FloatArray(half)
        for (k in 0 until half) {
            out[k] = ((re[k] * re[k] + im[k] * im[k]) / fftSize).toFloat()
        }
        return out
    }

    /** In-place complex FFT. [re]/[im] length must be a power of two. */
    fun transform(re: DoubleArray, im: DoubleArray) {
        val n = re.size
        require(isPowerOfTwo(n)) { "length must be a power of two, was $n" }
        // Bit-reversal permutation.
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) {
                j = j xor bit
                bit = bit shr 1
            }
            j = j or bit
            if (i < j) {
                val tr = re[i]; re[i] = re[j]; re[j] = tr
                val ti = im[i]; im[i] = im[j]; im[j] = ti
            }
        }
        // Butterfly stages.
        var len = 2
        while (len <= n) {
            val ang = -2.0 * PI / len
            val wLenRe = cos(ang)
            val wLenIm = sin(ang)
            var i = 0
            while (i < n) {
                var wRe = 1.0
                var wIm = 0.0
                val half = len / 2
                for (k in 0 until half) {
                    val a = i + k
                    val b = i + k + half
                    val vRe = re[b] * wRe - im[b] * wIm
                    val vIm = re[b] * wIm + im[b] * wRe
                    re[b] = re[a] - vRe
                    im[b] = im[a] - vIm
                    re[a] += vRe
                    im[a] += vIm
                    val nextWRe = wRe * wLenRe - wIm * wLenIm
                    wIm = wRe * wLenIm + wIm * wLenRe
                    wRe = nextWRe
                }
                i += len
            }
            len = len shl 1
        }
    }
}
