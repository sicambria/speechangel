package com.speechangel.app.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.model.VoiceCommand
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

data class CommandRow(val command: VoiceCommand, val templateCount: Int)
data class HomeUiState(val commands: List<CommandRow> = emptyList())

@HiltViewModel
class HomeViewModel @Inject constructor(commandRepository: CommandRepository, templateRepository: TemplateRepository) : ViewModel() {

    val state: StateFlow<HomeUiState> =
        combine(
            commandRepository.observeCommands(),
            templateRepository.observeTemplates(),
        ) { commands, templates ->
            HomeUiState(
                commands = commands.map { command ->
                    CommandRow(command, templates.count { it.commandId == command.id })
                },
            )
        }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_TIMEOUT_MS), HomeUiState())

    private companion object {
        const val STOP_TIMEOUT_MS = 5_000L
    }
}
