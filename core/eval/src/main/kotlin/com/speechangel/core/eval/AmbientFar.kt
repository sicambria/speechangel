package com.speechangel.core.eval

import com.speechangel.core.dsp.EnergyVad
import com.speechangel.core.dsp.MfccExtractor
import com.speechangel.core.dsp.Vad
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.matching.TemplateMatcher
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.RecognitionResult
import com.speechangel.core.model.Template
import java.util.Locale

/**
 * The first **ambient false-accept-per-hour proxy** for SpeechAngel — the always-on number the existing
 * TORGO harness explicitly *cannot* produce (`TorgoEval.renderCaveats`: "TORGO has no continuous ambient
 * stream"). It concatenates real OOV (non-command) speech + optional noise into a simulated continuous
 * listening stream, slides the command window over it, and counts how often enrolled templates
 * false-fire → **FA/hour** at a given operating threshold.
 *
 * **Honesty (emitted in [render]):**
 * - Concatenated isolated OOV words with silence gaps are **less** command-like than continuous TV /
 *   dialogue, so this proxy is likely **optimistically biased** (fewer false fires than a real living
 *   room). It is a proxy, not a field measurement.
 * - Supplying a real recording via `-Dambient.wav=…` replaces the synthetic stream with a real one, at
 *   which point the number becomes a genuine (still single-room) measurement.
 */
class AmbientFar(
    private val frontEnd: FeatureFrontEnd,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val windowMs: Int = 1500,
    private val hopMs: Int = 500,
    private val vad: Vad = EnergyVad(),
) {
    data class Result(
        val streamSeconds: Double,
        val windows: Int,
        val falseAccepts: Int,
        val faPerHour: Double,
        val threshold: Float,
        val synthetic: Boolean,
    )

    /**
     * Build a synthetic continuous ambient stream from real OOV utterances, each followed by a [gapMs]
     * silence, with optional additive white noise at [noiseSnrDb]. Deterministic from [seed].
     */
    fun buildStream(oov: List<AudioSamples>, gapMs: Int = 400, noiseSnrDb: Double? = null, seed: Long = 1): AudioSamples {
        if (oov.isEmpty()) return AudioSamples(FloatArray(0), frontEnd.config.sampleRateHz)
        val sr = oov.first().sampleRateHz
        val gap = FloatArray((sr * gapMs / 1000).coerceAtLeast(1))
        val pieces = ArrayList<AudioSamples>()
        for (u in oov) {
            pieces.add(u)
            pieces.add(AudioSamples(gap, sr))
        }
        var stream = AudioSamples.concat(pieces)
        if (noiseSnrDb != null) stream = AudioAugment.addWhiteNoise(stream, noiseSnrDb, seed, vad)
        return stream
    }

    /**
     * Slide the command window over [ambient] and count false accepts against [templates] at operating
     * [threshold]. Overlapping accepting windows are debounced (one accept → skip a full window) so hop
     * overlap does not inflate the count. All accepts are false accepts (ambient has no true commands).
     */
    fun measure(templates: List<Template>, ambient: AudioSamples, threshold: Float, synthetic: Boolean): Result {
        val sr = ambient.sampleRateHz
        val win = (sr * windowMs / 1000).coerceAtLeast(1)
        val hop = (sr * hopMs / 1000).coerceAtLeast(1)
        val mfcc = MfccExtractor(frontEnd.config)
        val matcher = TemplateMatcher(matcherConfig.copy(defaultAcceptanceThreshold = threshold))

        var start = 0
        var windows = 0
        var falseAccepts = 0
        while (start + win <= ambient.samples.size) {
            windows++
            val window = AudioSamples(ambient.samples.copyOfRange(start, start + win), sr)
            val speech = vad.trim(window)
            val accepted = if (speech.isEmpty) {
                false
            } else {
                val q = mfcc.extract(speech)
                !q.isEmpty && matcher.match(q, templates) is RecognitionResult.Match
            }
            if (accepted) {
                falseAccepts++
                start += win // debounce: skip the rest of this event.
            } else {
                start += hop
            }
        }
        val seconds = if (sr <= 0) 0.0 else ambient.samples.size.toDouble() / sr
        val faPerHour = if (seconds <= 0.0) 0.0 else falseAccepts / (seconds / 3600.0)
        return Result(seconds, windows, falseAccepts, faPerHour, threshold, synthetic)
    }

    fun render(r: Result, corpus: String): String = buildString {
        appendLine("## Ambient FAR/hour proxy ($corpus)")
        appendLine()
        val kind = if (r.synthetic) "**SYNTHETIC** stream (real OOV speech + silence gaps + noise)" else "dropped-in real recording"
        appendLine("Source: $kind. Operating threshold ${String.format(Locale.US, "%.2f", r.threshold)}.")
        appendLine()
        appendLine(
            "- Simulated listening: **${String.format(Locale.US, "%.1f", r.streamSeconds / 60.0)} min** " +
                "(${r.windows} windows of $windowMs ms, $hopMs ms hop, debounced).",
        )
        appendLine("- False accepts: **${r.falseAccepts}** → **${String.format(Locale.US, "%.2f", r.faPerHour)} FA/hour**.")
        appendLine()
        if (r.synthetic) {
            appendLine("_Honesty:_ concatenated isolated OOV words with silence gaps are **less** command-like than")
            appendLine("continuous TV/conversation, so this proxy is **optimistically biased** — a real living room")
            appendLine("would likely false-fire more. Drop in a real ambient recording (`-Dambient.wav`) to replace")
            appendLine("this proxy with a genuine measurement. The Phase-0 exit (≤ 0.5 FA/hr on real continuous")
            appendLine("audio) remains gated on that recording — this proxy does not retire it.")
        } else {
            appendLine("_Note:_ a single real recording — a genuine measurement for THIS room/content, not yet a")
            appendLine("distribution over rooms. The Phase-0 ≤ 0.5 FA/hr exit needs representative continuous audio.")
        }
        appendLine()
    }
}
