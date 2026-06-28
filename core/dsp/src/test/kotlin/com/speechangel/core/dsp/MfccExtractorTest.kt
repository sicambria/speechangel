package com.speechangel.core.dsp

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test

class MfccExtractorTest {

    private val extractor = MfccExtractor(MfccConfig(numCoefficients = 13))

    @Test
    fun `extracts 13 coefficients per frame`() {
        val features = extractor.extract(TestSignals.tone(440.0, 500))
        assertThat(features.frameCount).isGreaterThan(0)
        assertThat(features.coefficientCount).isEqualTo(13)
    }

    @Test
    fun `extraction is deterministic`() {
        val audio = TestSignals.tone(440.0, 300)
        val a = extractor.extract(audio)
        val b = extractor.extract(audio)
        assertThat(a.frameCount).isEqualTo(b.frameCount)
        for (t in 0 until a.frameCount) {
            assertThat(a.frames[t]).usingExactEquality().containsExactlyElementsIn(b.frames[t].toList())
        }
    }

    @Test
    fun `audio shorter than one frame yields empty features`() {
        val tiny = AudioSamples(FloatArray(100), 16_000)
        assertThat(extractor.extract(tiny).isEmpty).isTrue()
    }

    @Test
    fun `frame count follows the windowing formula`() {
        // 500 ms @ 16 kHz = 8000 samples; frame 400, shift 160 => floor((8000-400)/160)+1 = 48
        val features = extractor.extract(TestSignals.tone(440.0, 500))
        assertThat(features.frameCount).isEqualTo(48)
    }

    @Test
    fun `delta order widens the vector to 2x and 3x without summing`() {
        val audio = TestSignals.tone(440.0, 500)
        val static = MfccExtractor(MfccConfig(numCoefficients = 13, deltaOrder = DeltaOrder.NONE)).extract(audio)
        val delta = MfccExtractor(MfccConfig(numCoefficients = 13, deltaOrder = DeltaOrder.DELTA)).extract(audio)
        val accel = MfccExtractor(MfccConfig(numCoefficients = 13, deltaOrder = DeltaOrder.DELTA_DELTA)).extract(audio)

        assertThat(static.coefficientCount).isEqualTo(13)
        assertThat(delta.coefficientCount).isEqualTo(26)
        assertThat(accel.coefficientCount).isEqualTo(39)
    }

    @Test
    fun `static block is preserved verbatim in the concatenated delta-delta vector`() {
        // Proves concatenation (static | Δ | ΔΔ), never summation (LIVE BUG #1): the first 13 columns
        // of the Δ+ΔΔ vector must equal the static-only coefficients frame-for-frame.
        val audio = TestSignals.tone(440.0, 500)
        val static = MfccExtractor(MfccConfig(numCoefficients = 13, deltaOrder = DeltaOrder.NONE)).extract(audio)
        val accel = MfccExtractor(MfccConfig(numCoefficients = 13, deltaOrder = DeltaOrder.DELTA_DELTA)).extract(audio)

        assertThat(accel.frameCount).isEqualTo(static.frameCount)
        for (t in 0 until static.frameCount) {
            val staticBlock = accel.frames[t].copyOfRange(0, 13)
            assertThat(staticBlock).usingExactEquality().containsExactlyElementsIn(static.frames[t].toList())
        }
    }

    @Test
    fun `acceleration of a constant-velocity feature ramp is near zero`() {
        // Build a synthetic feature ramp: frame t has every coefficient = t (constant velocity).
        // Δ is constant (=1), so ΔΔ must be ~0 in the interior. Validates the second derivative.
        val width = 4
        val frames = (0 until 20).map { t -> FloatArray(width) { t.toFloat() } }
        val delta = MfccExtractor.derivative(frames)
        val accel = MfccExtractor.derivative(delta)
        for (t in 2 until frames.size - 2) {
            for (i in 0 until width) {
                assertThat(accel[t][i]).isWithin(1e-5f).of(0f)
            }
        }
    }
}
