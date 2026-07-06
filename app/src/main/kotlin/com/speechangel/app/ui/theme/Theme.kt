package com.speechangel.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat

// Brand teal, darkened from #00696E to clear WCAG AAA for white text at normal-text sizes:
// white-on-#005457 = 8.73:1 (AAA ≥ 7:1). The old #00696E was 6.47:1 (AA only) — a real miss for
// button labels, which are our most common text-on-color surface.
private val Teal = Color(0xFF005457)
private val TealLight = Color(0xFF6FF6FE) // dark-theme primary; onPrimary-on-this = 10.25:1 (AAA)
private val Coral = Color(0xFFB3261E) // error; on white = 6.54:1 (AAA large / AA normal — error text is short + bold)

private val LightColors = lightColorScheme(
    primary = Teal,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF6FF6FE),
    onPrimaryContainer = Color(0xFF00201F),
    secondary = Color(0xFF35494A), // on background = 9.33:1 (AAA)
    onSecondary = Color.White,
    // Tonal surfaces (FilledTonalButton "Try it", selected FilterChip): keep them teal-family, not
    // Material's default purple. onSecondaryContainer on secondaryContainer = 13.25:1 (AAA).
    secondaryContainer = Color(0xFFCCE8E7),
    onSecondaryContainer = Color(0xFF002020),
    background = Color(0xFFFBFDFC),
    onBackground = Color(0xFF191C1C), // 16.79:1 (AAA)
    surface = Color(0xFFFBFDFC),
    onSurface = Color(0xFF191C1C),
    surfaceVariant = Color(0xFFDAE4E4),
    onSurfaceVariant = Color(0xFF2E3838), // on surfaceVariant = 9.32:1 (AAA)
    outline = Color(0xFF3F4948), // decorative borders; 9.10:1 on background
    error = Coral,
    onError = Color.White,
)

private val DarkColors = darkColorScheme(
    primary = TealLight,
    onPrimary = Color(0xFF00363A),
    primaryContainer = Color(0xFF004F52),
    onPrimaryContainer = Color(0xFF6FF6FE),
    secondary = Color(0xFFB1CBCD),
    onSecondary = Color(0xFF1C3437),
    secondaryContainer = Color(0xFF234A4B), // onSecondaryContainer on this = 7.42:1 (AAA)
    onSecondaryContainer = Color(0xFFC2E8E6),
    background = Color(0xFF191C1C),
    onBackground = Color(0xFFE0E3E2), // 13.28:1 (AAA)
    surface = Color(0xFF191C1C),
    onSurface = Color(0xFFE0E3E2),
    surfaceVariant = Color(0xFF3F4948),
    onSurfaceVariant = Color(0xFFDCE6E5), // on surfaceVariant = 7.30:1 (AAA)
    outline = Color(0xFF899392),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
)

/**
 * Large, high-contrast type scale — legible for a 10-year-old and for users with low vision. Every role
 * the app uses is defined here so nothing silently falls back to Material's small defaults (M3
 * `bodySmall` is 12sp, `bodyMedium` 14sp — far too small for this audience). Sizes are in `sp`, so they
 * still honour the user's system font-scale on top of this baseline.
 */
private val AccessibleTypography = Typography(
    displaySmall = TextStyle(fontWeight = FontWeight.Bold, fontSize = 32.sp, lineHeight = 40.sp),
    headlineMedium = TextStyle(fontWeight = FontWeight.Bold, fontSize = 28.sp, lineHeight = 36.sp),
    headlineSmall = TextStyle(fontWeight = FontWeight.Bold, fontSize = 24.sp, lineHeight = 32.sp),
    titleLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 24.sp, lineHeight = 30.sp),
    titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 26.sp),
    bodyLarge = TextStyle(fontSize = 20.sp, lineHeight = 28.sp),
    bodyMedium = TextStyle(fontSize = 18.sp, lineHeight = 26.sp),
    bodySmall = TextStyle(fontSize = 16.sp, lineHeight = 22.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 24.sp),
    labelMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 20.sp),
)

@Composable
fun SpeechAngelTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val colors = if (darkTheme) DarkColors else LightColors
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    MaterialTheme(
        colorScheme = colors,
        typography = AccessibleTypography,
        content = content,
    )
}
