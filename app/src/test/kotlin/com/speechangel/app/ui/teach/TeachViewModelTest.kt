package com.speechangel.app.ui.teach

import com.google.common.truth.Truth.assertThat
import com.speechangel.app.action.DeviceAction
import com.speechangel.app.testutil.FakeAudioRecorder
import com.speechangel.app.testutil.FakeCommandRepository
import com.speechangel.app.testutil.FakeTemplateRepository
import com.speechangel.app.testutil.MainDispatcherRule
import com.speechangel.app.testutil.SilentAudioRecorder
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.QualityIssue
import com.speechangel.data.audio.AudioRecorder
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Rule
import org.junit.Test
import java.util.UUID

@OptIn(ExperimentalCoroutinesApi::class)
class TeachViewModelTest {

    @get:Rule
    val mainRule = MainDispatcherRule()

    private val commands = FakeCommandRepository()
    private val templates = FakeTemplateRepository()

    private fun viewModel(recorder: AudioRecorder) = TeachViewModel(
        enroller = Enroller(MfccExtractor(), EnergyVad(), idGenerator = { UUID.randomUUID().toString() }),
        recorder = recorder,
        commandRepository = commands,
        templateRepository = templates,
    )

    @Test
    fun `recording a good example stores a template and persists the command`() = runTest(mainRule.dispatcher) {
        val vm = viewModel(FakeAudioRecorder(freqHz = 250.0))
        vm.onLabelChange("home")
        vm.onActionChange(DeviceAction.HOME)

        vm.recordExample()
        advanceUntilIdle()

        assertThat(vm.state.value.recordedCount).isEqualTo(1)
        assertThat(vm.state.value.justSucceeded).isTrue()
        assertThat(vm.state.value.lastIssue).isNull()
        assertThat(templates.allTemplates()).hasSize(1)
        val saved = commands.observeCommands().value.single()
        assertThat(saved.label).isEqualTo("home")
        assertThat(saved.action.value).isEqualTo("HOME")
    }

    @Test
    fun `a silent recording is rejected and stores nothing`() = runTest(mainRule.dispatcher) {
        val vm = viewModel(SilentAudioRecorder())
        vm.onLabelChange("home")

        vm.recordExample()
        advanceUntilIdle()

        assertThat(vm.state.value.recordedCount).isEqualTo(0)
        assertThat(vm.state.value.lastIssue).isEqualTo(QualityIssue.SILENT)
        assertThat(templates.allTemplates()).isEmpty()
    }

    @Test
    fun `cannot record without a label`() {
        val vm = viewModel(FakeAudioRecorder(freqHz = 250.0))
        assertThat(vm.state.value.canRecord).isFalse()
        vm.onLabelChange("yes")
        assertThat(vm.state.value.canRecord).isTrue()
    }
}
