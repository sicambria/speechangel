package com.speechangel.core.enrollment

import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCommand
import kotlinx.coroutines.flow.Flow

/** Persistence boundary for user-defined commands (implemented in the data layer with Room). */
interface CommandRepository {
    fun observeCommands(): Flow<List<VoiceCommand>>
    suspend fun getCommand(id: CommandId): VoiceCommand?
    suspend fun upsertCommand(command: VoiceCommand)
    suspend fun deleteCommand(id: CommandId)
}

/** Persistence boundary for enrolled acoustic templates. */
interface TemplateRepository {
    fun observeTemplates(): Flow<List<Template>>
    suspend fun allTemplates(): List<Template>
    suspend fun templatesFor(commandId: CommandId): List<Template>
    suspend fun countFor(commandId: CommandId): Int
    suspend fun addTemplate(template: Template)
    suspend fun deleteTemplate(id: TemplateId)
    suspend fun deleteTemplatesFor(commandId: CommandId)
}
