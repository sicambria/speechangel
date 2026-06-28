package com.speechangel.app.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.speechangel.app.ui.alwayson.AlwaysOnScreen
import com.speechangel.app.ui.home.HomeScreen
import com.speechangel.app.ui.policy.LicensesScreen
import com.speechangel.app.ui.teach.TeachScreen
import com.speechangel.app.ui.tryit.TryScreen
import com.speechangel.app.ui.wizard.CaregiverWizard

private object Routes {
    const val HOME = "home"
    const val TEACH = "teach"
    const val TRY = "try"
    const val ALWAYS_ON = "always_on"
    const val WIZARD = "wizard"
    const val LICENSES = "licenses"
}

@Composable
fun SpeechAngelNavHost(isListening: Boolean, onListeningChange: (Boolean) -> Unit) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = Routes.HOME) {
        composable(Routes.HOME) {
            HomeScreen(
                isListening = isListening,
                onListeningChange = onListeningChange,
                onAddCommand = { navController.navigate(Routes.TEACH) },
                onTryIt = { navController.navigate(Routes.TRY) },
                onOpenAlwaysOn = { navController.navigate(Routes.ALWAYS_ON) },
                onStartSetup = { navController.navigate(Routes.WIZARD) },
            )
        }
        composable(Routes.TEACH) {
            TeachScreen(onDone = { navController.popBackStack() })
        }
        composable(Routes.TRY) {
            TryScreen(onBack = { navController.popBackStack() })
        }
        composable(Routes.ALWAYS_ON) {
            AlwaysOnScreen(
                isListening = isListening,
                onListeningChange = onListeningChange,
                onRecordWakeWord = { navController.navigate(Routes.TEACH) },
                onBack = { navController.popBackStack() },
            )
        }
        composable(Routes.WIZARD) {
            CaregiverWizard(
                onTeach = { navController.navigate(Routes.TEACH) },
                onTry = { navController.navigate(Routes.TRY) },
                onAlwaysOn = { navController.navigate(Routes.ALWAYS_ON) },
                onFinish = { navController.popBackStack(Routes.HOME, inclusive = false) },
            )
        }
        composable(Routes.LICENSES) {
            LicensesScreen(onBack = { navController.popBackStack() })
        }
    }
}
