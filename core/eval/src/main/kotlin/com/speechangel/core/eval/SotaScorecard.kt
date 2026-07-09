package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import java.io.File
import java.util.Locale

/**
 * Runs the measurable subset of the 15-domain SOTA ladder ([DomainBands]) against real corpora on the
 * **shipped** static-MFCC front-end (`deltaOrder=NONE`), maps each measurement to a band, and emits a
 * machine-readable score plus a human composite band map. It is the first automated bridge from measured
 * performance to the `SOTA=1000` scale — the doc's "Current band" column was hand-typed until now.
 *
 * ## Honesty contract (why this is trustworthy, not a vanity number)
 * - **Wall-dominated composite** — the headline is the *minimum* band over the shipped-system domains,
 *   never a mean (a mean laundered ~<600 walls into a mid-600s score).
 * - **No fabrication** — a domain with no real measurement on this host is [Status.NOT_MEASURED] with the
 *   exact reason/command, not a guessed band.
 * - **Fidelity is first-class** — simulated-channel (noise/reverb/bandwidth), proxy (ambient FA/hr), and
 *   low-fidelity/confounded (vocab, enrollment) measurements are tagged and the last are excluded from the
 *   authoritative composite rather than laundered into a clean band.
 * - **Optimistic-bias disclosure** — the composite is over measurable domains only; the unmeasured ones
 *   (real-ambient, language, device) are precisely the known-weak axes, so the true binding band can only
 *   be equal or lower. The report says so.
 * - **Config-explicit** — every value carries its front-end/corpus/regime/on-off-device provenance.
 *
 * SSL domains (7/8/9) are read from an optional key=value metrics file produced by the Python spikes
 * (`--emit`), never parsed from their prose stdout.
 */
class SotaScorecard(
    private val frontEnd: FeatureFrontEnd = FeatureFrontEnd("none", MfccConfig(deltaOrder = DeltaOrder.NONE)),
    private val k: Int = 5,
    private val minReps: Int = 2,
    private val mic: String = "wav_headMic",
    private val target: Double = 0.05,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
) {
    enum class Status { MEASURED, PROXY, SIMULATED_CHANNEL, SIMULATED_DEVICE, LOW_FIDELITY, NOT_MEASURED }

    data class DomainScore(
        val id: Int,
        val name: String,
        /** Measured value in the spec's unit, or null when [Status.NOT_MEASURED]. */
        val value: Double?,
        /** Band in [DomainBands]; meaningful only when [value] != null. */
        val band: Int,
        val status: Status,
        /** Whether this domain contributes to the shipped-system wall-dominated composite. */
        val countsForComposite: Boolean,
        val config: String,
    )

    data class Scorecard(val corpus: String, val domains: List<DomainScore>) {
        val measured: List<DomainScore> get() = domains.filter { it.status != Status.NOT_MEASURED && it.value != null }
        val compositeDomains: List<DomainScore> get() = measured.filter { it.countsForComposite }

        /** Wall-dominated: the minimum band over shipped-system measured domains. */
        val bindingBand: Int get() = compositeDomains.minOfOrNull { it.band } ?: DomainBands.BELOW_FLOOR
        val bindingLabel: String get() = DomainBands.bandLabel(bindingBand)
        val bindingDomains: List<DomainScore> get() = compositeDomains.filter { it.band == bindingBand }
    }

    fun run(torgoRoot: File, sslMetrics: File? = null): Scorecard {
        val ssl = sslMetrics?.takeIf { it.isFile }?.let { readMetrics(it) } ?: emptyMap()
        val domains = torgoDomains(torgoRoot) +
            conditionDomains(torgoRoot) +
            ambientDomain(torgoRoot) +
            sslDomains(ssl) +
            deviceDomains(torgoRoot) +
            enrollmentDomain(torgoRoot) +
            blockedDomains()
        return Scorecard(torgoRoot.name, domains.sortedBy { it.id })
    }

    /** Domains 1 (rank-1), 2 (FRR@FAR), 14 (vocab scaling) — one shipped-static TorgoEval run. */
    private fun torgoDomains(root: File): List<DomainScore> {
        val torgo = TorgoEval(frontEnd, k, minReps, mic, matcherConfig).run(root)
        val agg = torgo.aggregate
        val cfg = "static MFCC (`none`), TORGO ${torgo.speakerSet} speaker-dependent, held-out (EVAL-002)"
        val d1 = domain(1, agg.rank1, Status.MEASURED, true, "$cfg; aggregate rank-1")
        val d2 = domain(
            2,
            agg.frrLowFarGlobalHeldOut,
            Status.MEASURED,
            true,
            "$cfg; FRR at realized FAR ${pct(agg.farLowFarGlobalHeldOut)} (per-utterance OOV, not per-hour)",
        )
        // D14: largest-vocabulary speaker's rank-1 — CONFOUNDED with speaker (no clean within-speaker
        // sub-sampling curve), so LOW_FIDELITY and excluded from the composite.
        val largest = torgo.perSpeaker.maxByOrNull { it.commandCount }
        val d14 = if (largest == null) {
            notMeasured(14, "no speaker rows")
        } else {
            domain(
                14,
                largest.rank1,
                Status.LOW_FIDELITY,
                false,
                "$cfg; ${largest.id} @ ${largest.commandCount} cmds — CONFOUNDED with speaker; excluded from composite",
            )
        }
        return listOf(d1, d2, d14)
    }

    /** Domains 4/5/6 — the simulated-channel condition grid (one ConditionEval run). */
    private fun conditionDomains(root: File): List<DomainScore> {
        val byName = ConditionEval(frontEnd, k, minReps, mic, target, matcherConfig)
            .run(root, Conditions.standard).associateBy { it.name }
        val cfg = "static MFCC (`none`), TORGO deployment-slice (≤25 cmds), SIMULATED channel"
        return listOf(
            conditionDomain(byName, "noise_20dB", 4, "$cfg; additive white noise @ 20 dB SNR")
                ?: notMeasured(4, "condition noise_20dB absent"),
            conditionDomain(byName, "reverb_small", 5, "$cfg; simulated room reverb (rt60≈250 ms)")
                ?: notMeasured(5, "condition reverb_small absent"),
            conditionDomain(byName, "bandlimit_tel", 6, "$cfg; telephone band-limit 300–3400 Hz")
                ?: notMeasured(6, "condition bandlimit_tel absent"),
        )
    }

    /** Domain 3 — ambient FA/hr proxy (optimistically biased). */
    private fun ambientDomain(root: File): DomainScore {
        val fahr = measureAmbient(root) ?: return notMeasured(3, "no deployment-slice speaker for the ambient proxy")
        return domain(
            3,
            fahr,
            Status.PROXY,
            true,
            "static MFCC (`none`); synthetic in-regime proxy (speaker OOV + silence + 20 dB noise) — OPTIMISTICALLY BIASED",
        )
    }

    /**
     * Domains 7/8/9 — Python spikes via the `--emit` metrics bridge. D7 (in-regime wake detection) is a
     * torch-free numpy MFCC spike and a shipped-path PROXY (counts); D8/D9 need torch and are off-device
     * research-tier (excluded).
     *
     * **Domain 10 is deliberately NOT here.** Its `lang_indep_rank1.py` diagnostic empirically confirms
     * that single-read Common Voice yields only chance-level cross-clip rank-1 (English anchor ≈ 1/N ≈
     * chance) — the null, not a signal. DTW distance is informative only for same-content pairs, which CV
     * lacks, so no valid command-word rank-1 proxy exists on available data. D10 therefore stays
     * [Status.NOT_MEASURED]; its band basis is the **by-construction** argument (no LM/lexicon/phoneme in
     * the shipped MFCC path; Zhang 2014; Picovoice 89.2% untuned English corroboration) documented in
     * `docs/product/2026-07-08_sota-domain-bands.md` §10 — argued in prose, never mapped to a band from
     * noise (the doc's "no theoretical derivations in the band table" rule).
     */
    private fun sslDomains(ssl: Map<Int, Metric>): List<DomainScore> = listOf(
        sslDomain(
            ssl,
            7,
            Status.PROXY,
            true,
            "in-regime MFCC-DTW detection @ ≤0.5 FA/hr, LibriSpeech bg, off-device numpy MFCC (mirrors shipped `none`)",
            "run `make sota-score-ssl` → `in_regime.py mfcc <spk> <bg_min> --emit` (torch-free; in-regime proxy, optimistically biased)",
        ),
        sslDomain(
            ssl,
            8,
            Status.MEASURED,
            false,
            "dual-cascade rel FRR reduction, WavLM-base-plus L12, off-device",
            "run `dual_cascade_verify.py --emit` (needs torch; research-tier, not shipped)",
        ),
        sslDomain(
            ssl,
            9,
            Status.MEASURED,
            false,
            "SSL embedding ceiling rank-1, off-device",
            "run `sweep_ssl.py --emit` (needs torch; ceiling probe, deployable student NOT BUILT)",
        ),
        notMeasured(
            10,
            "language independence: single-read Common Voice yields only chance-level cross-clip rank-1 " +
                "(anchor ≈ 1/N ≈ chance — the null; `lang_indep_rank1.py` diagnostic), so no valid " +
                "command-word rank-1 proxy exists on available data. Basis is by-construction (no " +
                "LM/lexicon/phoneme in the shipped MFCC path; Zhang 2014; Picovoice 89.2% untuned) — see " +
                "domain-bands §10, argued in prose not banded from noise",
        ),
    )

    /** Domains 11/12 — on-device latency + battery, host-measured then device-scaled (SIMULATED_DEVICE, excluded). */
    private fun deviceDomains(root: File): List<DomainScore> {
        val latency = LatencyEval(frontEnd, mic, minReps, matcherConfig).run(root)
            ?: return listOf(
                notMeasured(11, "no deployment-slice speaker to time"),
                notMeasured(12, "no latency input for the battery model"),
            )
        val d11 = domain(
            11,
            latency.deviceP50Ms,
            Status.SIMULATED_DEVICE,
            false,
            "host P50 ${fmt(latency.hostP50Ms)} ms on ${latency.hostCpu} × ${latency.deviceScale} (Pixel 6 scale) " +
                "over ${latency.templateCount} templates — HOST-SCALED estimate, excluded from composite",
        )
        val model = BatteryModel()
        val battery = model.estimate(latency.deviceP50Ms)
        val d12 = domain(
            12,
            battery.pctPerHour,
            Status.SIMULATED_DEVICE,
            false,
            "${fmt(battery.pctPerHour)}%/hr (±${fmt(battery.pctPerHourHigh - battery.pctPerHour)}); ${model.assumptions()}",
        )
        return listOf(d11, d12)
    }

    /** Domain 13 — enrollment efficiency: real TORGO template-count sweep (MEASURED, counts). */
    private fun enrollmentDomain(root: File): DomainScore {
        val e = EnrollmentEfficiencyEval(frontEnd, k, minReps, mic, matcherConfig).run(root)
        if (e.points.all { it.queries == 0 }) return notMeasured(13, "no scorable positives for the enrollment sweep")
        return domain(
            13,
            e.efficiency,
            Status.MEASURED,
            true,
            "static MFCC (`none`), TORGO; 1-shot rank-1 ${pct(e.oneShotRank1)} / saturation ${pct(e.saturationRank1)} " +
                "(saturates @ ${e.saturationCount} templates) → efficiency ${pct(e.efficiency)}",
        )
    }

    /** Domain 15 — structural (guardrail count), not a performance measurement; NOT_MEASURED by design. */
    private fun blockedDomains(): List<DomainScore> = listOf(
        notMeasured(
            15,
            "guardrail coverage: structural/process, not a performance measurement " +
                "(see `scripts/audits/verify-sota-measurement.mjs`)",
        ),
    )

    // ---- measurement helpers ----

    private fun domain(id: Int, value: Double, status: Status, counts: Boolean, config: String): DomainScore =
        DomainScore(id, DomainBands.spec(id).name, value, DomainBands.bandFor(id, value), status, counts, config)

    private fun notMeasured(id: Int, reason: String): DomainScore =
        DomainScore(id, DomainBands.spec(id).name, null, DomainBands.BELOW_FLOOR, Status.NOT_MEASURED, false, reason)

    private fun conditionDomain(
        byName: Map<String, ConditionEval.ConditionResult>,
        condition: String,
        id: Int,
        config: String,
    ): DomainScore? = byName[condition]?.let { domain(id, it.rank1, Status.SIMULATED_CHANNEL, true, config) }

    private fun sslDomain(
        ssl: Map<Int, Metric>,
        id: Int,
        status: Status,
        counts: Boolean,
        defaultConfig: String,
        howto: String,
    ): DomainScore {
        val m = ssl[id] ?: return notMeasured(id, "SSL/Python domain — $howto")
        return domain(id, m.value, status, counts, m.config.ifBlank { defaultConfig })
    }

    private fun fmt(v: Double) = String.format(Locale.US, "%.1f", v)

    /** Replicates `SimReport`'s ambient proxy: enroll a small-vocab speaker's words, scan a synthetic stream. */
    private fun measureAmbient(root: File): Double? {
        val spk = TorgoCorpus.scan(root, mic, minReps)
            .filter { it.commandCount in 2..SLICE_MAX }
            .minByOrNull { it.commandCount } ?: return null
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val enrollSamples = spk.commands.flatMap { (word, utts) ->
            utts.map { EnrollmentSample(CommandId(word), WavFile.read(it.wav)) }
        }
        val templates = evaluator.enroll(Corpus(enrollSamples, emptyList())).templates
        val oov = spk.negatives.map { WavFile.read(it.wav) }
        if (oov.isEmpty()) return null
        val rows = TorgoEval(frontEnd, k, minReps, mic, matcherConfig).rowsBySpeaker(root)
            .firstOrNull { it.first == spk.id }?.second ?: emptyList()
        val threshold = RejectionEval(target).operatingThreshold(rows, RejectionScore.RawDistance)
        val ambient = AmbientFar(frontEnd, matcherConfig)
        val stream = ambient.buildStream(oov, gapMs = 400, noiseSnrDb = 20.0, seed = 1)
        return ambient.measure(templates, stream, threshold, synthetic = true).faPerHour
    }

    // ---- SSL metrics bridge (key=value; `domainN_value=`, `domainN_config=`) ----

    private data class Metric(val value: Double, val config: String)

    private fun readMetrics(file: File): Map<Int, Metric> {
        val values = HashMap<Int, Double>()
        val configs = HashMap<Int, String>()
        val keyPattern = Regex("""domain(\d+)_(value|config)""")
        file.readLines()
            .map { it.trim() }
            .filter { it.isNotEmpty() && !it.startsWith("#") && it.indexOf('=') > 0 }
            .forEach { line ->
                val eq = line.indexOf('=')
                val m = keyPattern.matchEntire(line.substring(0, eq).trim())
                if (m != null) {
                    val id = m.groupValues[1].toInt()
                    val v = line.substring(eq + 1).trim()
                    if (m.groupValues[2] == "value") v.toDoubleOrNull()?.let { values[id] = it } else configs[id] = v
                }
            }
        return values.mapValues { (id, v) -> Metric(v, configs[id] ?: "") }
    }

    // ---- rendering ----

    fun renderMarkdown(sc: Scorecard): String = buildString {
        appendLine("# SpeechAngel — Automated SOTA Scorecard (${sc.corpus})")
        appendLine()
        appendLine("Generated by `SotaScorecard` (`core:eval`) — measured performance mapped to the 15-domain")
        appendLine("`SOTA=1000` band ladder (`DomainBands`). **Real speech; any acoustic condition is a")
        appendLine("SIMULATED channel — a probe, NOT a field far-field recording.** Ambient FA/hr is a")
        appendLine("SYNTHETIC in-regime proxy (real OOV speech + silence gaps + 20 dB noise), optimistically")
        appendLine("biased. **SIMULATED_DEVICE** domains (latency/battery) are host-measured then device-scaled")
        appendLine("or first-principles-derived — displayed and banded but **excluded from the composite** so a")
        appendLine("modelled number can never set the wall (as are LOW_FIDELITY/confounded domains). NOT MEASURED")
        appendLine("means no real measurement exists on this host — never a guessed band.")
        appendLine()
        appendLine("## Headline — wall-dominated composite: **${sc.bindingLabel}**")
        appendLine()
        val binding = sc.bindingDomains.joinToString(", ") { "D${it.id} ${it.name}" }
        appendLine("The composite is the **minimum** band over the shipped-system domains (never a mean). It is")
        appendLine("bound by: **$binding**. Measured over ${sc.compositeDomains.size} shipped-system domains;")
        appendLine("the unmeasured domains (real-ambient, language, on-device latency/battery) are the known-weak")
        appendLine("axes, so the true binding band can only be **equal or lower** — this composite is")
        appendLine("**optimistically biased**.")
        appendLine()
        appendLine("| # | Domain | Value | Band | Status | In composite | Provenance |")
        appendLine("|---|--------|------:|:----:|--------|:-----------:|------------|")
        for (d in sc.domains) {
            val value = d.value?.let { formatValue(d.id, it) } ?: "—"
            val band = if (d.status == Status.NOT_MEASURED) "—" else DomainBands.bandLabel(d.band)
            val inComp = if (d.countsForComposite && d.status != Status.NOT_MEASURED) "✓" else "—"
            appendLine("| ${d.id} | ${d.name} | $value | $band | ${d.status} | $inComp | ${d.config} |")
        }
        appendLine()
        val notMeasured = sc.domains.count { it.status == Status.NOT_MEASURED }
        appendLine(
            "**Coverage:** ${sc.measured.size}/15 domains measured on this host " +
                "(${sc.compositeDomains.size} shipped-system in the composite); $notMeasured NOT MEASURED.",
        )
        appendLine()
    }

    fun renderJson(sc: Scorecard): String = buildString {
        appendLine("{")
        appendLine("  \"corpus\": \"${sc.corpus}\",")
        appendLine("  \"compositeRule\": \"wall-dominated (minimum band over shipped-system measured domains)\",")
        appendLine("  \"bindingBand\": \"${sc.bindingLabel}\",")
        appendLine("  \"measuredCount\": ${sc.measured.size},")
        appendLine("  \"compositeCount\": ${sc.compositeDomains.size},")
        appendLine("  \"optimisticallyBiased\": true,")
        appendLine("  \"domains\": [")
        sc.domains.forEachIndexed { i, d ->
            val value = d.value?.let { String.format(Locale.US, "%.4f", it) } ?: "null"
            val band = if (d.status == Status.NOT_MEASURED) "null" else "\"${DomainBands.bandLabel(d.band)}\""
            val comma = if (i == sc.domains.lastIndex) "" else ","
            appendLine(
                "    {\"id\": ${d.id}, \"name\": \"${d.name}\", \"value\": $value, \"band\": $band, " +
                    "\"status\": \"${d.status}\", \"countsForComposite\": ${d.countsForComposite}, " +
                    "\"config\": \"${d.config.replace("\"", "'")}\"}$comma",
            )
        }
        appendLine("  ]")
        appendLine("}")
    }

    private fun formatValue(id: Int, v: Double): String = when (DomainBands.spec(id).unit) {
        "fraction" -> String.format(Locale.US, "%.1f%%", v * 100)
        "per_hour" -> String.format(Locale.US, "%.1f/hr", v)
        "ms" -> String.format(Locale.US, "%.0f ms", v)
        "percent_per_hour" -> String.format(Locale.US, "%.1f%%/hr", v)
        "pp_delta" -> String.format(Locale.US, "Δ%.1f pp", v)
        "count_of_5" -> String.format(Locale.US, "%.0f/5", v)
        else -> String.format(Locale.US, "%.3f", v)
    }

    private fun pct(v: Double) = String.format(Locale.US, "%.1f%%", v * 100)

    private companion object {
        const val SLICE_MAX = 25 // deployment-slice vocabulary cutoff (matches SimReport/ConditionEval).
    }
}
