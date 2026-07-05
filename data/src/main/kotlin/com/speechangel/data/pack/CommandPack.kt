package com.speechangel.data.pack

import com.speechangel.core.model.VoiceCommand
import org.json.JSONArray
import org.json.JSONObject

/**
 * A shareable command pack (Phase 3). Because the matcher is **speaker-dependent**, a pack is NOT a
 * bundle of one person's audio — it is a vocabulary + action mapping (`label` → `actionId`) that the
 * recipient **re-enrols in their own voice**. Definitions only; no templates travel, so no voice audio
 * ever leaves the device through a pack.
 */
data class CommandPack(val schemaVersion: Int, val name: String, val author: String, val commands: List<PackCommand>)

/** One command definition in a pack: what to say ([label]) and which action id it maps to. */
data class PackCommand(val label: String, val actionId: String)

/** Thrown when a pack string is malformed or its schema is newer than this build understands. */
class CommandPackException(message: String) : Exception(message)

/** Encodes/decodes a [CommandPack] as JSON (org.json — already available on Android). */
object CommandPackCodec {
    const val SCHEMA_VERSION = 1

    fun encode(pack: CommandPack): String {
        val commands = JSONArray()
        for (c in pack.commands) {
            commands.put(JSONObject().put("label", c.label).put("actionId", c.actionId))
        }
        return JSONObject()
            .put("schemaVersion", pack.schemaVersion)
            .put("name", pack.name)
            .put("author", pack.author)
            .put("commands", commands)
            .toString()
    }

    fun decode(json: String): CommandPack {
        val root = runCatching { JSONObject(json) }
            .getOrElse { throw CommandPackException("not a valid command pack: ${it.message}") }
        val version = root.optInt("schemaVersion", -1)
        if (version !in 1..SCHEMA_VERSION) {
            val why = if (version > SCHEMA_VERSION) "newer than supported" else "missing or invalid"
            throw CommandPackException("pack schemaVersion $version is $why ($SCHEMA_VERSION)")
        }
        val commandsJson = root.optJSONArray("commands") ?: JSONArray()
        val commands = ArrayList<PackCommand>(commandsJson.length())
        for (i in 0 until commandsJson.length()) {
            val c = commandsJson.getJSONObject(i)
            commands.add(PackCommand(c.optString("label"), c.optString("actionId")))
        }
        return CommandPack(version, root.optString("name"), root.optString("author"), commands)
    }
}

/** Builds a pack from the user's current commands (definitions only — no templates included). */
object CommandPackExporter {
    fun export(name: String, author: String, commands: List<VoiceCommand>): CommandPack = CommandPack(
        schemaVersion = CommandPackCodec.SCHEMA_VERSION,
        name = name,
        author = author,
        commands = commands.map { PackCommand(it.label, it.action.value) },
    )
}

/** Why a pack command could not be imported. */
enum class RejectReason { UNKNOWN_ACTION, BLANK_LABEL }

/** A pack command that failed import, with the reason (surfaced to the user, never silently dropped). */
data class RejectedCommand(val command: PackCommand, val reason: RejectReason)

/** The outcome of validating a pack: what would import vs what was rejected and why. */
data class PackImportResult(val accepted: List<PackCommand>, val rejected: List<RejectedCommand>)

/**
 * Validates a pack before import. Every command's [PackCommand.actionId] is checked against
 * [isKnownAction] (the app passes `DeviceAction.fromId(it) != null`), so a pack can never introduce an
 * action this build cannot perform — the deterministic action layer stays sound. Unknown actions and
 * blank labels are collected into the rejection list, never imported silently. The pack layer stays
 * decoupled from the app's action table via the predicate.
 */
object CommandPackImporter {
    fun validate(pack: CommandPack, isKnownAction: (String) -> Boolean): PackImportResult {
        val accepted = ArrayList<PackCommand>()
        val rejected = ArrayList<RejectedCommand>()
        for (c in pack.commands) {
            when {
                c.label.isBlank() -> rejected.add(RejectedCommand(c, RejectReason.BLANK_LABEL))
                !isKnownAction(c.actionId) -> rejected.add(RejectedCommand(c, RejectReason.UNKNOWN_ACTION))
                else -> accepted.add(c)
            }
        }
        return PackImportResult(accepted, rejected)
    }
}
