package com.speechangel.app.ui.teach

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.speechangel.app.action.DeviceAction
import com.speechangel.app.ui.components.announce
import com.speechangel.app.ui.components.confirmHaptic
import com.speechangel.app.ui.components.heading
import com.speechangel.app.ui.components.rejectHaptic
import com.speechangel.core.enrollment.QualityIssue

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun TeachScreen(onDone: () -> Unit, viewModel: TeachViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val view = LocalView.current

    // Non-visual confirmation the recording landed (or didn't), for users not watching the 👍/👎.
    LaunchedEffect(state.justSucceeded, state.lastIssue) {
        when {
            state.justSucceeded -> view.confirmHaptic()
            state.lastIssue != null -> view.rejectHaptic()
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Teach a command") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            StepHeading("1. Name it")
            OutlinedTextField(
                value = state.label,
                onValueChange = viewModel::onLabelChange,
                label = { Text("What is this command? (e.g. “home”)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            StepHeading("2. What should it do?")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                DeviceAction.entries.forEach { action ->
                    FilterChip(
                        selected = state.action == action,
                        onClick = { viewModel.onActionChange(action) },
                        label = { Text(action.label) },
                        // Guarantee the 48dp minimum touch target regardless of font scale.
                        modifier = Modifier.heightIn(min = 48.dp),
                    )
                }
            }

            StepHeading("3. Say it a few times")
            Text(
                "Recorded ${state.recordedCount} time${if (state.recordedCount == 1) "" else "s"}. " +
                    "Record it 2–3 times for best results.",
                style = MaterialTheme.typography.bodyLarge,
            )
            Feedback(state.lastIssue, state.justSucceeded)
            if (state.closeToLabels.isNotEmpty()) {
                Text(
                    "Heads up: this sounds close to ${state.closeToLabels.joinToString(", ") { "“$it”" }}. " +
                        "A more distinct word may work better — but you can keep it.",
                    modifier = Modifier.fillMaxWidth().announce(assertive = false),
                    style = MaterialTheme.typography.bodyLarge,
                )
            }

            RecordButton(
                isRecording = state.isRecording,
                enabled = state.canRecord,
                onClick = viewModel::recordExample,
            )

            TextButton(
                onClick = onDone,
                enabled = state.canFinish,
                modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
            ) {
                Text("Done", style = MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun StepHeading(text: String) {
    Text(text, style = MaterialTheme.typography.titleLarge, modifier = Modifier.heading())
}

@Composable
private fun RecordButton(isRecording: Boolean, enabled: Boolean, onClick: () -> Unit) {
    // While recording, the mic icon pulses — a live "I'm hearing you" cue, not a neutral spinner.
    val transition = rememberInfiniteTransition(label = "record-pulse")
    val pulseAlpha by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.35f,
        animationSpec = infiniteRepeatable(tween(700), RepeatMode.Reverse),
        label = "record-pulse-alpha",
    )
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = Modifier.fillMaxWidth().heightIn(min = 72.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Filled.Mic,
                contentDescription = null,
                modifier = Modifier
                    .size(28.dp)
                    .then(if (isRecording) Modifier.alpha(pulseAlpha) else Modifier),
            )
            Text(
                if (isRecording) "Recording… speak now" else "Record",
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun Feedback(issue: QualityIssue?, success: Boolean) {
    val message = when {
        success -> "👍 Got it!"
        issue == QualityIssue.SILENT -> "👎 I didn't hear anything — try again, a little louder."
        issue == QualityIssue.TOO_SHORT -> "👎 That was too short — hold and say the whole word."
        issue == QualityIssue.TOO_FEW_FRAMES -> "👎 A bit too quick — say it again clearly."
        else -> null
    }
    if (message != null) {
        Text(
            message,
            modifier = Modifier.fillMaxWidth().announce(),
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodyLarge,
        )
    }
}
