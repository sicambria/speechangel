package com.speechangel.app.ui.packs

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.speechangel.app.action.DeviceAction
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.data.pack.CommandPack
import com.speechangel.data.pack.CommandPackCodec
import com.speechangel.data.pack.CommandPackException
import com.speechangel.data.pack.CommandPackExporter
import com.speechangel.data.pack.CommandPackImporter
import com.speechangel.data.pack.PackImportResult
import com.speechangel.data.pack.RejectedCommand
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

data class CommandPackUiState(
    val exportedJson: String? = null,
    val importedCount: Int = 0,
    val rejected: List<RejectedCommand> = emptyList(),
    val error: String? = null,
    val lastImportRan: Boolean = false,
)

/**
 * Import/export the shareable command pack. Because packs carry no audio (the matcher is
 * speaker-dependent), an import creates command *definitions* the user then re-enrols in their own
 * voice. Every imported action id is validated against [DeviceAction] so a pack can never introduce an
 * action this build cannot perform.
 */
@HiltViewModel
class CommandPackViewModel @Inject constructor(private val commandRepository: CommandRepository) : ViewModel() {

    private val _state = MutableStateFlow(CommandPackUiState())
    val state: StateFlow<CommandPackUiState> = _state.asStateFlow()

    /** Build a pack from the user's current commands (definitions only). */
    suspend fun exportToPack(name: String, author: String): CommandPack =
        CommandPackExporter.export(name, author, commandRepository.observeCommands().first())

    /** Validate a decoded pack against the action table and persist the accepted commands. */
    suspend fun importFromPack(pack: CommandPack): PackImportResult {
        val result = CommandPackImporter.validate(pack) { DeviceAction.fromId(it) != null }
        for (c in result.accepted) {
            commandRepository.upsertCommand(
                VoiceCommand(CommandId(UUID.randomUUID().toString()), c.label, ActionId(c.actionId)),
            )
        }
        return result
    }

    fun export(name: String, author: String) {
        viewModelScope.launch {
            val json = CommandPackCodec.encode(exportToPack(name, author))
            _state.update { it.copy(exportedJson = json, error = null) }
        }
    }

    fun import(json: String) {
        viewModelScope.launch {
            val pack = try {
                CommandPackCodec.decode(json)
            } catch (e: CommandPackException) {
                _state.update { it.copy(error = e.message ?: "Invalid command pack", lastImportRan = true) }
                return@launch
            }
            val result = importFromPack(pack)
            _state.update {
                it.copy(importedCount = result.accepted.size, rejected = result.rejected, error = null, lastImportRan = true)
            }
        }
    }
}
