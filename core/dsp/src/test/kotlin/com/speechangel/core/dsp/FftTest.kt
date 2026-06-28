package com.speechangel.core.dsp

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import kotlin.math.PI
import kotlin.math.cos

class FftTest {

    @Test
    fun `power of two helpers`() {
        assertThat(Fft.isPowerOfTwo(1)).isTrue()
        assertThat(Fft.isPowerOfTwo(512)).isTrue()
        assertThat(Fft.isPowerOfTwo(400)).isFalse()
        assertThat(Fft.nextPowerOfTwo(400)).isEqualTo(512)
        assertThat(Fft.nextPowerOfTwo(512)).isEqualTo(512)
    }

    @Test
    fun `power spectrum peaks at the frequency bin of a pure cosine`() {
        val n = 64
        val k = 5 // cycles across the window -> energy should land in bin 5
        val frame = FloatArray(n) { i -> cos(2.0 * PI * k * i / n).toFloat() }
        val spectrum = Fft.powerSpectrum(frame, n)

        var maxBin = 0
        for (b in spectrum.indices) if (spectrum[b] > spectrum[maxBin]) maxBin = b
        assertThat(maxBin).isEqualTo(k)
    }

    @Test
    fun `power spectrum size is fftSize over two plus one`() {
        val spectrum = Fft.powerSpectrum(FloatArray(64) { 0f }, 64)
        assertThat(spectrum.size).isEqualTo(33)
    }
}
