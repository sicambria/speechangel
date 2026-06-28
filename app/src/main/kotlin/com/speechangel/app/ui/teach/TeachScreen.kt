package com.speechangel.app.ui.teach

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.speechangel.app.action.DeviceAction
import com.speechangel.core.enrollment.QualityIssue

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun TeachScreen(
    onDone: () -> Unit,
    viewModel: TeachViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Teach a command") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            Text("1. Name it", style = androidx.compose.material3.MaterialTheme.typography.titleLarge)
            OutlinedTextField(
                value = state.label,
                onValueChange = viewModel::onLabelChange,
                label = { Text("What is this command? (e.g. “home”)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )

            Text("2. What should it do?", style = androidx.compose.material3.MaterialTheme.typography.titleLarge)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                DeviceAction.entries.forEach { action ->
                    FilterChip(
                        selected = state.action == action,
                        onClick = { viewModel.onActionChange(action) },
                        label = { Text(action.label) },
                    )
                }
            }

            Text("3. Say it a few times", style = androidx.compose.material3.MaterialTheme.typography.titleLarge)
            Text(
                "Recorded ${state.recordedCount} time${if (state.recordedCount == 1) "" else "s"}. " +
                    "Record it 2–3 times for best results.",
                style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
            )
            feedback(state.lastIssue, state.justSucceeded)

            Button(
                onClick = viewModel::recordExample,
                enabled = state.canRecord,
                modifier = Modifier.fillMaxWidth().height(72.dp),
            ) {
                if (state.isRecording) {
                    CircularProgressIndicator(modifier = Modifier.height(28.dp))
                } else {
                    Text("🎙  Record", style = androidx.compose.material3.MaterialTheme.typography.labelLarge)
                }
            }

            TextButton(
                onClick = onDone,
                enabled = state.canFinish,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Done", style = androidx.compose.material3.MaterialTheme.typography.labelLarge)
            }
        }
    }
}

@Composable
private fun feedback(issue: QualityIssue?, success: Boolean) {
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
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
            style = androidx.compose.material3.MaterialTheme.typography.bodyLarge,
        )
    }
}
