package com.speechangel.data.di

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import java.util.UUID
import javax.inject.Singleton

/** Wires the pure-Kotlin recognizer core into the DI graph. Configs are the single tuning surface. */
@Module
@InstallIn(SingletonComponent::class)
internal object RecognitionModule {

    @Provides
    @Singleton
    fun provideMfccConfig(): MfccConfig = MfccConfig()

    @Provides
    @Singleton
    fun provideMfccExtractor(config: MfccConfig): MfccExtractor = MfccExtractor(config)

    @Provides
    @Singleton
    fun provideVad(): Vad = EnergyVad()

    @Provides
    @Singleton
    fun provideMatcherConfig(): MatcherConfig = MatcherConfig()

    @Provides
    @Singleton
    fun provideTemplateMatcher(config: MatcherConfig): TemplateMatcher = TemplateMatcher(config)

    @Provides
    @Singleton
    fun provideRecognizer(mfcc: MfccExtractor, vad: Vad, matcher: TemplateMatcher): Recognizer =
        Recognizer(mfcc, vad, matcher)

    @Provides
    @Singleton
    fun provideEnroller(mfcc: MfccExtractor, vad: Vad): Enroller =
        Enroller(
            mfcc = mfcc,
            vad = vad,
            idGenerator = { UUID.randomUUID().toString() },
            clock = { System.currentTimeMillis() },
        )
}
