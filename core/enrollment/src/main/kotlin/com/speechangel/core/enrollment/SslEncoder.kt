package com.speechangel.core.enrollment

import com.speechangel.core.model.AudioSamples

/**
 * Speech-representation encoder that maps raw audio directly to a fixed-length embedding.
 * Unlike [QbeEncoder] (which operates on MFCC [FeatureSequence]), this interface is for SSL
 * models (DistilHuBERT, WavLM, etc.) that extract features internally from raw PCM samples.
 *
 * Activation: [available] becomes true once a trained model is loaded. Until then the template
 * engine is selected by [SpeechBackendSelector].
 */
interface RawAudioEncoder {
    val available: Boolean
    val dimensions: Int

    /**
     * Encode raw PCM audio (16 kHz, 16-bit signed, mono) into an L2-normalised embedding
     * vector of length [dimensions]. The caller is responsible for VAD trimming before
     * calling encode — silence should be rejected before reaching the encoder.
     */
    fun encode(audio: AudioSamples): FloatArray
}

/**
 * Placeholder raw-audio encoder with no model loaded. Always unavailable.
 * Keeps the seam compiling until DistilHuBERT is wired at runtime.
 */
class NoopRawAudioEncoder : RawAudioEncoder {
    override val available: Boolean = false
    override val dimensions: Int = 0
    override fun encode(audio: AudioSamples): FloatArray = FloatArray(0)
}
