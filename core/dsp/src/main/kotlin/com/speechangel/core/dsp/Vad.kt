package com.speechangel.core.dsp

import com.speechangel.core.model.AudioSamples
import kotlin.math.sqrt

/** A detected speech region within a buffer, in sample indices. */
data class SpeechSegment(val startSample: Int, val endSampleExclusive: Int) {
    val lengthSamples: Int get() = endSampleExclusive - startSample
}

/**
 * Voice-activity detection. Pluggable so an energy gate (default, no model) can be swapped for a
 * learned VAD (e.g. Silero) later without touching the recognizer (see `research/02_*` §T1.6).
 */
interface Vad {
    /** Returns the speech region, or null if the buffer is (effectively) silent. */
    fun detect(audio: AudioSamples): SpeechSegment?

    /** Convenience: trim [audio] to its speech region, or return an empty buffer if silent. */
    fun trim(audio: AudioSamples): AudioSamples {
        val seg = detect(audio) ?: return AudioSamples(FloatArray(0), audio.sampleRateHz)
        return AudioSamples(audio.samples.copyOfRange(seg.startSample, seg.endSampleExclusive), audio.sampleRateHz)
    }
}

/** Configuration for [EnergyVad]. */
data class EnergyVadConfig(
    val frameMs: Int = 20,
    val shiftMs: Int = 10,
    val energyRatioOverNoise: Double = 3.0,
    val absoluteRmsFloor: Float = 1e-3f,
    val minSpeechMs: Int = 80,
    val hangoverMs: Int = 80,
)

/**
 * Simple, robust RMS-energy VAD. Estimates a per-utterance noise floor, then marks frames whose
 * RMS exceeds `noiseFloor * ratio` (and an absolute floor) as speech, with hangover smoothing.
 */
class EnergyVad(private val config: EnergyVadConfig = EnergyVadConfig()) : Vad {

    override fun detect(audio: AudioSamples): SpeechSegment? {
        if (audio.isEmpty) return null
        val frameLen = (audio.sampleRateHz * config.frameMs / 1000).coerceAtLeast(1)
        val shift = (audio.sampleRateHz * config.shiftMs / 1000).coerceAtLeast(1)
        if (audio.samples.size < frameLen) return null

        val energies = ArrayList<Float>()
        var start = 0
        while (start + frameLen <= audio.samples.size) {
            energies.add(rms(audio.samples, start, frameLen))
            start += shift
        }
        if (energies.isEmpty()) return null

        val noiseFloor = percentile(energies, NOISE_PERCENTILE)
        val threshold = maxOf((noiseFloor * config.energyRatioOverNoise).toFloat(), config.absoluteRmsFloor)

        val minSpeechFrames = (config.minSpeechMs / config.shiftMs).coerceAtLeast(1)
        val hangoverFrames = config.hangoverMs / config.shiftMs

        var firstSpeech = -1
        var lastSpeech = -1
        var run = 0
        for (i in energies.indices) {
            if (energies[i] >= threshold) {
                run++
                if (run >= minSpeechFrames) {
                    if (firstSpeech < 0) firstSpeech = (i - run + 1).coerceAtLeast(0)
                    lastSpeech = i
                }
            } else {
                run = 0
            }
        }
        if (firstSpeech < 0) return null

        val startFrame = (firstSpeech - hangoverFrames).coerceAtLeast(0)
        val endFrame = (lastSpeech + hangoverFrames)
        val startSample = startFrame * shift
        val endSample = ((endFrame * shift) + frameLen).coerceAtMost(audio.samples.size)
        return SpeechSegment(startSample, endSample)
    }

    private companion object {
        const val NOISE_PERCENTILE = 0.10

        fun rms(samples: FloatArray, start: Int, len: Int): Float {
            var sum = 0.0
            for (i in start until start + len) sum += samples[i].toDouble() * samples[i]
            return sqrt(sum / len).toFloat()
        }

        fun percentile(values: List<Float>, p: Double): Float {
            val sorted = values.sorted()
            val idx = (p * (sorted.size - 1)).toInt().coerceIn(0, sorted.size - 1)
            return sorted[idx]
        }
    }
}
