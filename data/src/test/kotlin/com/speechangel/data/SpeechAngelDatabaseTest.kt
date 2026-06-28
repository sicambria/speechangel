package com.speechangel.data

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.FeatureSequence
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.core.model.VoiceCondition
import com.speechangel.data.db.SpeechAngelDatabase
import com.speechangel.data.db.toDomain
import com.speechangel.data.db.toEntity
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class SpeechAngelDatabaseTest {

    private lateinit var database: SpeechAngelDatabase

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(context, SpeechAngelDatabase::class.java)
            .allowMainThreadQueries()
            .build()
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun `command and template round-trip through Room, preserving features`() = runBlocking<Unit> {
        val dao = database.dao()
        val command = VoiceCommand(CommandId("yes"), "Yes", ActionId("HOME"))
        dao.upsertCommand(command.toEntity())

        val features = FeatureSequence(listOf(floatArrayOf(1f, 2f, 3f), floatArrayOf(-1f, 0f, 0.5f)))
        val template = Template(TemplateId("t1"), CommandId("yes"), features, VoiceCondition.TIRED, 99L)
        dao.addTemplate(template.toEntity())

        assertThat(dao.getCommand("yes")?.toDomain()).isEqualTo(command)
        assertThat(dao.countFor("yes")).isEqualTo(1)

        val restored = dao.templatesFor("yes").single().toDomain()
        assertThat(restored.condition).isEqualTo(VoiceCondition.TIRED)
        assertThat(restored.createdAtEpochMs).isEqualTo(99L)
        assertThat(restored.features.frameCount).isEqualTo(2)
        assertThat(restored.features.frames[0]).usingExactEquality().containsExactly(1f, 2f, 3f)
    }

    @Test
    fun `deleting a command cascades to its templates`() = runBlocking<Unit> {
        val dao = database.dao()
        dao.upsertCommand(VoiceCommand(CommandId("no"), "No", ActionId("BACK")).toEntity())
        val features = FeatureSequence(listOf(floatArrayOf(0f, 1f)))
        dao.addTemplate(Template(TemplateId("t2"), CommandId("no"), features).toEntity())

        dao.deleteCommand("no")

        assertThat(dao.countFor("no")).isEqualTo(0)
        assertThat(dao.allTemplates()).isEmpty()
    }
}
