package com.speechangel.app.ui.packs

import com.google.common.truth.Truth.assertThat
import com.speechangel.app.testutil.FakeCommandRepository
import com.speechangel.app.testutil.MainDispatcherRule
import com.speechangel.core.model.ActionId
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCommand
import com.speechangel.data.pack.CommandPack
import com.speechangel.data.pack.PackCommand
import com.speechangel.data.pack.RejectReason
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class CommandPackViewModelTest {

    @get:Rule
    val mainRule = MainDispatcherRule()

    private val commands = FakeCommandRepository()
    private val viewModel = CommandPackViewModel(commands)

    @Test
    fun `export builds a definitions-only pack from the user's commands`() = runTest {
        commands.upsertCommand(VoiceCommand(CommandId("a"), "Home", ActionId("HOME")))
        commands.upsertCommand(VoiceCommand(CommandId("b"), "Go back", ActionId("BACK")))

        val pack = viewModel.exportToPack("Starter", "me")

        assertThat(pack.commands).containsExactly(PackCommand("Home", "HOME"), PackCommand("Go back", "BACK"))
    }

    @Test
    fun `import upserts valid commands and rejects unknown actions against DeviceAction`() = runTest {
        val pack = CommandPack(
            schemaVersion = 1,
            name = "Mixed",
            author = "x",
            commands = listOf(
                PackCommand("Home", "HOME"),
                PackCommand("Launch nukes", "NUKES"),
            ),
        )

        val result = viewModel.importFromPack(pack)

        assertThat(result.accepted).containsExactly(PackCommand("Home", "HOME"))
        assertThat(result.rejected.single().reason).isEqualTo(RejectReason.UNKNOWN_ACTION)
        // The accepted command was persisted (with a fresh id) for the user to re-enrol.
        val stored = commands.observeCommands().value
        assertThat(stored.map { it.label to it.action.value }).containsExactly("Home" to "HOME")
    }
}
