package com.speechangel.app.ui.teach

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.app.action.DeviceAction
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.EnrollmentResult
import com.speechangel.core.enrollment.QualityIssue
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.matching.VocabularyDistinctness
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.core.model.VoiceCondition
import com.speechangel.data.audio.AudioRecorder
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class TeachUiState(
    val label: String = "",
    val action: DeviceAction = DeviceAction.default,
    val recordedCount: Int = 0,
    val isRecording: Boolean = false,
    val lastIssue: QualityIssue? = null,
    val justSucceeded: Boolean = false,
    /** Labels of existing commands this one sounds acoustically close to (advisory nudge). */
    val closeToLabels: List<String> = emptyList(),
) {
    val canRecord: Boolean get() = label.isNotBlank() && !isRecording
    val canFinish: Boolean get() = recordedCount > 0
}

@HiltViewModel
class TeachViewModel @Inject constructor(
    private val enroller: Enroller,
    private val recorder: AudioRecorder,
    private val commandRepository: CommandRepository,
    private val templateRepository: TemplateRepository,
    private val matcher: TemplateMatcher,
) : ViewModel() {

    private val commandId = CommandId(UUID.randomUUID().toString())
    private val _state = MutableStateFlow(TeachUiState())
    val state: StateFlow<TeachUiState> = _state.asStateFlow()

    fun onLabelChange(value: String) = _state.update { it.copy(label = value) }
    fun onActionChange(action: DeviceAction) = _state.update { it.copy(action = action) }

    /** Records one example of the command and, if good enough, stores it as a template. */
    fun recordExample() {
        val current = _state.value
        if (!current.canRecord) return
        _state.update { it.copy(isRecording = true, justSucceeded = false, lastIssue = null) }
        viewModelScope.launch {
            persistCommand(current)
            val audio = recorder.record(RECORD_MS)
            when (val result = enroller.enroll(audio, commandId, VoiceCondition.NORMAL)) {
                is EnrollmentResult.Success -> {
                    templateRepository.addTemplate(result.template)
                    _state.update {
                        it.copy(isRecording = false, recordedCount = it.recordedCount + 1, justSucceeded = true)
                    }
                    checkDistinctness()
                }
                is EnrollmentResult.Rejected -> {
                    _state.update { it.copy(isRecording = false, lastIssue = result.reason) }
                }
            }
        }
    }

    /**
     * After a template lands, warn (advisory only) if this command is acoustically close to another
     * enrolled command — a caregiver can then pick a more distinct word. Never blocks enrollment.
     */
    private suspend fun checkDistinctness() {
        val grouped = templateRepository.allTemplates().groupBy { it.commandId }
        if (grouped.size < 2) return
        val closePairs = VocabularyDistinctness.analyze(grouped, matcher)
            .filter { it.a == commandId || it.b == commandId }
        val labels = closePairs
            .map { if (it.a == commandId) it.b else it.a }
            .distinct()
            .mapNotNull { commandRepository.getCommand(it)?.label }
        _state.update { it.copy(closeToLabels = labels) }
    }

    private suspend fun persistCommand(state: TeachUiState) {
        commandRepository.upsertCommand(
            VoiceCommand(id = commandId, label = state.label.trim(), action = ActionId(state.action.id)),
        )
    }

    private companion object {
        const val RECORD_MS = 1_500
    }
}
