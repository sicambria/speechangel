package com.speechangel.core.eval

import com.speechangel.core.matching.MatcherConfig
import com.speechangel.core.model.CommandId

/**
 * Runs the same raw corpus through several feature front-ends and *computes* a comparison table. It
 * reports the numbers; it deliberately does NOT assert which front-end wins — that ranking is the
 * experiment's output, not an invariant (deltas may or may not help on a given corpus).
 */
class FrontEndBakeoff(private val frontEnds: List<FeatureFrontEnd>, private val matcherConfig: MatcherConfig = MatcherConfig()) {
    data class Row(val name: String, val frr: Double, val falseAccepts: Int, val negativeAudioSeconds: Double)

    data class BakeoffReport(val rows: List<Row>, val synthetic: Boolean = true) {
        fun render(): String = buildString {
            if (synthetic) appendLine("> **SYNTHETIC — illustrative comparison, not a real-voice result.**").also { appendLine() }
            appendLine("# Feature front-end bake-off")
            appendLine()
            appendLine("| Front-end | FRR | False accepts | Neg audio (s) |")
            appendLine("|---|---|---|---|")
            for (r in rows) {
                val frrPct = "%.1f%%".format(r.frr * 100)
                val negS = "%.1f".format(r.negativeAudioSeconds)
                appendLine("| `${r.name}` | $frrPct | ${r.falseAccepts} | $negS |")
            }
        }
    }

    fun run(corpus: Corpus, thresholds: Map<CommandId, Float> = emptyMap()): BakeoffReport {
        val rows = frontEnds.map { fe ->
            val r = Evaluator(fe, matcherConfig).evaluate(corpus, thresholds)
            Row(fe.name, r.frr, r.falseAccepts, r.negativeAudioSeconds)
        }
        return BakeoffReport(rows)
    }
}
