package com.speechangel.app.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.speechangel.app.R
import com.speechangel.app.action.CommandActionBus
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.core.model.RecognitionResult
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import javax.inject.Inject

/**
 * The always-on, hands-free listening loop, hosted in a `microphone` foreground service so it can
 * keep capturing in the background once started while visible (see research §T2.1).
 *
 * MVP: it records short windows and runs the rejecting template matcher on each — the OOV reject
 * path is what stops non-command speech firing actions. A low-power Stage-1 wake word that gates
 * this heavier Stage-2 recogniser is the next roadmap item (battery; research §T2.4).
 */
@AndroidEntryPoint
class ListeningService : LifecycleService() {

    @Inject lateinit var recognizer: Recognizer

    @Inject lateinit var recorder: com.speechangel.data.audio.AudioRecorder

    @Inject lateinit var templateRepository: TemplateRepository

    @Inject lateinit var commandRepository: CommandRepository

    @Inject lateinit var actionBus: CommandActionBus

    private var loop: Job? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        startAsForeground()
        if (loop == null) loop = lifecycleScope.launch { listenLoop() }
        return START_STICKY
    }

    private suspend fun listenLoop() {
        while (lifecycleScope.coroutineContext.isActive) {
            val templates = templateRepository.allTemplates()
            if (templates.isEmpty()) {
                delay(IDLE_DELAY_MS)
                continue
            }
            val audio = recorder.record(WINDOW_MS)
            val result = withContext(Dispatchers.Default) { recognizer.recognize(audio, templates) }
            if (result is RecognitionResult.Match) {
                commandRepository.getCommand(result.commandId)?.let { actionBus.publish(it.action) }
                delay(POST_MATCH_DELAY_MS)
            }
        }
    }

    private fun startAsForeground() {
        val manager = getSystemService(NotificationManager::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, getString(R.string.listening_channel_name), NotificationManager.IMPORTANCE_LOW)
            manager.createNotificationChannel(channel)
        }
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.listening_notification_title))
            .setContentText(getString(R.string.listening_notification_text))
            .setSmallIcon(R.drawable.ic_launcher)
            .setOngoing(true)
            .build()
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
        } else {
            0
        }
        ServiceCompat.startForeground(this, NOTIF_ID, notification, type)
    }

    override fun onDestroy() {
        loop?.cancel()
        loop = null
        super.onDestroy()
    }

    private companion object {
        const val CHANNEL_ID = "listening"
        const val NOTIF_ID = 1001
        const val WINDOW_MS = 1_500
        const val IDLE_DELAY_MS = 800L
        const val POST_MATCH_DELAY_MS = 600L
    }
}
