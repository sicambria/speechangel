package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.RejectionReason
import com.speechangel.core.model.Template
import com.speechangel.core.model.VoiceCondition
import org.junit.Test
import java.util.concurrent.atomic.AtomicInteger

/** End-to-end: enroll two distinct commands from the user's own audio, then recognise fresh takes. */
class RecognizerTest {

    private val ids = AtomicInteger(0)
    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()
    private val enroller = Enroller(mfcc, vad, idGenerator = { "t${ids.incrementAndGet()}" })

    // Generous threshold: this test proves *discrimination* (argmin picks the right command),
    // not absolute calibration (which is a Phase-0 measurement task).
    private val recognizer = Recognizer(mfcc, vad, TemplateMatcher(MatcherConfig(defaultAcceptanceThreshold = 1_000f)))

    private fun enroll(freq: Double, command: String, toneMs: Int): Template {
        val result = enroller.enroll(TestSignals.utterance(freq, toneMs = toneMs), CommandId(command), VoiceCondition.NORMAL)
        return (result as EnrollmentResult.Success).template
    }

    private val templates: List<Template> = listOf(
        enroll(250.0, "yes", 420),
        enroll(250.0, "yes", 380),
        enroll(1500.0, "no", 420),
        enroll(1500.0, "no", 380),
    )

    @Test
    fun `a fresh take of YES is recognised as yes`() {
        val result = recognizer.recognize(TestSignals.utterance(250.0, toneMs = 400, amplitude = 0.25f), templates)
        assertThat(result).isInstanceOf(RecognitionResult.Match::class.java)
        assertThat((result as RecognitionResult.Match).commandId).isEqualTo(CommandId("yes"))
    }

    @Test
    fun `a fresh take of NO is recognised as no`() {
        val result = recognizer.recognize(TestSignals.utterance(1500.0, toneMs = 400, amplitude = 0.25f), templates)
        assertThat((result as RecognitionResult.Match).commandId).isEqualTo(CommandId("no"))
    }

    @Test
    fun `the shipped default config accepts a fresh take of an enrolled command`() {
        // Guards against a threshold that silently rejects all real input (the default ships in the app).
        val defaultRecognizer = Recognizer(mfcc, vad, TemplateMatcher())
        val result = defaultRecognizer.recognize(
            TestSignals.utterance(250.0, toneMs = 400, amplitude = 0.25f),
            templates,
        )
        assertThat(result).isInstanceOf(RecognitionResult.Match::class.java)
        assertThat((result as RecognitionResult.Match).commandId).isEqualTo(CommandId("yes"))
    }

    @Test
    fun `silence is not forced onto a command`() {
        val result = recognizer.recognize(TestSignals.silence(500), templates)
        assertThat(result).isInstanceOf(RecognitionResult.NoMatch::class.java)
        assertThat((result as RecognitionResult.NoMatch).reason).isEqualTo(RejectionReason.SILENCE)
    }
}
