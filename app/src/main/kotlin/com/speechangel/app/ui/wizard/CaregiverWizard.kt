package com.speechangel.app.ui.wizard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.speechangel.app.ui.components.heading

/**
 * Guided caregiver setup: Welcome → Teach a command → Try it → Turn on always-on → Done. It sequences
 * the existing screens via callbacks (rather than embedding their Scaffolds), with a progress indicator
 * and a persisted "setup complete" flag set by the caller on finish.
 */
private data class Step(val title: String, val body: String, val actionLabel: String?)

private val STEPS = listOf(
    Step("Welcome", "Let's set up SpeechAngel together. It takes about a minute.", null),
    Step("Teach a command", "Record a short word a few times for one action (for example “home”).", "Teach a command"),
    Step("Try it", "Say the word and check SpeechAngel recognises it.", "Try it"),
    Step("Turn on always-on", "Turn on hands-free listening and keep the app running in the background.", "Open always-on"),
    Step("All set", "You're ready. You can re-run this anytime from the menu.", null),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaregiverWizard(onTeach: () -> Unit, onTry: () -> Unit, onAlwaysOn: () -> Unit, onFinish: () -> Unit) {
    var index by rememberSaveable { mutableIntStateOf(0) }
    val step = STEPS[index]
    val isLast = index == STEPS.lastIndex

    Scaffold(topBar = { TopAppBar(title = { Text("Setup (${index + 1}/${STEPS.size})") }) }) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            LinearProgressIndicator(progress = { (index + 1f) / STEPS.size }, modifier = Modifier.fillMaxWidth())
            Text(step.title, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.heading())
            Text(step.body, style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Start)

            step.actionLabel?.let { label ->
                Button(
                    onClick = {
                        if (index == 1) {
                            onTeach()
                        } else if (index == 2) {
                            onTry()
                        } else {
                            onAlwaysOn()
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(label) }
            }

            Column(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { if (isLast) onFinish() else index++ },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(if (isLast) "Finish" else "Next") }
                if (index > 0) {
                    OutlinedButton(onClick = { index-- }, modifier = Modifier.fillMaxWidth()) { Text("Back") }
                }
            }
        }
    }
}
