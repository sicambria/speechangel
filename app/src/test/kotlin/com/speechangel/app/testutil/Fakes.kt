package com.speechangel.app.testutil

import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.data.audio.AudioRecorder
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlin.math.PI
import kotlin.math.sin

class FakeCommandRepository : CommandRepository {
    private val commands = MutableStateFlow<List<VoiceCommand>>(emptyList())
    override fun observeCommands() = commands.asStateFlow()
    override suspend fun getCommand(id: CommandId) = commands.value.firstOrNull { it.id == id }
    override suspend fun upsertCommand(command: VoiceCommand) {
        commands.value = commands.value.filterNot { it.id == command.id } + command
    }
    override suspend fun deleteCommand(id: CommandId) {
        commands.value = commands.value.filterNot { it.id == id }
    }
}

class FakeTemplateRepository : TemplateRepository {
    private val templates = MutableStateFlow<List<Template>>(emptyList())
    override fun observeTemplates() = templates.asStateFlow()
    override suspend fun allTemplates() = templates.value
    override suspend fun templatesFor(commandId: CommandId) = templates.value.filter { it.commandId == commandId }
    override suspend fun countFor(commandId: CommandId) = templatesFor(commandId).size
    override suspend fun addTemplate(template: Template) {
        templates.value = templates.value + template
    }
    override suspend fun deleteTemplate(id: TemplateId) {
        templates.value = templates.value.filterNot { it.id == id }
    }
    override suspend fun deleteTemplatesFor(commandId: CommandId) {
        templates.value = templates.value.filterNot { it.commandId == commandId }
    }
}

/** Returns a fixed, silence-padded tone so the energy VAD can endpoint it. */
class FakeAudioRecorder(private val freqHz: Double, private val toneMs: Int = 400, override val sampleRateHz: Int = 16_000) :
    AudioRecorder {
    override suspend fun record(durationMs: Int): AudioSamples {
        val pad = FloatArray(sampleRateHz * 150 / 1000)
        val n = sampleRateHz * toneMs / 1000
        val tone = FloatArray(n) { i ->
            val t = i.toDouble() / sampleRateHz
            (0.3 * sin(2.0 * PI * freqHz * t) + 0.15 * sin(2.0 * PI * 2 * freqHz * t)).toFloat()
        }
        return AudioSamples(pad + tone + pad, sampleRateHz)
    }

    override fun stream(frameMs: Int): kotlinx.coroutines.flow.Flow<AudioSamples> = kotlinx.coroutines.flow.flow { emit(record(frameMs)) }
}

/** A recorder that yields pure silence (for rejection paths). */
class SilentAudioRecorder(override val sampleRateHz: Int = 16_000) : AudioRecorder {
    override suspend fun record(durationMs: Int) = AudioSamples(FloatArray(sampleRateHz * durationMs / 1000), sampleRateHz)
    override fun stream(frameMs: Int): kotlinx.coroutines.flow.Flow<AudioSamples> = kotlinx.coroutines.flow.flow { emit(record(frameMs)) }
}
