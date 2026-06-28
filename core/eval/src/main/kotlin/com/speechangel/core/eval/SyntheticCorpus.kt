package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.model.AudioSamples
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import kotlin.math.PI
import kotlin.math.sin
import kotlin.random.Random

/**
 * A deterministic synthetic corpus for exercising the harness end to end. Signals are **silence-padded**
 * (so the energy VAD can estimate a noise floor and endpoint — a bare steady tone would be trimmed to
 * nothing) and **time-varying** frequency sweeps (so Δ/ΔΔ features carry information, making the bake-off
 * non-vacuous). It is illustrative only — never a substitute for a real, labeled, multi-voice corpus.
 */
object SyntheticCorpus {

    private const val SR = 16_000
    private const val TONE_MS = 400
    private const val PAD_MS = 200

    /** A linear frequency sweep `f0→f1` with deterministic low-level jitter, silence-padded. */
    private fun sweepUtterance(f0: Double, f1: Double, amp: Double, jitter: Double, seed: Int): AudioSamples {
        val n = SR * TONE_MS / 1000
        val rnd = Random(seed)
        val tone = FloatArray(n) { i ->
            val frac = i.toDouble() / n
            val f = f0 + (f1 - f0) * frac
            val t = i.toDouble() / SR
            // tone + quieter octave gives MFCC a clearer envelope; tiny jitter de-aliases templates.
            val v = amp * sin(2.0 * PI * f * t) + 0.15 * amp * sin(2.0 * PI * 2 * f * t)
            (v + jitter * (rnd.nextDouble() - 0.5)).toFloat()
        }
        val pad = FloatArray(SR * PAD_MS / 1000)
        return AudioSamples(pad + tone + pad, SR)
    }

    private fun noiseUtterance(amp: Double, seed: Int): AudioSamples {
        val n = SR * TONE_MS / 1000
        val rnd = Random(seed)
        val tone = FloatArray(n) { (amp * (rnd.nextDouble() * 2 - 1)).toFloat() }
        val pad = FloatArray(SR * PAD_MS / 1000)
        return AudioSamples(pad + tone + pad, SR)
    }

    // Three acoustically distinct command "words" defined by their sweep shape.
    private data class Spec(val id: String, val f0: Double, val f1: Double)
    private val SPECS = listOf(
        Spec("up_low", 300.0, 800.0),
        Spec("down_high", 1100.0, 500.0),
        Spec("up_high", 600.0, 1600.0),
    )

    fun build(): Corpus {
        val enrollment = ArrayList<EnrollmentSample>()
        val utterances = ArrayList<LabeledUtterance>()
        var seed = 1

        for (spec in SPECS) {
            val cmd = CommandId(spec.id)
            // 2 NORMAL enrollment recordings per command.
            repeat(2) {
                enrollment += EnrollmentSample(cmd, sweepUtterance(spec.f0, spec.f1, 0.3, 0.01, seed++), VoiceCondition.NORMAL)
            }
            // 3 NORMAL positives + 1 TIRED (lower amplitude, slight pitch droop) positive.
            repeat(3) {
                utterances += LabeledUtterance(sweepUtterance(spec.f0, spec.f1, 0.3, 0.02, seed++), cmd, VoiceCondition.NORMAL)
            }
            utterances += LabeledUtterance(
                sweepUtterance(spec.f0 * 0.95, spec.f1 * 0.95, 0.22, 0.02, seed++),
                cmd,
                VoiceCondition.TIRED,
            )
        }

        // Negatives: noise bursts + off-target sweeps that match no enrolled command.
        repeat(6) { utterances += LabeledUtterance(noiseUtterance(0.25, seed++), truth = null) }
        repeat(4) { utterances += LabeledUtterance(sweepUtterance(2000.0, 2400.0, 0.3, 0.02, seed++), truth = null) }

        return Corpus(enrollment, utterances)
    }

    /** The three MFCC front-ends compared in the bake-off. */
    fun frontEnds(): List<FeatureFrontEnd> = listOf(
        FeatureFrontEnd("static", MfccConfig(deltaOrder = DeltaOrder.NONE)),
        FeatureFrontEnd("delta", MfccConfig(deltaOrder = DeltaOrder.DELTA)),
        FeatureFrontEnd("delta_delta", MfccConfig(deltaOrder = DeltaOrder.DELTA_DELTA)),
    )
}
