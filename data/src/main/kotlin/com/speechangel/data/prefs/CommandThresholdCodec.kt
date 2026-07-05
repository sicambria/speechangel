package com.speechangel.data.prefs

import com.speechangel.core.model.CommandId
import org.json.JSONObject

/**
 * Encodes a per-command acceptance-threshold map (the output of the eval `ThresholdCalibrator`) to a
 * single JSON string for DataStore, and back. The calibrator recomputes the whole map at once, so a
 * wholesale replace is the right granularity — this is a runtime-tuning value, not schema-worthy state,
 * which is why it lives in preferences and not a Room column.
 */
object CommandThresholdCodec {

    fun encode(thresholds: Map<CommandId, Float>): String {
        val json = JSONObject()
        for ((id, value) in thresholds) json.put(id.value, value.toDouble())
        return json.toString()
    }

    fun decode(encoded: String): Map<CommandId, Float> {
        if (encoded.isBlank()) return emptyMap()
        return runCatching {
            val json = JSONObject(encoded)
            val out = LinkedHashMap<CommandId, Float>()
            for (key in json.keys()) out[CommandId(key)] = json.getDouble(key).toFloat()
            out as Map<CommandId, Float>
        }.getOrDefault(emptyMap())
    }
}
