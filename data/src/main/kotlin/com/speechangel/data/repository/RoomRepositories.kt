package com.speechangel.data.repository

import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.data.db.SpeechAngelDao
import com.speechangel.data.db.toDomain
import com.speechangel.data.db.toEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

internal class RoomCommandRepository @Inject constructor(private val dao: SpeechAngelDao) : CommandRepository {
    override fun observeCommands(): Flow<List<VoiceCommand>> = dao.observeCommands().map { list -> list.map { it.toDomain() } }

    override suspend fun getCommand(id: CommandId): VoiceCommand? = dao.getCommand(id.value)?.toDomain()

    override suspend fun upsertCommand(command: VoiceCommand) = dao.upsertCommand(command.toEntity())

    override suspend fun deleteCommand(id: CommandId) = dao.deleteCommand(id.value)
}

internal class RoomTemplateRepository @Inject constructor(private val dao: SpeechAngelDao) : TemplateRepository {
    override fun observeTemplates(): Flow<List<Template>> = dao.observeTemplates().map { list -> list.map { it.toDomain() } }

    override suspend fun allTemplates(): List<Template> = dao.allTemplates().map { it.toDomain() }

    override suspend fun templatesFor(commandId: CommandId): List<Template> = dao.templatesFor(commandId.value).map { it.toDomain() }

    override suspend fun countFor(commandId: CommandId): Int = dao.countFor(commandId.value)

    override suspend fun addTemplate(template: Template) = dao.addTemplate(template.toEntity())

    override suspend fun deleteTemplate(id: TemplateId) = dao.deleteTemplateById(id.value)

    override suspend fun deleteTemplatesFor(commandId: CommandId) = dao.deleteTemplatesFor(commandId.value)
}
