package com.speechangel.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [CommandEntity::class, TemplateEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class SpeechAngelDatabase : RoomDatabase() {
    abstract fun dao(): SpeechAngelDao

    companion object {
        const val NAME = "speechangel.db"
    }
}
