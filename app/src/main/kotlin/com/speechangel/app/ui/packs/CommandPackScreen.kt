package com.speechangel.app.ui.packs

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.speechangel.app.ui.components.announce

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CommandPackScreen(onBack: () -> Unit, viewModel: CommandPackViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var importText by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Command packs") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Share a starter set of commands. Packs carry no recordings — each command is re-taught in your own voice after import.")

            Button(onClick = { viewModel.export("My commands", "me") }, modifier = Modifier.fillMaxWidth()) {
                Text("Export my commands")
            }
            state.exportedJson?.let { json ->
                Text("Copy this pack to share it:")
                OutlinedTextField(
                    value = json,
                    onValueChange = {},
                    readOnly = true,
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3,
                )
            }

            OutlinedTextField(
                value = importText,
                onValueChange = { importText = it },
                label = { Text("Paste a command pack to import") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3,
            )
            Button(
                onClick = { viewModel.import(importText) },
                enabled = importText.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Import pack")
            }

            state.error?.let { Text("Couldn't import: $it", modifier = Modifier.announce()) }
            if (state.lastImportRan && state.error == null) {
                Text(
                    "Imported ${state.importedCount} command(s). Teach each one in your own voice.",
                    modifier = Modifier.announce(),
                )
                if (state.rejected.isNotEmpty()) {
                    Text("Skipped ${state.rejected.size} (unknown action or blank name):")
                    for (r in state.rejected) {
                        Text(
                            "• ${r.command.label.ifBlank {
                                "(no name)"
                            }} → ${r.command.actionId}",
                            overflow = TextOverflow.Ellipsis,
                            maxLines = 1,
                        )
                    }
                }
            }
        }
    }
}
