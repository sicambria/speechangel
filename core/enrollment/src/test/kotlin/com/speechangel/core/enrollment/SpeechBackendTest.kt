package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import org.junit.Test

class SpeechBackendTest {

    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()
    private val recognizer = Recognizer(mfcc, vad, TemplateMatcher())

    private fun enroll(commandId: CommandId, freq: Double): Template {
        var n = 0L
        val enroller = Enroller(mfcc, vad, idGenerator = { "t${n++}" }, clock = { n })
        return (enroller.enroll(TestSignals.utterance(freq), commandId) as EnrollmentResult.Success).template
    }

    @Test
    fun `template backend maps a match into a neutral BackendResult`() {
        val go = CommandId("go")
        val backend = TemplateSpeechBackend(recognizer, listOf(enroll(go, 440.0)))
        val result = backend.recognize(TestSignals.utterance(440.0))
        assertThat(result.commandId).isEqualTo(go)
        assertThat(result.reason).isNull()
    }

    @Test
    fun `silence maps to the neutral NO_SPEECH reason, never a template-centric one`() {
        val backend = TemplateSpeechBackend(recognizer, listOf(enroll(CommandId("go"), 440.0)))
        val result = backend.recognize(TestSignals.silence(400))
        assertThat(result.commandId).isNull()
        assertThat(result.reason).isEqualTo(BackendRejection.NO_SPEECH)
    }

    @Test
    fun `detailed result preserves the DTW nearest-command and distance for the template engine`() {
        val go = CommandId("go")
        val backend = TemplateSpeechBackend(recognizer, listOf(enroll(go, 440.0)))
        val detailed = backend.recognizeDetailed(TestSignals.utterance(440.0))
        assertThat(detailed.result.commandId).isEqualTo(go)
        assertThat(detailed.bestDistance).isFinite()
    }

    @Test
    fun `noop path-a backend is always unavailable`() {
        val backend = NoopPathABackend()
        assertThat(backend.capabilities.languageDependent).isTrue()
        assertThat(backend.recognize(TestSignals.utterance(440.0)).reason)
            .isEqualTo(BackendRejection.BACKEND_UNAVAILABLE)
    }
}
