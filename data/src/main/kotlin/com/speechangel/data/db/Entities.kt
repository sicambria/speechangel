package com.speechangel.data.db

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "commands")
data class CommandEntity(@PrimaryKey val id: String, val label: String, val action: String)

@Entity(
    tableName = "templates",
    foreignKeys = [
        ForeignKey(
            entity = CommandEntity::class,
            parentColumns = ["id"],
            childColumns = ["commandId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("commandId")],
)
data class TemplateEntity(
    @PrimaryKey val id: String,
    val commandId: String,
    val condition: String,
    val createdAtEpochMs: Long,
    val features: ByteArray,
) {
    // Room entities with array fields need explicit equals/hashCode.
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is TemplateEntity) return false
        return id == other.id
    }

    override fun hashCode(): Int = id.hashCode()
}
