package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import org.junit.Test

class QbeTest {

    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()

    /** Deterministic stand-in encoder: the per-coefficient mean over frames (dims == MFCC width). */
    private class MeanEncoder(override val dimensions: Int) : QbeEncoder {
        override val available = true
        override fun encode(features: FeatureSequence): FloatArray {
            val out = FloatArray(dimensions)
            if (features.isEmpty) return out
            for (frame in features.frames) {
                for (i in 0 until minOf(dimensions, frame.size)) out[i] += frame[i]
            }
            for (i in out.indices) out[i] /= features.frameCount
            return out
        }
    }

    private val encoder = MeanEncoder(13)
    private val go = CommandId("go")
    private val stop = CommandId("stop")

    private fun examples() = mapOf(
        go to List(3) { TestSignals.utterance(440.0) },
        stop to List(3) { TestSignals.utterance(880.0) },
    )

    @Test
    fun `enroll builds one prototype per command and classifies the right one`() {
        val prototypes = QbeSpeechBackend.enroll(encoder, mfcc, vad, examples())
        assertThat(prototypes.keys).containsExactly(go, stop)

        val backend = QbeSpeechBackend(encoder, mfcc, vad, prototypes)
        assertThat(backend.available).isTrue()
        assertThat(backend.recognize(TestSignals.utterance(440.0)).commandId).isEqualTo(go)
        assertThat(backend.recognize(TestSignals.utterance(880.0)).commandId).isEqualTo(stop)
    }

    @Test
    fun `silence rejects with the neutral NO_SPEECH reason`() {
        val backend = QbeSpeechBackend(encoder, mfcc, vad, QbeSpeechBackend.enroll(encoder, mfcc, vad, examples()))
        val result = backend.recognize(TestSignals.silence(400))
        assertThat(result.commandId).isNull()
        assertThat(result.reason).isEqualTo(BackendRejection.NO_SPEECH)
    }

    @Test
    fun `an unreachable acceptance bar rejects with LOW_CONFIDENCE, never a wrong match`() {
        val prototypes = QbeSpeechBackend.enroll(encoder, mfcc, vad, examples())
        val strict = QbeSpeechBackend(encoder, mfcc, vad, prototypes, acceptSimilarity = 1.1f)
        val result = strict.recognize(TestSignals.utterance(440.0))
        assertThat(result.commandId).isNull()
        assertThat(result.reason).isEqualTo(BackendRejection.LOW_CONFIDENCE)
    }

    @Test
    fun `the Noop encoder leaves the backend unavailable`() {
        val noop = NoopQbeEncoder()
        assertThat(QbeSpeechBackend.enroll(noop, mfcc, vad, examples())).isEmpty()
        val backend = QbeSpeechBackend(noop, mfcc, vad, emptyMap())
        assertThat(backend.available).isFalse()
        val result = backend.recognize(TestSignals.utterance(440.0))
        assertThat(result.reason).isEqualTo(BackendRejection.BACKEND_UNAVAILABLE)
    }

    @Test
    fun `selector defaults to the template engine and uses QbE only when chosen and available`() {
        val recognizer = Recognizer(mfcc, vad, TemplateMatcher())
        val template: SpeechBackend = TemplateSpeechBackend(recognizer, emptyList())
        val availableQbe = QbeSpeechBackend(encoder, mfcc, vad, QbeSpeechBackend.enroll(encoder, mfcc, vad, examples()))
        val dormantQbe = QbeSpeechBackend(NoopQbeEncoder(), mfcc, vad, emptyMap())

        assertThat(SpeechBackendSelector.select(BackendChoice.TEMPLATE, template, availableQbe)).isSameInstanceAs(template)
        assertThat(SpeechBackendSelector.select(BackendChoice.QBE, template, availableQbe)).isSameInstanceAs(availableQbe)
        assertThat(SpeechBackendSelector.select(BackendChoice.QBE, template, dormantQbe)).isSameInstanceAs(template)
        assertThat(SpeechBackendSelector.select(BackendChoice.QBE, template, null)).isSameInstanceAs(template)
    }
}
