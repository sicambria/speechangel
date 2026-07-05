package com.speechangel.app.ui.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Suppress("LongParameterList") // Home is the hub screen: hoisted navigation callbacks, one per destination.
@Composable
fun HomeScreen(
    isListening: Boolean,
    onListeningChange: (Boolean) -> Unit,
    onAddCommand: () -> Unit,
    onTryIt: () -> Unit,
    onOpenAlwaysOn: () -> Unit = {},
    onStartSetup: () -> Unit = {},
    onOpenPacks: () -> Unit = {},
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { TopAppBar(title = { Text("SpeechAngel") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            ListeningCard(isListening = isListening, onListeningChange = onListeningChange)

            Text("Your commands", style = MaterialTheme.typography.titleLarge)

            if (state.commands.isEmpty()) {
                Text(
                    "No commands yet. Tap “Teach a new command” to record your first one.",
                    style = MaterialTheme.typography.bodyLarge,
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxWidth().weight(1f),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(state.commands, key = { it.command.id.value }) { row ->
                        CommandCard(row)
                    }
                }
            }

            OutlinedButton(
                onClick = onTryIt,
                modifier = Modifier.fillMaxWidth().height(64.dp),
            ) {
                Icon(Icons.Filled.Mic, contentDescription = null)
                Spacer(Modifier.height(0.dp))
                Text("  Try it", style = MaterialTheme.typography.labelLarge)
            }
            androidx.compose.material3.Button(
                onClick = onAddCommand,
                modifier = Modifier.fillMaxWidth().height(64.dp),
            ) {
                Icon(Icons.Filled.Add, contentDescription = null)
                Text("  Teach a new command", style = MaterialTheme.typography.labelLarge)
            }
            OutlinedButton(onClick = onStartSetup, modifier = Modifier.fillMaxWidth()) {
                Text("Set up step by step", style = MaterialTheme.typography.labelLarge)
            }
            OutlinedButton(onClick = onOpenAlwaysOn, modifier = Modifier.fillMaxWidth()) {
                Text("Always-on settings", style = MaterialTheme.typography.labelLarge)
            }
            OutlinedButton(onClick = onOpenPacks, modifier = Modifier.fillMaxWidth()) {
                Text("Command packs", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun ListeningCard(isListening: Boolean, onListeningChange: (Boolean) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp)
                .semantics { contentDescription = if (isListening) "Listening is on" else "Listening is off" },
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text("Always-on listening", style = MaterialTheme.typography.titleLarge)
                Text(
                    if (isListening) "I'm listening for your commands." else "Turn on to listen hands-free.",
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
            Switch(checked = isListening, onCheckedChange = onListeningChange)
        }
    }
}

@Composable
private fun CommandCard(row: CommandRow) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(row.command.label, style = MaterialTheme.typography.titleLarge)
            Text(
                "${row.templateCount} recording${if (row.templateCount == 1) "" else "s"} • does: ${row.command.action.value}",
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}
