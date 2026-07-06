package com.speechangel.core.eval

import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.MfccConfig
import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId
import java.io.File

/**
 * Orchestrates the realistic-condition + rejection-scoring evaluation into one markdown report on real
 * TORGO, on the **shipped** static-MFCC front-end (`deltaOrder=NONE`) — not `TorgoEval`'s `delta_delta`
 * default — so every number is for the config the product actually ships.
 *
 * Sections: (1) the pre-registered common-mode rejection adjudication (McNemar vs baseline) + exploratory
 * family; (2) the realistic-condition grid (real speech, simulated channel); (3) the ambient FAR/hour
 * proxy. See `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`.
 */
class SimReport(
    private val frontEnd: FeatureFrontEnd = FeatureFrontEnd("none", MfccConfig(deltaOrder = DeltaOrder.NONE)),
    private val k: Int = 5,
    private val minReps: Int = 2,
    private val mic: String = "wav_headMic",
    private val target: Double = 0.05,
    private val matcherConfig: MatcherConfig = MatcherConfig(),
    private val sliceMaxCommands: Int = 25,
) {
    fun render(root: File, runConditions: Boolean = false, ambientWav: File? = null): String = buildString {
        val corpus = root.name
        val torgo = TorgoEval(frontEnd, k, minReps, mic, matcherConfig)
        val bySpeaker = torgo.rowsBySpeaker(root)
        val rejection = RejectionEval(target)

        appendLine("# Realistic-condition simulation + rejection scoring — TORGO ($corpus)")
        appendLine()
        appendLine("Front-end: `${frontEnd.name}` (the **shipped** default `deltaOrder=NONE`). Held-out")
        appendLine("(leave-one-fold-out), matched FAR. Real speech; any acoustic condition below is a")
        appendLine("**simulated channel** — a probe, not a field far-field recording.")
        appendLine()

        // (1) Pre-registered rejection adjudication.
        val mc = rejection.mcNemar(bySpeaker, RejectionScore.RawDistance, RejectionScore.CommonMode)
        val family = rejection.family(
            bySpeaker,
            listOf(RejectionScore.RawDistance, RejectionScore.CommonMode, RejectionScore.margin(), RejectionScore.Ratio),
        )
        append(rejection.render(mc, family, corpus))

        // (2) Realistic-condition grid (opt-in — expensive, one full k-fold pass per condition).
        if (runConditions) {
            val ce = ConditionEval(frontEnd, k, minReps, mic, target, matcherConfig)
            append(ce.render(ce.run(root), corpus))
        }

        // (3) Ambient FAR/hour proxy on a small-vocab (deployment-slice) speaker.
        append(ambientSection(root, bySpeaker, rejection, ambientWav))
    }

    private fun ambientSection(
        root: File,
        bySpeaker: List<Pair<String, List<DistanceRow>>>,
        rejection: RejectionEval,
        ambientWav: File?,
    ): String {
        val speakers = TorgoCorpus.scan(root, mic, minReps)
            .filter { it.commandCount in 2..sliceMaxCommands }
            .sortedBy { it.commandCount }
        val spk = speakers.firstOrNull() ?: return "## Ambient FAR/hour proxy\n\n_No deployment-slice speaker available._\n"

        // Enroll ALL of this speaker's command utterances as templates (clean).
        val evaluator = Evaluator(frontEnd, matcherConfig)
        val enrollSamples = spk.commands.flatMap { (word, utts) ->
            utts.map { EnrollmentSample(CommandId(word), WavFile.read(it.wav)) }
        }
        val templates = evaluator.enroll(Corpus(enrollSamples, emptyList())).templates
        val oov = spk.negatives.map { WavFile.read(it.wav) }

        val ambient = AmbientFar(frontEnd, matcherConfig)
        val rows = bySpeaker.firstOrNull { it.first == spk.id }?.second ?: emptyList()
        // Operating point: raw threshold calibrated to ≤ target per-utterance OOV FAR (in-sample, for the proxy).
        val threshold = rejection.operatingThreshold(rows, RejectionScore.RawDistance)

        val (stream, synthetic) = if (ambientWav != null && ambientWav.isFile) {
            WavFile.read(ambientWav) to false
        } else {
            ambient.buildStream(oov, gapMs = 400, noiseSnrDb = 20.0, seed = 1) to true
        }
        val result = ambient.measure(templates, stream, threshold, synthetic)
        return "_(ambient speaker: `${spk.id}`, ${spk.commandCount} commands)_\n\n" + ambient.render(result, root.name)
    }
}
