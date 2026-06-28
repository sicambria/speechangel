package com.speechangel.app.service

import android.content.Context
import android.content.Intent
import android.os.PowerManager
import android.provider.Settings

/**
 * Battery-optimization exemption helper. Uses the Play-permitted settings-list intent
 * (`ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`) by default; the direct allow-prompt
 * (`ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`) is restricted by Play to approved use-case
 * categories and is intentionally not used here. Must be shown only after a prominent in-app disclosure.
 */
object BatteryOptimization {

    fun isExempt(context: Context): Boolean {
        val pm = context.getSystemService(PowerManager::class.java) ?: return false
        return pm.isIgnoringBatteryOptimizations(context.packageName)
    }

    fun settingsIntent(): Intent = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
}
