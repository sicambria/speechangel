package com.speechangel.app.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * A large circular microphone button that emits expanding "sound" rings while [active], giving a clear
 * *visual* "I'm hearing you" signal — the affordance a bare spinner lacks, and the one users unsure
 * whether their (dysarthric) speech registered most need. Tapping fires a haptic. The button carries its
 * own TalkBack [contentDescription] + a live [stateDescription] so a screen-reader user gets the same
 * "listening now" state the rings convey visually.
 *
 * While [active] the button is non-interactive (a capture is already in flight), matching the callers'
 * existing "disabled while recording" behaviour.
 */
@Composable
fun PulsingMicButton(
    active: Boolean,
    onClick: () -> Unit,
    contentDescription: String,
    idleStateDescription: String,
    activeStateDescription: String,
    modifier: Modifier = Modifier,
    size: Dp = 168.dp,
) {
    val haptics = LocalHapticFeedback.current
    val ringColor = MaterialTheme.colorScheme.primary

    val transition = rememberInfiniteTransition(label = "mic-pulse")
    val pulse by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1600, easing = LinearEasing), RepeatMode.Restart),
        label = "mic-pulse-fraction",
    )

    Box(contentAlignment = Alignment.Center, modifier = modifier.size(size)) {
        if (active) {
            Canvas(Modifier.size(size)) {
                val maxRadius = this.size.minDimension / 2f
                // Two rings, half a cycle apart, expanding and fading outward.
                listOf(0f, 0.5f).forEach { offset ->
                    val f = (pulse + offset) % 1f
                    drawCircle(
                        color = ringColor.copy(alpha = (1f - f) * 0.35f),
                        radius = maxRadius * (0.62f + f * 0.38f),
                    )
                }
            }
        }
        Surface(
            onClick = {
                haptics.performHapticFeedback(HapticFeedbackType.LongPress)
                onClick()
            },
            enabled = !active,
            shape = CircleShape,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier
                .size(size * 0.74f)
                .semantics {
                    this.contentDescription = contentDescription
                    stateDescription = if (active) activeStateDescription else idleStateDescription
                },
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(
                    imageVector = Icons.Filled.Mic,
                    contentDescription = null, // described by the Surface above
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(size * 0.30f),
                )
            }
        }
    }
}
