package com.speechangel.app.ui.tryit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.EnrollmentResult
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.enrollment.decideAdaptation
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.RecognitionResult
import com.speechangel.data.audio.AudioRecorder
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface TryResult {
    data class Heard(val label: String, val confidence: Float) : TryResult
    data object NotSure : TryResult
    data object NoCommands : TryResult
}

data class TryUiState(
    val isListening: Boolean = false,
    val result: TryResult? = null,
    val canAdapt: Boolean = false,
    val adapted: Boolean = false,
)

@HiltViewModel
class TryViewModel @Inject constructor(
    private val recognizer: Recognizer,
    private val recorder: AudioRecorder,
    private val templateRepository: TemplateRepository,
    private val commandRepository: CommandRepository,
    private val enroller: Enroller,
    private val matcher: TemplateMatcher,
) : ViewModel() {

    private val _state = MutableStateFlow(TryUiState())
    val state: StateFlow<TryUiState> = _state.asStateFlow()

    private var lastAudio: AudioSamples? = null
    private var lastMatch: RecognitionResult.Match? = null

    fun listen() {
        if (_state.value.isListening) return
        _state.update { it.copy(isListening = true, result = null, canAdapt = false, adapted = false) }
        viewModelScope.launch {
            val templates = templateRepository.allTemplates()
            if (templates.isEmpty()) {
                _state.update { it.copy(isListening = false, result = TryResult.NoCommands) }
                return@launch
            }
            val audio = recorder.record(RECORD_MS)
            val result = when (val recognition = recognizer.recognize(audio, templates)) {
                is RecognitionResult.Match -> {
                    lastAudio = audio
                    lastMatch = recognition
                    val label = commandRepository.getCommand(recognition.commandId)?.label ?: recognition.commandId.value
                    TryResult.Heard(label, recognition.confidence)
                }
                is RecognitionResult.NoMatch -> {
                    lastAudio = null
                    lastMatch = null
                    TryResult.NotSure
                }
            }
            _state.update { it.copy(isListening = false, result = result, canAdapt = result is TryResult.Heard) }
        }
    }

    fun rememberThis() {
        val audio = lastAudio ?: return
        val match = lastMatch ?: return
        viewModelScope.launch {
            val existing = templateRepository.templatesFor(match.commandId)
            when (val enrolled = enroller.enroll(audio, match.commandId)) {
                is EnrollmentResult.Success -> {
                    val decision = decideAdaptation(
                        existing = existing,
                        candidate = enrolled.template,
                        distance = { a, b -> matcher.distance(a, b) },
                    )
                    templateRepository.addTemplate(decision.toAdd)
                    decision.toRemove.forEach { templateRepository.deleteTemplate(it) }
                    lastAudio = null
                    lastMatch = null
                    _state.update { it.copy(canAdapt = false, adapted = true) }
                }
                is EnrollmentResult.Rejected -> {
                    lastAudio = null
                    lastMatch = null
                    _state.update { it.copy(canAdapt = false) }
                }
            }
        }
    }

    private companion object {
        const val RECORD_MS = 1_500
    }
}
