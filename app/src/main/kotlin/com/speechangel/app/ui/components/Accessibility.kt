package com.speechangel.app.ui.components

import android.os.Build
import android.view.HapticFeedbackConstants
import android.view.View
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics

/**
 * Marks a composable as a heading so TalkBack users can jump between sections with heading navigation.
 * Cheap to add, and the single biggest lever for screen-reader wayfinding on a form-heavy screen.
 */
fun Modifier.heading(): Modifier = semantics { heading() }

/**
 * Marks a region whose text changes should be *announced* by TalkBack the moment they happen (without
 * the user having to move focus onto it). Used for the record/recognition feedback so a blind user hears
 * "Got it!" or "too short — try again" immediately. Assertive by default because these are the primary
 * outcome of the user's action.
 */
fun Modifier.announce(assertive: Boolean = true): Modifier =
    semantics { liveRegion = if (assertive) LiveRegionMode.Assertive else LiveRegionMode.Polite }

/**
 * A short "success" haptic. Uses the dedicated [HapticFeedbackConstants.CONFIRM] pattern on API 30+ and
 * falls back to a plain key tick below it (minSdk is 26). Non-visual confirmation matters for users who
 * cannot easily read the on-screen 👍 — e.g. low vision, or eyes on the device they're controlling.
 */
fun View.confirmHaptic() {
    val constant = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        HapticFeedbackConstants.CONFIRM
    } else {
        HapticFeedbackConstants.VIRTUAL_KEY
    }
    performHapticFeedback(constant)
}

/** A short "rejected" haptic (distinct from [confirmHaptic]); API-guarded like it. */
fun View.rejectHaptic() {
    val constant = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        HapticFeedbackConstants.REJECT
    } else {
        HapticFeedbackConstants.LONG_PRESS
    }
    performHapticFeedback(constant)
}
