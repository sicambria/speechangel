package com.speechangel.app.ui.tryit

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.speechangel.app.ui.components.PulsingMicButton
import com.speechangel.app.ui.components.announce
import com.speechangel.app.ui.components.confirmHaptic
import com.speechangel.app.ui.components.rejectHaptic
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TryScreen(onBack: () -> Unit, viewModel: TryViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val view = LocalView.current

    // Non-visual confirmation of the outcome (matched / not sure) for users who can't easily read it.
    LaunchedEffect(state.result) {
        when (state.result) {
            is TryResult.Heard -> view.confirmHaptic()
            TryResult.NotSure -> view.rejectHaptic()
            else -> Unit
        }
    }

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

            PulsingMicButton(
                active = state.isListening,
                onClick = viewModel::listen,
                contentDescription = "Listen for a command",
                idleStateDescription = "Ready. Tap to listen.",
                activeStateDescription = "Listening now",
            )

            ResultText(state.result)

            if (state.canAdapt) {
                OutlinedButton(onClick = viewModel::rememberThis) { Text("Remember this") }
            }
            if (state.adapted) {
                Text(
                    "Saved!",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.announce(),
                )
            }

            // Demoted from a filled button so it no longer competes with the microphone for attention.
            TextButton(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
            ) {
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
        Text(
            text,
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().announce(),
        )
    }
}
