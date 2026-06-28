package com.speechangel.app.service

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import com.speechangel.app.action.CommandActionBus
import com.speechangel.app.action.DeviceAction
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Executes recognised commands as deterministic device actions.
 *
 * This is intentionally a *rule-based accessibility tool* (`isAccessibilityTool=true`): it maps each
 * recognised [DeviceAction] to a single `performGlobalAction`. It never interprets free-form speech
 * or decides actions autonomously — that distinction is what keeps it inside Google Play's 2026
 * accessibility policy (research §T2.7).
 */
@AndroidEntryPoint
class SpeechAngelAccessibilityService : AccessibilityService() {

    @Inject lateinit var actionBus: CommandActionBus

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    override fun onServiceConnected() {
        super.onServiceConnected()
        scope.launch {
            actionBus.actions.collect { actionId ->
                DeviceAction.fromId(actionId.value)?.let { performGlobalAction(it.globalAction) }
            }
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}
