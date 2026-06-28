package com.speechangel.app.ui.policy

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/** Component + license. Source of truth for now is this hand-maintained list (see policy plan). */
private data class License(val component: String, val license: String)

private val THIRD_PARTY = listOf(
    License("AndroidX (Core, Lifecycle, Compose, Navigation, Room, DataStore)", "Apache-2.0"),
    License("Kotlin & kotlinx.coroutines", "Apache-2.0"),
    License("Dagger Hilt", "Apache-2.0"),
    // Planned on-device models (not yet bundled) — permissive only:
    License("Silero VAD (planned)", "MIT"),
    License("Vosk / sherpa-onnx (optional Path-A, planned)", "Apache-2.0"),
    License("whisper.cpp (optional, planned)", "MIT"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LicensesScreen(onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Open-source licenses") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
                },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(THIRD_PARTY) { entry ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(entry.component, style = MaterialTheme.typography.titleMedium)
                        Text(entry.license, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}
