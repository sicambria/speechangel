package com.speechangel.app.ui.tryit

import com.google.common.truth.Truth.assertThat
import com.speechangel.app.testutil.FakeAudioRecorder
import com.speechangel.app.testutil.FakeCommandRepository
import com.speechangel.app.testutil.FakeTemplateRepository
import com.speechangel.app.testutil.MainDispatcherRule
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.EnrollmentResult
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.data.audio.AudioRecorder
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Rule
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sin

@OptIn(ExperimentalCoroutinesApi::class)
class TryViewModelTest {

    @get:Rule
    val mainRule = MainDispatcherRule()

    private val commands = FakeCommandRepository()
    private val templates = FakeTemplateRepository()
    private val mfcc = MfccExtractor()
    private val vad = EnergyVad()

    // Generous threshold: VM/label-mapping logic under test, not threshold calibration.
    private val matcher = TemplateMatcher(MatcherConfig(defaultAcceptanceThreshold = 1_000f))
    private val recognizer = Recognizer(mfcc, vad, matcher)
    private var vmIdCounter = 0
    private val enroller = Enroller(mfcc, vad, idGenerator = { "vm-${vmIdCounter++}" })

    private fun viewModel(recorder: AudioRecorder) = TryViewModel(recognizer, recorder, templates, commands, enroller, matcher)

    private fun enroll(freq: Double, command: String, label: String) = runBlocking {
        commands.upsertCommand(VoiceCommand(CommandId(command), label, ActionId("HOME")))
        val enroller = Enroller(mfcc, vad, idGenerator = { "$command-${freq.toInt()}" })
        val audio = paddedTone(freq)
        val result = enroller.enroll(audio, CommandId(command))
        templates.addTemplate((result as EnrollmentResult.Success).template)
    }

    private fun paddedTone(freq: Double, sr: Int = 16_000): AudioSamples {
        val pad = FloatArray(sr * 150 / 1000)
        val n = sr * 400 / 1000
        val tone = FloatArray(n) { i ->
            val t = i.toDouble() / sr
            (0.3 * sin(2.0 * PI * freq * t) + 0.15 * sin(2.0 * PI * 2 * freq * t)).toFloat()
        }
        return AudioSamples(pad + tone + pad, sr)
    }

    @Test
    fun `with no commands enrolled, listening reports NoCommands`() = runTest(mainRule.dispatcher) {
        val vm = viewModel(FakeAudioRecorder(250.0))
        vm.listen()
        advanceUntilIdle()
        assertThat(vm.state.value.result).isEqualTo(TryResult.NoCommands)
    }

    @Test
    fun `a recognised command is reported with its label`() = runTest(mainRule.dispatcher) {
        enroll(250.0, "yes", "Yes please")
        enroll(1500.0, "no", "No thanks")

        val vm = viewModel(FakeAudioRecorder(250.0))
        vm.listen()
        advanceUntilIdle()

        val result = vm.state.value.result
        assertThat(result).isInstanceOf(TryResult.Heard::class.java)
        assertThat((result as TryResult.Heard).label).isEqualTo("Yes please")
    }

    @Test
    fun `rememberThis adds a second template after a Match`() = runTest(mainRule.dispatcher) {
        enroll(250.0, "yes", "Yes please")

        val vm = viewModel(FakeAudioRecorder(250.0))
        vm.listen()
        advanceUntilIdle()
        assertThat(vm.state.value.canAdapt).isTrue()

        vm.rememberThis()
        advanceUntilIdle()

        assertThat(templates.countFor(CommandId("yes"))).isEqualTo(2)
        assertThat(vm.state.value.adapted).isTrue()
        assertThat(vm.state.value.canAdapt).isFalse()
    }

    @Test
    fun `rememberThis is a no-op when no prior recognition`() = runTest(mainRule.dispatcher) {
        enroll(250.0, "yes", "Yes please")
        val vm = viewModel(FakeAudioRecorder(250.0))

        vm.rememberThis()
        advanceUntilIdle()

        assertThat(templates.countFor(CommandId("yes"))).isEqualTo(1)
        assertThat(vm.state.value.adapted).isFalse()
        assertThat(vm.state.value.canAdapt).isFalse()
    }
}
