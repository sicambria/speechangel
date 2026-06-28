package com.speechangel.app.action

import com.speechangel.core.model.ActionId
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * In-process bus connecting the recognizer (ListeningService) to the executor
 * (SpeechAngelAccessibilityService). The two Android services cannot call each other directly,
 * so recognised actions are published here and the accessibility service consumes them.
 */
@Singleton
class CommandActionBus @Inject constructor() {
    private val _actions = MutableSharedFlow<ActionId>(extraBufferCapacity = 16)
    val actions: SharedFlow<ActionId> = _actions.asSharedFlow()

    fun publish(action: ActionId) {
        _actions.tryEmit(action)
    }
}
