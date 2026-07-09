package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.Template
import com.speechangel.core.model.TemplateId
import java.io.File

/**
 * **SOTA Domain 11 — on-device recognition latency (P50).** The domain-bands doc marks this "physical
 * device only." This harness does not wait for a device: it times the **real shipped decide path**
 * ([EnergyVad] trim → [MfccExtractor] → [TemplateMatcher] 1-NN min-DTW over a realistic template pool)
 * on the host JVM, then scales the host percentiles to a Pixel 6 with a single, documented, cited CPU
 * factor. Every assumption is explicit — this is a `SIMULATED_DEVICE` estimate, **excluded from the
 * wall-dominated composite** (a host-scaled number must never *set* the reported wall — see the
 * scorecard plan and `SotaScorecard.kt`).
 *
 * ## Device scaling (the one assumption, made explicit)
 * `device_ms = host_ms × [DEVICE_SCALE]`.
 * `DEVICE_SCALE` = (host single-core throughput) / (Pixel 6 single-core throughput), Geekbench-6
 * single-core as the common yardstick:
 * - Host measured on: AMD Ryzen 7 8845HS (GB6 ST ≈ 2650).
 * - Target: Pixel 6, Google Tensor, Cortex-X1 @ 2.8 GHz (GB6 ST ≈ 1050, published).
 * - Ratio ≈ 2.52, **rounded up to 2.6** to bias the device *slower* (also covers ART-vs-JIT hot-loop
 *   overhead, which favours the desktop JVM). A wrong constant moves this by at most a band and can
 *   never affect the composite (D11 is excluded). The actual host CPU string is read from
 *   `/proc/cpuinfo` at run time and echoed into the provenance so a different host is caught, not
 *   silently mis-scaled.
 */
class LatencyEval(
    private val frontEnd: FeatureFrontEnd = FeatureFrontEnd("none", MfccConfig(deltaOrder = DeltaOrder.NONE)),
    private val mic: String = "wav_headMic",
    private val minReps: Int = 2,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val warmup: Int = 30,
    private val reps: Int = 200,
    private val deviceScale: Double = DEVICE_SCALE,
    private val sliceMaxCommands: Int = 25,
) {
    data class Result(
        val hostCpu: String,
        val deviceScale: Double,
        val templateCount: Int,
        val timedQueries: Int,
        val hostP50Ms: Double,
        val hostP99Ms: Double,
        val deviceP50Ms: Double,
        val deviceP99Ms: Double,
        val corpus: String,
    )

    /**
     * Enroll a realistic deployment-slice vocabulary (the largest ≤ [sliceMaxCommands]-command speaker),
     * then time the full decide path over that speaker's utterances. Returns null if no such speaker
     * exists (empty corpus).
     */
    fun run(root: File): Result? {
        val mfcc = MfccExtractor(frontEnd.config)
        val vad = EnergyVad()
        val matcher = TemplateMatcher(matcherConfig)

        val speaker = TorgoCorpus.scan(root, mic, minReps)
            .filter { it.commands.isNotEmpty() && it.commandCount <= sliceMaxCommands }
            .maxByOrNull { it.commandCount } ?: return null

        // Full enrollment (latency is a compute property; correctness of the split is irrelevant here —
        // we want a realistic template pool and realistic queries).
        var id = 0L
        val templates = ArrayList<Template>()
        val queries = ArrayList<com.speechangel.core.model.AudioSamples>()
        for ((word, utts) in speaker.commands) {
            for (u in utts) {
                val audio = WavFile.read(u.wav)
                val feats = featuresOrNull(audio, vad, mfcc) ?: continue
                templates += Template(TemplateId("lat-${id++}"), CommandId(word), feats)
                queries += audio
            }
        }
        if (templates.isEmpty() || queries.isEmpty()) return null

        // Warmup (let the JIT compile the hot DTW loop), then timed reps cycling through the queries.
        repeat(warmup) { i -> decideOnce(queries[i % queries.size], vad, mfcc, matcher, templates) }
        val samples = DoubleArray(reps) { i ->
            decideOnce(queries[i % queries.size], vad, mfcc, matcher, templates) / 1_000_000.0 // ns → ms
        }
        samples.sort()

        val hostP50 = percentile(samples, 0.50)
        val hostP99 = percentile(samples, 0.99)
        return Result(
            hostCpu = readHostCpu(),
            deviceScale = deviceScale,
            templateCount = templates.size,
            timedQueries = queries.size,
            hostP50Ms = hostP50,
            hostP99Ms = hostP99,
            deviceP50Ms = hostP50 * deviceScale,
            deviceP99Ms = hostP99 * deviceScale,
            corpus = root.name,
        )
    }

    /** VAD-trim → MFCC for one recording, or null if it trims/extracts to empty. */
    private fun featuresOrNull(
        audio: com.speechangel.core.model.AudioSamples,
        vad: EnergyVad,
        mfcc: MfccExtractor,
    ): com.speechangel.core.model.FeatureSequence? {
        val speech = vad.trim(audio)
        if (speech.isEmpty) return null
        val feats = mfcc.extract(speech)
        return feats.takeUnless { it.isEmpty }
    }

    /** One full decide: VAD trim → MFCC → match. Returns elapsed nanoseconds. */
    private fun decideOnce(
        audio: com.speechangel.core.model.AudioSamples,
        vad: EnergyVad,
        mfcc: MfccExtractor,
        matcher: TemplateMatcher,
        templates: List<Template>,
    ): Double {
        val start = System.nanoTime()
        val speech = vad.trim(audio)
        val feats = mfcc.extract(speech)
        matcher.match(feats, templates)
        return (System.nanoTime() - start).toDouble()
    }

    private fun percentile(sorted: DoubleArray, p: Double): Double {
        if (sorted.isEmpty()) return 0.0
        val idx = (p * (sorted.size - 1)).toInt().coerceIn(0, sorted.size - 1)
        return sorted[idx]
    }

    private fun readHostCpu(): String = try {
        File("/proc/cpuinfo").readLines()
            .firstOrNull { it.startsWith("model name") }
            ?.substringAfter(':')?.trim() ?: "unknown"
    } catch (_: Exception) {
        "unknown"
    }

    companion object {
        /** Host(Ryzen 7 8845HS, GB6 ST ≈ 2650) / Pixel 6 (Cortex-X1, GB6 ST ≈ 1050) ≈ 2.52, rounded up. */
        const val DEVICE_SCALE: Double = 2.6
    }
}
