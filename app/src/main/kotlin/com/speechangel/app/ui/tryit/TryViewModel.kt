package com.speechangel.app.ui.tryit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.enrollment.TemplateRepository
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

data class TryUiState(val isListening: Boolean = false, val result: TryResult? = null)

@HiltViewModel
class TryViewModel @Inject constructor(
    private val recognizer: Recognizer,
    private val recorder: AudioRecorder,
    private val templateRepository: TemplateRepository,
    private val commandRepository: CommandRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(TryUiState())
    val state: StateFlow<TryUiState> = _state.asStateFlow()

    fun listen() {
        if (_state.value.isListening) return
        _state.update { it.copy(isListening = true, result = null) }
        viewModelScope.launch {
            val templates = templateRepository.allTemplates()
            if (templates.isEmpty()) {
                _state.update { it.copy(isListening = false, result = TryResult.NoCommands) }
                return@launch
            }
            val audio = recorder.record(RECORD_MS)
            val result = when (val recognition = recognizer.recognize(audio, templates)) {
                is RecognitionResult.Match -> {
                    val label = commandRepository.getCommand(recognition.commandId)?.label ?: recognition.commandId.value
                    TryResult.Heard(label, recognition.confidence)
                }
                is RecognitionResult.NoMatch -> TryResult.NotSure
            }
            _state.update { it.copy(isListening = false, result = result) }
        }
    }

    private companion object {
        const val RECORD_MS = 1_500
    }
}
