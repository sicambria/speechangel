package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.AudioSamples
import org.junit.Test

class DictationTest {

    /** A fake backend that "transcribes" a clip to a fixed string — proves the seam round-trips. */
    private class EchoDictationBackend(private val text: String) : DictationBackend {
        override val capabilities = DictationCapabilities(languageDependent = true, streaming = false)
        override fun transcribe(audio: AudioSamples): DictationResult = if (audio.isEmpty) {
            DictationResult("", 0f, DictationRejection.NO_SPEECH)
        } else {
            DictationResult(text, 0.9f, null)
        }
    }

    @Test
    fun `a dictation backend round-trips audio into a transcript`() {
        val backend = EchoDictationBackend("hello world")
        val result = backend.transcribe(TestSignals.utterance(440.0))
        assertThat(result.transcript).isEqualTo("hello world")
        assertThat(result.reason).isNull()
    }

    @Test
    fun `empty audio yields NO_SPEECH, not a fabricated transcript`() {
        val result = EchoDictationBackend("hello").transcribe(AudioSamples(FloatArray(0), 16_000))
        assertThat(result.transcript).isEmpty()
        assertThat(result.reason).isEqualTo(DictationRejection.NO_SPEECH)
    }

    @Test
    fun `the Noop backend reports unavailable and never returns text`() {
        val result = NoopDictationBackend().transcribe(TestSignals.utterance(440.0))
        assertThat(result.transcript).isEmpty()
        assertThat(result.reason).isEqualTo(DictationRejection.BACKEND_UNAVAILABLE)
    }
}
