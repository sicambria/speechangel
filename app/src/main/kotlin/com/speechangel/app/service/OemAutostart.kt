package com.speechangel.app.service

/**
 * Per-OEM autostart guidance (DontKillMyApp). [resolve] is a pure function over the manufacturer string
 * so it is unit-testable without a device; the settings deep-link is returned as package/class strings
 * and the Intent is built (and its failure caught) at the UI layer.
 */
data class OemGuidance(val manufacturer: String, val steps: List<String>, val autostartPackage: String?, val autostartClass: String?) {
    val hasDeepLink: Boolean get() = autostartPackage != null && autostartClass != null
}

object OemAutostart {

    private val GENERIC = listOf(
        "Open Settings → Apps → SpeechAngel.",
        "Allow background activity / autostart and disable battery restrictions.",
    )

    fun resolve(manufacturer: String): OemGuidance {
        val m = manufacturer.lowercase()
        return when {
            m.contains("xiaomi") || m.contains("redmi") || m.contains("poco") -> OemGuidance(
                manufacturer,
                listOf("Open Security → Permissions → Autostart and enable SpeechAngel.", "Set battery saver to “No restrictions”."),
                "com.miui.securitycenter",
                "com.miui.permcenter.autostart.AutoStartManagementActivity",
            )
            m.contains("huawei") || m.contains("honor") -> OemGuidance(
                manufacturer,
                listOf("Open Phone Manager → Startup management and allow SpeechAngel.", "Disable “Manage automatically” for SpeechAngel."),
                "com.huawei.systemmanager",
                "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity",
            )
            m.contains("oppo") || m.contains("realme") -> OemGuidance(
                manufacturer,
                listOf("Open Settings → Battery → App energy saver and allow background for SpeechAngel.", "Enable Auto-startup."),
                "com.coloros.safecenter",
                "com.coloros.safecenter.startupapp.StartupAppListActivity",
            )
            m.contains("vivo") || m.contains("iqoo") -> OemGuidance(
                manufacturer,
                listOf("Open i Manager → App manager → Autostart and enable SpeechAngel.", "Allow high background power use."),
                "com.vivo.permissionmanager",
                "com.vivo.permissionmanager.activity.BgStartUpManagerActivity",
            )
            m.contains("samsung") -> OemGuidance(
                manufacturer,
                listOf(
                    "Open Settings → Battery → Background usage limits.",
                    "Remove SpeechAngel from “Sleeping apps” and disable “Put to sleep”.",
                ),
                null,
                null,
            )
            else -> OemGuidance(manufacturer, GENERIC, null, null)
        }
    }
}
