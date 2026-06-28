package com.speechangel.app.ui.tryit

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TryScreen(onBack: () -> Unit, viewModel: TryViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Try it") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(24.dp, Alignment.CenterVertically),
        ) {
            Text(
                "Tap the microphone, then say one of your commands.",
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
            )

            Button(
                onClick = viewModel::listen,
                enabled = !state.isListening,
                modifier = Modifier.size(160.dp),
            ) {
                if (state.isListening) {
                    CircularProgressIndicator(modifier = Modifier.size(56.dp))
                } else {
                    Icon(Icons.Filled.Mic, contentDescription = "Listen", modifier = Modifier.size(72.dp))
                }
            }

            ResultText(state.result)

            if (state.canAdapt) {
                OutlinedButton(onClick = viewModel::rememberThis) { Text("Remember this") }
            }
            if (state.adapted) {
                Text("Saved!", style = MaterialTheme.typography.bodySmall)
            }

            Button(onClick = onBack, modifier = Modifier.fillMaxWidth().height(56.dp)) {
                Text("Back", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun ResultText(result: TryResult?) {
    val text = when (result) {
        is TryResult.Heard -> "I heard: “${result.label}” (${(result.confidence * 100).roundToInt()}% sure)"
        TryResult.NotSure -> "Hmm, I didn't catch that. Try again."
        TryResult.NoCommands -> "Teach me a command first."
        null -> ""
    }
    if (text.isNotEmpty()) {
        Text(text, style = MaterialTheme.typography.headlineMedium, textAlign = TextAlign.Center)
    }
}
