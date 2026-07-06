package com.speechangel.data.di

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.enrollment.DictationBackend
import com.speechangel.core.enrollment.Enroller
import com.speechangel.core.enrollment.NoopDictationBackend
import com.speechangel.core.enrollment.NoopQbeEncoder
import com.speechangel.core.enrollment.QbeEncoder
import com.speechangel.core.enrollment.Recognizer
import com.speechangel.core.enrollment.WakeWordGate
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
    fun provideRecognizer(mfcc: MfccExtractor, vad: Vad, matcher: TemplateMatcher): Recognizer = Recognizer(mfcc, vad, matcher)

    @Provides
    @Singleton
    fun provideWakeWordGate(mfcc: MfccExtractor, matcher: TemplateMatcher): WakeWordGate = WakeWordGate(mfcc, matcher, wakeThreshold = 8.0f)

    /**
     * Query-by-example encoder binding (Phase 3, dormant). The optional QbE matcher is off by default;
     * with [NoopQbeEncoder] the [com.speechangel.core.enrollment.SpeechBackendSelector] never selects
     * the QbE branch, so the live loop stays on the template [Recognizer]. Swap this provider for a real
     * encoder to enable QbE — no other wiring changes.
     */
    @Provides
    @Singleton
    fun provideQbeEncoder(): QbeEncoder = NoopQbeEncoder()

    /**
     * Optional, opt-in batch-dictation backend (Phase 3, dormant). Bound to [NoopDictationBackend] so
     * the seam is live and the dictation stub screen renders "unavailable" until a real whisper.cpp
     * backend is supplied — swap this provider to enable it. Deliberately **not** on the always-on
     * command path: nothing in the [Recognizer]/action loop injects [DictationBackend].
     */
    @Provides
    @Singleton
    fun provideDictationBackend(): DictationBackend = NoopDictationBackend()

    @Provides
    @Singleton
    fun provideEnroller(mfcc: MfccExtractor, vad: Vad): Enroller = Enroller(
        mfcc = mfcc,
        vad = vad,
        idGenerator = { UUID.randomUUID().toString() },
        clock = { System.currentTimeMillis() },
    )
}
