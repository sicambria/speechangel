package com.speechangel.app.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.speechangel.app.MainActivity
import com.speechangel.app.R
import com.speechangel.data.prefs.ListeningPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * On boot, if listening was enabled, posts a **tap-to-resume** notification — it does NOT start the
 * microphone foreground service directly, because a `microphone` FGS cannot be started from a
 * BOOT_COMPLETED (background) context on Android 14+ (`ForegroundServiceStartNotAllowedException`). The
 * user's tap opens the app, from which the FGS starts legally. Reads the flag off the main thread via
 * `goAsync()`.
 */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val pending = goAsync()
        val appContext = context.applicationContext
        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (ListeningPreferences(appContext).isListeningEnabledNow()) {
                    postResumeNotification(appContext)
                }
            } finally {
                pending.finish()
            }
        }
    }

    private fun postResumeNotification(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    CHANNEL_ID,
                    context.getString(R.string.resume_channel_name),
                    NotificationManager.IMPORTANCE_DEFAULT,
                ),
            )
        }
        val tap = PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle(context.getString(R.string.resume_title))
            .setContentText(context.getString(R.string.resume_text))
            .setSmallIcon(R.drawable.ic_launcher)
            .setContentIntent(tap)
            .setAutoCancel(true)
            .build()
        manager.notify(NOTIF_ID, notification)
    }

    private companion object {
        const val CHANNEL_ID = "resume"
        const val NOTIF_ID = 2001
    }
}
