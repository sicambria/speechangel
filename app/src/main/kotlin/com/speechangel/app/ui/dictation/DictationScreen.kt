package com.speechangel.app.ui.dictation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Mic
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle

/**
 * Minimal "dictate to a text field" surface (Phase 3, opt-in, dormant). Wired to the neutral
 * [DictationViewModel]/[com.speechangel.core.enrollment.DictationBackend] seam only — it never enters
 * the always-on command flow. With the shipping Noop backend, dictating reports "unavailable".
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DictationScreen(onBack: () -> Unit, viewModel: DictationViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dictation") },
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
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Dictate a note into the text field. This is optional and separate from your voice commands — it never triggers actions.")

            OutlinedTextField(
                value = state.transcript,
                onValueChange = {},
                readOnly = true,
                label = { Text("Transcript") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3,
            )

            Button(onClick = { viewModel.dictate() }, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Filled.Mic, contentDescription = null)
                Text("  Dictate")
            }

            state.message?.let { Text(it) }
        }
    }
}
