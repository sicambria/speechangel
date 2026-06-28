package com.speechangel.app.ui.policy

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable

/**
 * Prominent in-app microphone disclosure, shown BEFORE the mic permission / foreground service starts
 * (Play prominent-disclosure requirement). The acknowledgement is persisted by the caller (via
 * `ListeningPreferences.setMicDisclosed`) so it is shown once.
 */
@Composable
fun MicDisclosureDialog(onAcknowledge: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Microphone use") },
        text = {
            Text(
                "SpeechAngel listens with your microphone to recognise the voice commands you record. " +
                    "Audio is matched on your device only — it is never uploaded, and SpeechAngel performs " +
                    "only the fixed action you assign to each command.",
            )
        },
        confirmButton = { TextButton(onClick = onAcknowledge) { Text("I understand") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Not now") } },
    )
}
