package com.speechangel.core.dsp

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test

class NoiseReductionTest {

    private fun config(nr: NoiseReduction) = MfccConfig(numCoefficients = 13, noiseReduction = nr)

    /** Non-stationary signal (440 Hz then 880 Hz) so a per-band noise floor differs from per-frame. */
    private fun nonStationary(): AudioSamples {
        val first = TestSignals.tone(440.0, 250)
        val second = TestSignals.tone(880.0, 250)
        return AudioSamples(first.samples + second.samples, first.sampleRateHz)
    }

    @Test
    fun `NONE is byte-identical to the default pipeline`() {
        val audio = nonStationary()
        val default = MfccExtractor(MfccConfig(numCoefficients = 13)).extract(audio)
        val none = MfccExtractor(config(NoiseReduction.NONE)).extract(audio)
        assertThat(none.frameCount).isEqualTo(default.frameCount)
        for (t in 0 until default.frameCount) {
            assertThat(none.frames[t]).usingExactEquality().containsExactlyElementsIn(default.frames[t].toList())
        }
    }

    @Test
    fun `spectral subtraction keeps the frame shape but changes features, surviving CMN`() {
        val audio = nonStationary()
        val base = MfccExtractor(config(NoiseReduction.NONE)).extract(audio)
        val denoised = MfccExtractor(config(NoiseReduction.SPECTRAL_SUBTRACTION)).extract(audio)

        assertThat(denoised.frameCount).isEqualTo(base.frameCount)
        assertThat(denoised.coefficientCount).isEqualTo(base.coefficientCount)
        // CMN is on by default; a constant offset would be cancelled, so any difference proves the
        // subtraction is genuinely non-linear (rectified) and active.
        val differs = (0 until base.frameCount).any { t -> base.frames[t].toList() != denoised.frames[t].toList() }
        assertThat(differs).isTrue()
    }

    @Test
    fun `spectral subtraction is deterministic`() {
        val audio = nonStationary()
        val extractor = MfccExtractor(config(NoiseReduction.SPECTRAL_SUBTRACTION))
        val a = extractor.extract(audio)
        val b = extractor.extract(audio)
        assertThat(a.frameCount).isEqualTo(b.frameCount)
        for (t in 0 until a.frameCount) {
            assertThat(a.frames[t]).usingExactEquality().containsExactlyElementsIn(b.frames[t].toList())
        }
    }

    @Test
    fun `audio shorter than one frame yields empty features under noise reduction`() {
        val tiny = AudioSamples(FloatArray(100), 16_000)
        assertThat(MfccExtractor(config(NoiseReduction.SPECTRAL_SUBTRACTION)).extract(tiny).isEmpty).isTrue()
    }
}
