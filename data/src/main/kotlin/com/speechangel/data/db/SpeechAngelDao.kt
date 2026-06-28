package com.speechangel.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface SpeechAngelDao {

    @Query("SELECT * FROM commands ORDER BY label")
    fun observeCommands(): Flow<List<CommandEntity>>

    @Query("SELECT * FROM commands WHERE id = :id")
    suspend fun getCommand(id: String): CommandEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertCommand(command: CommandEntity)

    @Query("DELETE FROM commands WHERE id = :id")
    suspend fun deleteCommand(id: String)

    @Query("SELECT * FROM templates")
    fun observeTemplates(): Flow<List<TemplateEntity>>

    @Query("SELECT * FROM templates")
    suspend fun allTemplates(): List<TemplateEntity>

    @Query("SELECT * FROM templates WHERE commandId = :commandId")
    suspend fun templatesFor(commandId: String): List<TemplateEntity>

    @Query("SELECT COUNT(*) FROM templates WHERE commandId = :commandId")
    suspend fun countFor(commandId: String): Int

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun addTemplate(template: TemplateEntity)

    @Delete
    suspend fun deleteTemplate(template: TemplateEntity)

    @Query("DELETE FROM templates WHERE id = :id")
    suspend fun deleteTemplateById(id: String)

    @Query("DELETE FROM templates WHERE commandId = :commandId")
    suspend fun deleteTemplatesFor(commandId: String)
}
