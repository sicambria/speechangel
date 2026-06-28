package com.speechangel.app.ui.alwayson

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
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
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp

/**
 * The "Always-on" screen. Binds to the EXISTING hoisted listening state (no second source of truth) and
 * surfaces the survival hooks (battery exemption, optional assistant role, per-OEM autostart) and the
 * "record wake word" entry. Settings deep-links use [LocalContext] and fail soft.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlwaysOnScreen(isListening: Boolean, onListeningChange: (Boolean) -> Unit, onRecordWakeWord: () -> Unit, onBack: () -> Unit) {
    val context = LocalContext.current
    val oem = remember { com.speechangel.app.service.OemAutostart.resolve(Build.MANUFACTURER) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Always-on") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Listen hands-free", style = MaterialTheme.typography.titleLarge)
                    Switch(checked = isListening, onCheckedChange = onListeningChange)
                }
            }

            bigButton("Record a wake word", onRecordWakeWord)

            bigButton("Keep running in the background") {
                runCatching { context.startActivity(com.speechangel.app.service.BatteryOptimization.settingsIntent()) }
            }

            if (com.speechangel.app.service.AssistantRole.isAvailable(context)) {
                bigButton("Set as assistant (optional)") {
                    com.speechangel.app.service.AssistantRole.requestIntent(context)?.let { runCatching { context.startActivity(it) } }
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Stop ${oem.manufacturer} from closing the app", style = MaterialTheme.typography.titleLarge)
                    oem.steps.forEach { Text("• $it", style = MaterialTheme.typography.bodyLarge) }
                    bigButton("Open settings") { openOemSettings(context, oem) }
                }
            }
        }
    }
}

@Composable
private fun bigButton(label: String, onClick: () -> Unit) {
    Button(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

/** Try the OEM autostart deep-link; fall back to this app's details settings. Both fail soft. */
private fun openOemSettings(context: android.content.Context, oem: com.speechangel.app.service.OemGuidance) {
    if (oem.hasDeepLink) {
        val ok = runCatching {
            context.startActivity(Intent().setClassName(oem.autostartPackage!!, oem.autostartClass!!))
        }.isSuccess
        if (ok) return
    }
    runCatching {
        val uri = Uri.parse("package:${context.packageName}")
        context.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, uri))
    }
}
