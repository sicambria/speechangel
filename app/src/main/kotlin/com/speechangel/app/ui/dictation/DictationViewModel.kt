package com.speechangel.app.ui.dictation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.core.enrollment.DictationBackend
import com.speechangel.core.enrollment.DictationRejection
import com.speechangel.core.model.AudioSamples
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DictationUiState(val transcript: String = "", val message: String? = null)

/**
 * Optional dictate-to-a-text-field surface (Phase 3, stub). It talks only to the neutral
 * [DictationBackend] seam — never the command recogniser — so it stays out of the deterministic
 * command→action path entirely. The shipping backend is [com.speechangel.core.enrollment.NoopDictationBackend],
 * so a dictate attempt reports "unavailable"; real audio capture is wired together with a real
 * whisper.cpp backend (Bucket C), at which point the transcript branch below goes live unchanged.
 */
@HiltViewModel
class DictationViewModel @Inject constructor(private val dictation: DictationBackend) : ViewModel() {

    private val _state = MutableStateFlow(DictationUiState())
    val state: StateFlow<DictationUiState> = _state.asStateFlow()

    /**
     * Probe the dictation seam. Until a real backend + recorder land, the clip is empty and the Noop
     * backend reports [DictationRejection.BACKEND_UNAVAILABLE]; the real-backend path returns a
     * transcript the same way.
     */
    fun dictate() {
        viewModelScope.launch {
            val result = dictation.transcribe(AudioSamples(FloatArray(0), SAMPLE_RATE_HZ))
            _state.update {
                when (result.reason) {
                    DictationRejection.BACKEND_UNAVAILABLE ->
                        it.copy(message = "Dictation isn't available in this build yet.")
                    DictationRejection.NO_SPEECH ->
                        it.copy(message = "I didn't hear anything to transcribe.")
                    null ->
                        it.copy(transcript = result.transcript, message = null)
                }
            }
        }
    }

    private companion object {
        const val SAMPLE_RATE_HZ = 16_000
    }
}
