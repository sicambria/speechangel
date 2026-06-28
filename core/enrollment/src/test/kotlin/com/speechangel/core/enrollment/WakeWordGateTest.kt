package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.VoiceCondition
import org.junit.Test

class WakeWordGateTest {

    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()
    private val gate = WakeWordGate(mfcc, TemplateMatcher(), wakeThreshold = BIG)

    private fun enrollWake(freq: Double): Template {
        var n = 0L
        val enroller = Enroller(mfcc, vad, idGenerator = { "w${n++}" }, clock = { n })
        return (enroller.enroll(TestSignals.utterance(freq), ReservedCommands.WAKE) as EnrollmentResult.Success).template
    }

    @Test
    fun `no wake templates yields NO_WAKE_ENROLLED`() {
        val decision = gate.evaluate(vad.trim(TestSignals.utterance(440.0)), emptyList())
        assertThat(decision).isInstanceOf(WakeDecision.NoWake::class.java)
        assertThat((decision as WakeDecision.NoWake).reason).isEqualTo(WakeReason.NO_WAKE_ENROLLED)
    }

    @Test
    fun `the wake word matches itself closer than a different utterance`() {
        val templates = listOf(enrollWake(440.0))
        val self = gate.evaluate(vad.trim(TestSignals.utterance(440.0)), templates) as WakeDecision.Wake
        val other = gate.evaluate(vad.trim(TestSignals.utterance(880.0)), templates) as WakeDecision.Wake
        assertThat(self.distance).isLessThan(other.distance)
    }

    @Test
    fun `a threshold between self and other wakes on self and rejects the other`() {
        val templates = listOf(enrollWake(440.0))
        val self = gate.evaluate(vad.trim(TestSignals.utterance(440.0)), templates) as WakeDecision.Wake
        val other = gate.evaluate(vad.trim(TestSignals.utterance(880.0)), templates) as WakeDecision.Wake
        val mid = (self.distance + other.distance) / 2f
        val tight = WakeWordGate(mfcc, TemplateMatcher(), wakeThreshold = mid)
        assertThat(tight.evaluate(vad.trim(TestSignals.utterance(440.0)), templates)).isInstanceOf(WakeDecision.Wake::class.java)
        val rejected = tight.evaluate(vad.trim(TestSignals.utterance(880.0)), templates)
        assertThat(rejected).isInstanceOf(WakeDecision.NoWake::class.java)
        assertThat((rejected as WakeDecision.NoWake).reason).isEqualTo(WakeReason.BELOW_THRESHOLD)
    }

    @Test
    fun `reserved wake templates are excluded from the Stage-2 candidate set`() {
        val wake = enrollWake(440.0)
        val command = Template(
            id = com.speechangel.core.model.TemplateId("cmd1"),
            commandId = CommandId("light"),
            features = wake.features,
            condition = VoiceCondition.NORMAL,
        )
        val stage2 = ReservedCommands.commandTemplates(listOf(wake, command))
        assertThat(stage2.map { it.commandId }).containsExactly(CommandId("light"))
        assertThat(stage2.none { it.commandId == ReservedCommands.WAKE }).isTrue()
    }

    private companion object {
        const val BIG = 1_000_000f
    }
}
