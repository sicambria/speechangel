package com.speechangel.data.prefs

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.speechangel.core.model.CommandId
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.speechAngelDataStore: DataStore<Preferences> by preferencesDataStore(name = "speechangel_settings")

/**
 * Small DataStore-backed settings holder. Owns the persisted flags the always-on flows need to survive
 * process death / reboot: whether listening was enabled, whether the mic disclosure was acknowledged,
 * and whether first-run setup completed. A single process-wide DataStore (the [speechAngelDataStore]
 * delegate) backs both the Hilt-injected instance and any direct construction (e.g. the boot receiver),
 * so there is never a duplicate-instance-per-file error.
 */
@Singleton
class ListeningPreferences @Inject constructor(@ApplicationContext private val context: Context) {

    private val store get() = context.speechAngelDataStore

    val listeningEnabled: Flow<Boolean> = store.data.map { it[LISTENING_ENABLED] ?: false }
    val micDisclosed: Flow<Boolean> = store.data.map { it[MIC_DISCLOSED] ?: false }
    val setupComplete: Flow<Boolean> = store.data.map { it[SETUP_COMPLETE] ?: false }

    /** Per-command acceptance thresholds from the eval calibrator; empty until calibration runs. */
    val commandThresholds: Flow<Map<CommandId, Float>> =
        store.data.map { CommandThresholdCodec.decode(it[COMMAND_THRESHOLDS] ?: "") }

    suspend fun setListeningEnabled(value: Boolean) = put(LISTENING_ENABLED, value)
    suspend fun setMicDisclosed(value: Boolean) = put(MIC_DISCLOSED, value)
    suspend fun setSetupComplete(value: Boolean) = put(SETUP_COMPLETE, value)

    /** Persist the whole calibrated threshold map (wholesale replace). */
    suspend fun setCommandThresholds(thresholds: Map<CommandId, Float>) {
        store.edit { it[COMMAND_THRESHOLDS] = CommandThresholdCodec.encode(thresholds) }
    }

    /** One-shot read for non-reactive callers (e.g. the boot receiver inside `goAsync`). */
    suspend fun isListeningEnabledNow(): Boolean = listeningEnabled.first()

    private suspend fun put(key: Preferences.Key<Boolean>, value: Boolean) {
        store.edit { it[key] = value }
    }

    private companion object {
        val LISTENING_ENABLED = booleanPreferencesKey("listening_enabled")
        val MIC_DISCLOSED = booleanPreferencesKey("mic_disclosed")
        val SETUP_COMPLETE = booleanPreferencesKey("setup_complete")
        val COMMAND_THRESHOLDS = stringPreferencesKey("command_thresholds")
    }
}
