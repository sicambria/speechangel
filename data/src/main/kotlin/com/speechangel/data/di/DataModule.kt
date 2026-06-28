package com.speechangel.data.di

import android.content.Context
import androidx.room.Room
import com.speechangel.core.enrollment.CommandRepository
import com.speechangel.core.enrollment.TemplateRepository
import com.speechangel.data.audio.AndroidAudioRecorder
import com.speechangel.data.audio.AudioRecorder
import com.speechangel.data.db.SpeechAngelDao
import com.speechangel.data.db.SpeechAngelDatabase
import com.speechangel.data.repository.RoomCommandRepository
import com.speechangel.data.repository.RoomTemplateRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class DataBindingsModule {
    @Binds
    @Singleton
    abstract fun bindCommandRepository(impl: RoomCommandRepository): CommandRepository

    @Binds
    @Singleton
    abstract fun bindTemplateRepository(impl: RoomTemplateRepository): TemplateRepository

    @Binds
    @Singleton
    abstract fun bindAudioRecorder(impl: AndroidAudioRecorder): AudioRecorder
}

@Module
@InstallIn(SingletonComponent::class)
internal object DataProvidersModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): SpeechAngelDatabase =
        Room.databaseBuilder(context, SpeechAngelDatabase::class.java, SpeechAngelDatabase.NAME)
            .fallbackToDestructiveMigration()
            .build()

    @Provides
    fun provideDao(database: SpeechAngelDatabase): SpeechAngelDao = database.dao()
}
