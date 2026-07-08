package com.speechangel.data.encoder

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import com.speechangel.core.enrollment.RawAudioEncoder
import com.speechangel.core.model.AudioSamples
import java.nio.FloatBuffer

/**
 * DistilHuBERT (ntu-spml/distilhubert) query-by-example encoder that runs ONNX inference
 * on-device. Expects 16 kHz, 16-bit signed, mono PCM — caller is responsible for VAD trim
 * and silence rejection upstream.
 *
 * ## Model file
 * The ONNX model (89.7 MB fp32, opset 17) must be present at the path supplied to [load].
 * For production this is typically `context.getExternalFilesDir(null) + "/distilhubert.onnx"`
 * — downloaded on first launch or bundled in the APK as an asset. The model is NOT committed
 * to this repository (blocked on an external asset — see docs/ROADMAP.md).
 *
 * ## Layer selection
 * Layer 2 (0-indexed) of DistilHuBERT's transformer stack is used — the last layer of the
 * 2-layer student model. This is the same configuration proven in CP-2 calibrations (E1–E20).
 * The ONNX model already applies mean-pool + L2-normalise, so [encode] returns a unit-norm
 * 768-dimensional embedding ready for cosine prototype matching.
 *
 * ## Thread safety
 * [OrtSession] is thread-safe for concurrent [OrtSession.run] calls after creation.
 * [encode] is safe to call from any thread.
 */

class DistilHuBERTEncoder(private val modelPath: String) : AutoCloseable, RawAudioEncoder {

    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()
    private var session: OrtSession? = null

    /** True once [load] succeeds. */
    override val available: Boolean get() = session != null

    /** DistilHuBERT embedding width. */
    override val dimensions: Int = 768

    private val SAMPLE_RATE_HZ = 16000

    /**
     * Load the ONNX model from [modelPath]. Must be called once before [encode].
     * @throws ai.onnxruntime.OrtException if the model file is missing or invalid.
     */
    fun load() {
        session = env.createSession(modelPath)
    }

    /**
     * Encode raw PCM audio (16 kHz, 16-bit, mono) into a 768-dim L2-normalised embedding.
     * Returns a zero-filled array if the session is not loaded.
     *
     * @throws ai.onnxruntime.OrtException on inference failure.
     */
    override fun encode(audio: AudioSamples): FloatArray {
        val sess = session ?: return FloatArray(dimensions)
        val samples = audio.samples
        if (samples.isEmpty()) return FloatArray(dimensions)

        val floatSamples = FloatArray(samples.size) { i -> samples[i].toFloat() }
        var mean = 0.0
        var std = 0.0
        for (s in floatSamples) mean += s
        mean /= floatSamples.size
        for (i in floatSamples.indices) {
            val d = floatSamples[i] - mean
            std += d * d
        }
        std = kotlin.math.sqrt(std / floatSamples.size)
        val eps = 1e-7f
        for (i in floatSamples.indices) {
            floatSamples[i] = ((floatSamples[i] - mean) / (std + eps)).toFloat()
        }

        val inputShape = longArrayOf(1, floatSamples.size.toLong())
        val inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(floatSamples), inputShape)

        val result = sess.run(mapOf("audio" to inputTensor))
        val output = result.first().value as Array<FloatArray>
        val embedding = output[0]

        inputTensor.close()
        result.use { }

        return embedding
    }

    override fun close() {
        session?.close()
        session = null
    }
}
