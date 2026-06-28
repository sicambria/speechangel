package com.speechangel.app.action

import android.accessibilityservice.AccessibilityService

/**
 * The fixed, human-defined set of device actions a voice command may trigger.
 *
 * This determinism is deliberate and load-bearing: SpeechAngel is an accessibility *tool*, not an
 * autonomous agent, which is what keeps it inside Google Play's 2026 accessibility policy
 * (see `research/02_technological_findings.md` §T2.7). Each command maps to exactly one of these.
 */
enum class DeviceAction(
    val id: String,
    val label: String,
    val globalAction: Int,
) {
    HOME("HOME", "Go to home screen", AccessibilityService.GLOBAL_ACTION_HOME),
    BACK("BACK", "Go back", AccessibilityService.GLOBAL_ACTION_BACK),
    RECENTS("RECENTS", "Show recent apps", AccessibilityService.GLOBAL_ACTION_RECENTS),
    NOTIFICATIONS("NOTIFICATIONS", "Open notifications", AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS),
    QUICK_SETTINGS("QUICK_SETTINGS", "Open quick settings", AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS),
    POWER_DIALOG("POWER_DIALOG", "Show power menu", AccessibilityService.GLOBAL_ACTION_POWER_DIALOG),
    LOCK_SCREEN("LOCK_SCREEN", "Lock the screen", AccessibilityService.GLOBAL_ACTION_LOCK_SCREEN),
    SCROLL_FORWARD("SCROLL_FORWARD", "Scroll down", AccessibilityService.GLOBAL_ACTION_DPAD_DOWN),
    SCROLL_BACK("SCROLL_BACK", "Scroll up", AccessibilityService.GLOBAL_ACTION_DPAD_UP),
    ;

    companion object {
        fun fromId(id: String): DeviceAction? = entries.firstOrNull { it.id == id }
        val default: DeviceAction = HOME
    }
}
