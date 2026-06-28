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
}
