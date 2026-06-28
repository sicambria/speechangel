package com.speechangel.app.service

import android.app.role.RoleManager
import android.content.Context
import android.content.Intent
import android.os.Build

/**
 * Optional `ROLE_ASSISTANT` hardening (API 29+). Offered as an *unverified* reboot-survival aid — it is
 * NOT claimed to lift the microphone-FGS boot/while-in-use restrictions (those are separate platform
 * rules). Guarded for minSdk 26.
 */
object AssistantRole {

    fun isAvailable(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false
        val rm = context.getSystemService(RoleManager::class.java) ?: return false
        return rm.isRoleAvailable(RoleManager.ROLE_ASSISTANT)
    }

    fun requestIntent(context: Context): Intent? {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return null
        val rm = context.getSystemService(RoleManager::class.java) ?: return null
        if (!rm.isRoleAvailable(RoleManager.ROLE_ASSISTANT)) return null
        return rm.createRequestRoleIntent(RoleManager.ROLE_ASSISTANT)
    }
}
