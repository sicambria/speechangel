package com.speechangel.app.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.speechangel.app.ui.home.HomeScreen
import com.speechangel.app.ui.teach.TeachScreen
import com.speechangel.app.ui.tryit.TryScreen

private object Routes {
    const val HOME = "home"
    const val TEACH = "teach"
    const val TRY = "try"
}

@Composable
fun SpeechAngelNavHost(
    isListening: Boolean,
    onListeningChange: (Boolean) -> Unit,
) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = Routes.HOME) {
        composable(Routes.HOME) {
            HomeScreen(
                isListening = isListening,
                onListeningChange = onListeningChange,
                onAddCommand = { navController.navigate(Routes.TEACH) },
                onTryIt = { navController.navigate(Routes.TRY) },
            )
        }
        composable(Routes.TEACH) {
            TeachScreen(onDone = { navController.popBackStack() })
        }
        composable(Routes.TRY) {
            TryScreen(onBack = { navController.popBackStack() })
        }
    }
}
