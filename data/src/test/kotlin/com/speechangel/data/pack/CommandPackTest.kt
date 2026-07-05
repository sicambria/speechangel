package com.speechangel.data.pack

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCommand
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

/** org.json is provided by Robolectric at test time. */
@RunWith(RobolectricTestRunner::class)
class CommandPackTest {

    private val known = setOf("HOME", "BACK", "FLASHLIGHT")
    private fun isKnown(id: String) = id in known

    @Test
    fun `export then encode then decode round-trips the command set`() {
        val commands = listOf(
            VoiceCommand(CommandId("c1"), "Home", ActionId("HOME")),
            VoiceCommand(CommandId("c2"), "Go back", ActionId("BACK")),
        )
        val pack = CommandPackExporter.export("Starter", "Ada", commands)
        val decoded = CommandPackCodec.decode(CommandPackCodec.encode(pack))

        assertThat(decoded.name).isEqualTo("Starter")
        assertThat(decoded.author).isEqualTo("Ada")
        assertThat(decoded.commands).containsExactly(
            PackCommand("Home", "HOME"),
            PackCommand("Go back", "BACK"),
        )
    }

    @Test
    fun `import validates action ids and reports what it rejects, never silently drops`() {
        val pack = CommandPack(
            schemaVersion = 1,
            name = "Mixed",
            author = "x",
            commands = listOf(
                PackCommand("Flashlight", "FLASHLIGHT"),
                PackCommand("Launch nukes", "NUKES"), // unknown action
                PackCommand("", "HOME"), // blank label
            ),
        )
        val result = CommandPackImporter.validate(pack, ::isKnown)

        assertThat(result.accepted).containsExactly(PackCommand("Flashlight", "FLASHLIGHT"))
        assertThat(result.rejected.map { it.reason }).containsExactly(RejectReason.UNKNOWN_ACTION, RejectReason.BLANK_LABEL)
    }

    @Test
    fun `a future schema version is refused`() {
        val future = CommandPackCodec.encode(CommandPack(99, "n", "a", emptyList()))
        try {
            CommandPackCodec.decode(future)
            throw AssertionError("expected CommandPackException")
        } catch (e: CommandPackException) {
            assertThat(e).hasMessageThat().contains("newer")
        }
    }

    @Test
    fun `malformed input is refused with a CommandPackException`() {
        try {
            CommandPackCodec.decode("definitely not json")
            throw AssertionError("expected CommandPackException")
        } catch (e: CommandPackException) {
            assertThat(e).hasMessageThat().isNotEmpty()
        }
    }
}
