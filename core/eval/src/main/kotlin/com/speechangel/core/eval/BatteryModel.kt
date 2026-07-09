package com.speechangel.core.eval

import java.util.Locale

/**
 * **SOTA Domain 12 — always-on battery drain (%/hr).** The domain-bands doc marks this "physical device
 * only." Rather than wait for a device, this is a transparent **first-principles power model**: it
 * consumes the measured device-scaled decide cost from [LatencyEval] (Domain 11) and combines it with
 * named, cited Pixel 6 power/energy constants to estimate active-listening battery drain. Deterministic;
 * every constant is a `const val` with its source; the result carries a ± band because the constants are
 * literature estimates, not a device measurement.
 *
 * Because it is a **derivation, not a measurement**, D12 is `SIMULATED_DEVICE` and **excluded from the
 * wall-dominated composite** — a modelled number must never *set* the reported wall.
 *
 * ## Model
 * ```
 * RTF        = deviceDecideMs / AVG_UTTERANCE_MS          // compute-ms per audio-ms of the decide path
 * duty       = min(1, RTF × SPEECH_DUTY)                  // fraction of wall-clock the big core is busy
 * P_total_W  = P_BASELINE_W + P_ACTIVE_W × duty           // always-on capture/VAD + gated recognition
 * pct/hr     = P_total_W × 1h / BATTERY_WH × 100
 * ```
 * The VAD/capture stage runs continuously and is folded into [P_BASELINE_W]; the expensive MFCC+DTW
 * stage only fires on energy-gated speech-like windows, so its contribution is throttled by [SPEECH_DUTY]
 * (the fraction of household wall-clock that reaches the matcher) and the decide-path [RTF].
 */
class BatteryModel(
    private val baselinePowerW: Double = P_BASELINE_W,
    private val activePowerW: Double = P_ACTIVE_W,
    private val speechDuty: Double = SPEECH_DUTY,
    private val batteryWh: Double = BATTERY_WH,
    private val avgUtteranceMs: Double = AVG_UTTERANCE_MS,
) {
    data class Result(
        val deviceDecideMs: Double,
        val rtf: Double,
        val dutyCycle: Double,
        val totalPowerW: Double,
        val pctPerHour: Double,
        val batteryWh: Double,
    ) {
        /** ± band from the constant uncertainty (see [BatteryModel.UNCERTAINTY]). */
        val pctPerHourLow: Double get() = pctPerHour * (1 - UNCERTAINTY)
        val pctPerHourHigh: Double get() = pctPerHour * (1 + UNCERTAINTY)
    }

    fun estimate(deviceDecideMs: Double): Result {
        val rtf = if (avgUtteranceMs <= 0) 0.0 else deviceDecideMs / avgUtteranceMs
        val duty = (rtf * speechDuty).coerceIn(0.0, 1.0)
        val totalPowerW = baselinePowerW + activePowerW * duty
        val pctPerHour = totalPowerW / batteryWh * 100.0
        return Result(deviceDecideMs, rtf, duty, totalPowerW, pctPerHour, batteryWh)
    }

    /** Human-readable provenance naming every assumption (echoed into the scorecard). */
    fun assumptions(): String = String.format(
        Locale.US,
        "first-principles model: battery %.1f Wh (Pixel 6 4614 mAh × 3.85 V), P_baseline %.2f W " +
            "(always-on CPU capture+VAD), P_active %.2f W (one Tensor big-core busy), speech-duty %.2f, " +
            "avg-utterance %.0f ms; ±%.0f%% band — DERIVATION, not a device measurement",
        batteryWh,
        baselinePowerW,
        activePowerW,
        speechDuty,
        avgUtteranceMs,
        UNCERTAINTY * 100,
    )

    companion object {
        /** Pixel 6: 4614 mAh × 3.85 V nominal ≈ 17.76 Wh (Google published capacity). */
        const val BATTERY_WH: Double = 17.76

        /**
         * Always-on incremental draw of a CPU-based mic-capture + energy-VAD foreground service (no
         * dedicated hotword DSP). Published CPU-based always-on-audio measurements sit at ~0.2–0.5 W;
         * 0.35 W is the mid-estimate.
         */
        const val P_BASELINE_W: Double = 0.35

        /** One Google Tensor Cortex-X1 big core at full load ≈ 2.0 W (published SoC per-core figures). */
        const val P_ACTIVE_W: Double = 2.0

        /** Fraction of household wall-clock containing speech-like audio that reaches the matcher. */
        const val SPEECH_DUTY: Double = 0.15

        /** Typical enrolled-command utterance length. */
        const val AVG_UTTERANCE_MS: Double = 1200.0

        /** Relative uncertainty of the literature constants → the reported ± band. */
        const val UNCERTAINTY: Double = 0.4
    }
}
