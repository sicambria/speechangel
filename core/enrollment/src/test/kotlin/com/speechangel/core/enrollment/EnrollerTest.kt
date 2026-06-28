package com.speechangel.core.enrollment

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import org.junit.Test
import java.util.concurrent.atomic.AtomicInteger

class EnrollerTest {

    private val ids = AtomicInteger(0)
    private fun enroller(minFrames: Int = 8) = Enroller(
        mfcc = MfccExtractor(),
        vad = EnergyVad(),
        minSpeechFrames = minFrames,
        idGenerator = { "t${ids.incrementAndGet()}" },
        clock = { 42L },
    )

    @Test
    fun `a clean utterance enrolls successfully`() {
        val result = enroller().enroll(
            TestSignals.utterance(300.0),
            CommandId("yes"),
            VoiceCondition.NORMAL,
        )
        assertThat(result).isInstanceOf(EnrollmentResult.Success::class.java)
        val template = (result as EnrollmentResult.Success).template
        assertThat(template.commandId).isEqualTo(CommandId("yes"))
        assertThat(template.features.frameCount).isGreaterThan(0)
        assertThat(template.createdAtEpochMs).isEqualTo(42L)
    }

    @Test
    fun `silence is rejected as SILENT`() {
        val result = enroller().enroll(TestSignals.silence(500), CommandId("yes"))
        assertThat((result as EnrollmentResult.Rejected).reason).isEqualTo(QualityIssue.SILENT)
    }

    @Test
    fun `empty audio is rejected as TOO_SHORT`() {
        val result = enroller().enroll(AudioSamples(FloatArray(0), 16_000), CommandId("yes"))
        assertThat((result as EnrollmentResult.Rejected).reason).isEqualTo(QualityIssue.TOO_SHORT)
    }

    @Test
    fun `too few frames is rejected`() {
        // Demand an unrealistically high frame count so a normal utterance is rejected.
        val result = enroller(minFrames = 10_000).enroll(TestSignals.utterance(300.0), CommandId("yes"))
        assertThat((result as EnrollmentResult.Rejected).reason).isEqualTo(QualityIssue.TOO_FEW_FRAMES)
    }
}
