package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.Template
import org.junit.Test

/**
 * Unit coverage for the wake→command streaming state machine that was previously inlined (untested)
 * in `ListeningService`. Uses the real DSP/matching stack with a generous matcher threshold so the
 * assertions are about *control flow* (gating, transitions, buffer reset), not threshold calibration.
 */
class WakeGatedRecognizerTest {

    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()

    // Generous threshold: we exercise the transition logic, not FRR/FAR tuning.
    private val matcher = TemplateMatcher(MatcherConfig(defaultAcceptanceThreshold = 1_000f))
    private val recognizer = Recognizer(mfcc, vad, matcher)

    private var ids = 0
    private fun enroll(freq: Double, command: CommandId): Template {
        val enroller = Enroller(mfcc, vad, idGenerator = { "t${ids++}" })
        return (enroller.enroll(TestSignals.utterance(freq), command) as EnrollmentResult.Success).template
    }

    /** A command-length utterance: long enough to fill at least one 1.5 s window with speech. */
    private fun longUtterance(freq: Double) = TestSignals.utterance(freq, toneMs = 1_400, padMs = 200)

    /** Chop a buffer into fixed [frameMs] frames (the last may be short), as the recorder stream does. */
    private fun frames(audio: AudioSamples, frameMs: Int = 150): List<AudioSamples> {
        val fs = audio.sampleRateHz * frameMs / 1000
        return audio.samples.toList().chunked(fs).map { AudioSamples(it.toFloatArray(), audio.sampleRateHz) }
    }

    private val yes = CommandId("yes")

    @Test
    fun `with no wake templates a command window is recognized directly`() {
        val sm = WakeGatedRecognizer(recognizer, WakeWordGate(mfcc, matcher, BIG), vad, RATE)
        val templates = listOf(enroll(250.0, yes))

        val outcomes = frames(longUtterance(250.0)).map { sm.onFrame(it, templates) }

        val matches = outcomes.filterIsInstance<WakeGatedRecognizer.Outcome.Recognized>().map { it.result }
        assertThat(matches.any { it is RecognitionResult.Match && it.commandId == yes }).isTrue()
        assertThat(outcomes.none { it is WakeGatedRecognizer.Outcome.Woke }).isTrue()
    }

    @Test
    fun `a wake gate that never fires suppresses Stage-2 entirely`() {
        // wakeThreshold 0 -> every distance exceeds it -> NoWake forever -> the command never runs.
        val neverWake = WakeWordGate(mfcc, matcher, wakeThreshold = 0f)
        val sm = WakeGatedRecognizer(recognizer, neverWake, vad, RATE)
        val templates = listOf(enroll(440.0, ReservedCommands.WAKE), enroll(250.0, yes))

        val outcomes = frames(longUtterance(250.0)).map { sm.onFrame(it, templates) }

        assertThat(outcomes.none { it is WakeGatedRecognizer.Outcome.Woke }).isTrue()
        assertThat(outcomes.none { it is WakeGatedRecognizer.Outcome.Recognized }).isTrue()
    }

    @Test
    fun `once woken the next command window is recognized`() {
        val sm = WakeGatedRecognizer(recognizer, WakeWordGate(mfcc, matcher, BIG), vad, RATE)
        val templates = listOf(enroll(440.0, ReservedCommands.WAKE), enroll(250.0, yes))

        // Feed wake frames only up to (and including) the Woke, so wake audio doesn't pollute cmdBuf.
        var woke = false
        for (f in frames(TestSignals.utterance(440.0))) {
            if (sm.onFrame(f, templates) is WakeGatedRecognizer.Outcome.Woke) {
                woke = true
                break
            }
        }
        assertThat(woke).isTrue()

        val outcomes = frames(longUtterance(250.0)).map { sm.onFrame(it, templates) }
        val matches = outcomes.filterIsInstance<WakeGatedRecognizer.Outcome.Recognized>().map { it.result }
        assertThat(matches.any { it is RecognitionResult.Match && it.commandId == yes }).isTrue()
    }

    @Test
    fun `reset clears the partially-filled command buffer`() {
        val sm = WakeGatedRecognizer(recognizer, WakeWordGate(mfcc, matcher, BIG), vad, RATE)
        val templates = listOf(enroll(250.0, yes))

        // Half-fill the 10-frame window, then reset.
        val all = frames(longUtterance(250.0))
        all.take(5).forEach { sm.onFrame(it, templates) }
        sm.reset()

        // 9 fresh frames is < the 10 needed for a window, so nothing recognizes (proves the 5 were dropped).
        val after = all.drop(5).take(9).map { sm.onFrame(it, templates) }
        assertThat(after.none { it is WakeGatedRecognizer.Outcome.Recognized }).isTrue()
    }

    private companion object {
        const val RATE = 16_000
        const val BIG = 1_000_000f
    }
}
