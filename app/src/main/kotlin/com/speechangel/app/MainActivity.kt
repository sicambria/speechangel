package com.speechangel.app

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.speechangel.app.service.ListeningService
import com.speechangel.app.ui.SpeechAngelNavHost
import com.speechangel.app.ui.theme.SpeechAngelTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private var listening by mutableStateOf(false)

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { /* result handled lazily when the user toggles listening */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestRuntimePermissions()
        setContent {
            SpeechAngelTheme {
                SpeechAngelNavHost(
                    isListening = listening,
                    onListeningChange = ::applyListening,
                )
            }
        }
    }

    private fun requestRuntimePermissions() {
        val needed = buildList {
            add(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }.toTypedArray()
        permissionLauncher.launch(needed)
    }

    private fun applyListening(enabled: Boolean) {
        val intent = Intent(this, ListeningService::class.java)
        if (enabled) {
            startForegroundService(intent)
        } else {
            stopService(intent)
        }
        listening = enabled
    }
}
