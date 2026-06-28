package com.speechangel.data.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import com.speechangel.core.model.AudioSamples
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import javax.inject.Inject

/** Records a mono 16 kHz PCM utterance and returns it normalised to [-1, 1]. */
interface AudioRecorder {
    val sampleRateHz: Int

    /** Records for [durationMs]. Caller must hold RECORD_AUDIO. Throws [AudioCaptureException] on failure. */
    suspend fun record(durationMs: Int): AudioSamples

    /**
     * Continuous capture over ONE persistent recorder, emitting fixed [frameMs] frames until cancelled.
     * The Stage-1 wake gate consumes this so the wake→command transition never reopens the mic (which
     * would clip the command onset). Caller must hold RECORD_AUDIO.
     */
    fun stream(frameMs: Int): Flow<AudioSamples>
}

class AudioCaptureException(message: String) : Exception(message)

class AndroidAudioRecorder @Inject constructor() : AudioRecorder {

    override val sampleRateHz: Int = SAMPLE_RATE

    @SuppressLint("MissingPermission") // Permission is enforced by the caller (UI/foreground service).
    override suspend fun record(durationMs: Int): AudioSamples = withContext(Dispatchers.IO) {
        val minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL, ENCODING)
        if (minBuffer <= 0) throw AudioCaptureException("Unsupported audio configuration on this device")
        val bufferSize = maxOf(minBuffer, SAMPLE_RATE / 4 * 2)

        val recorder = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            SAMPLE_RATE,
            CHANNEL,
            ENCODING,
            bufferSize,
        )
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            throw AudioCaptureException("AudioRecord failed to initialise (permission or device issue)")
        }

        val totalSamples = SAMPLE_RATE * durationMs / 1000
        val out = FloatArray(totalSamples)
        val chunk = ShortArray(bufferSize / 2)
        var written = 0
        try {
            recorder.startRecording()
            while (written < totalSamples) {
                val read = recorder.read(chunk, 0, chunk.size)
                if (read <= 0) break
                var i = 0
                while (i < read && written < totalSamples) {
                    out[written++] = chunk[i] / PCM16_MAX
                    i++
                }
            }
        } finally {
            runCatching { recorder.stop() }
            recorder.release()
        }
        AudioSamples(if (written == totalSamples) out else out.copyOf(written), SAMPLE_RATE)
    }

    @SuppressLint("MissingPermission") // Permission is enforced by the caller (foreground service).
    override fun stream(frameMs: Int): Flow<AudioSamples> = flow {
        val frameSamples = SAMPLE_RATE * frameMs / 1000
        val minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL, ENCODING)
        if (minBuffer <= 0) throw AudioCaptureException("Unsupported audio configuration on this device")
        val recorder = AudioRecord(
            // Headroom: the collector processes each frame inline (off-main), so size the hardware
            // buffer for several frames to absorb processing spikes without dropping audio / clipping
            // a command onset during the wake→command transition.
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            SAMPLE_RATE,
            CHANNEL,
            ENCODING,
            maxOf(minBuffer, frameSamples * 4),
        )
        if (recorder.state != AudioRecord.STATE_INITIALIZED) {
            recorder.release()
            throw AudioCaptureException("AudioRecord failed to initialise (permission or device issue)")
        }
        val buf = ShortArray(frameSamples)
        try {
            recorder.startRecording()
            while (currentCoroutineContext().isActive) {
                var read = 0
                while (read < frameSamples) {
                    val r = recorder.read(buf, read, frameSamples - read)
                    if (r <= 0) break
                    read += r
                }
                if (read <= 0) break
                emit(AudioSamples(FloatArray(read) { buf[it] / PCM16_MAX }, SAMPLE_RATE))
            }
        } finally {
            runCatching { recorder.stop() }
            recorder.release()
        }
    }.flowOn(Dispatchers.IO)

    private companion object {
        const val SAMPLE_RATE = 16_000
        const val CHANNEL = AudioFormat.CHANNEL_IN_MONO
        const val ENCODING = AudioFormat.ENCODING_PCM_16BIT
        const val PCM16_MAX = 32_768f
    }
}
