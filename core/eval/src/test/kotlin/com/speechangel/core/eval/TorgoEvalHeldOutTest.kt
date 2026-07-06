package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.dsp.DeltaOrder
import com.speechangel.core.dsp.NoiseReduction
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import org.junit.Test

/**
 * Corpus-absent, deterministic tests for the EVAL-002 held-out threshold machinery in [TorgoEval] and
 * [ThresholdCalibrator.calibrateFromRows]. These run on every host (no TORGO), pinning the honesty
 * properties: no fold is calibrated on its own rows, and per-command falls back to accept-all where a
 * command has no training negative.
 */
class TorgoEvalHeldOutTest {

    private val A = CommandId("A")
    private val B = CommandId("B")

    private fun row(truth: CommandId?, best: Map<CommandId, Float>, fold: Int) =
        DistanceRow(truth, VoiceCondition.NORMAL, durationMs = 1000, bestByCommand = best, fold = fold)

    // ---- calibrateFromRows (held-out entry point) ---------------------------------------------------

    @Test
    fun `calibrateFromRows falls back to accept-all for a command with no negatives`() {
        val calib = ThresholdCalibrator(FeatureFrontEnd("t", com.speechangel.core.dsp.MfccConfig()))
        // All negatives are won by A; B never wins a negative. maxObserved over all rows = 30.
        val rows = listOf(
            row(A, mapOf(A to 5f, B to 30f), fold = 0), // positive A
            row(B, mapOf(A to 25f, B to 6f), fold = 0), // positive B
            row(null, mapOf(A to 10f), fold = 0), // OOV won by A
            row(null, mapOf(A to 12f), fold = 0), // OOV won by A
        )
        val thr = calib.calibrateFromRows(rows, listOf(A, B), budgetFa = 2)
        val maxObserved = 30f
        // B has no constraining negative → accept-all fallback (> maxObserved).
        assertThat(thr.getValue(B)).isGreaterThan(maxObserved)
        // A is constrained by its 2 negatives (10, 12); with allowance ≥1 the threshold sits among them.
        assertThat(thr.getValue(A)).isLessThan(maxObserved)
    }

    // ---- fitGlobal picks the largest train threshold within the FAR budget --------------------------

    @Test
    fun `fitGlobal returns the largest candidate whose train FAR is within target`() {
        val eval = TorgoEval()
        val train = listOf(
            row(A, mapOf(A to 5f), fold = 0),
            row(A, mapOf(A to 15f), fold = 1),
            row(null, mapOf(A to 10f), fold = 0),
            row(null, mapOf(A to 20f), fold = 1),
            row(null, mapOf(A to 30f), fold = 2),
        )
        // 3 negatives at {10,20,30}; target 0.34 allows 1 accepted. Largest candidate accepting ≤1 neg = 15.
        val thr = eval.fitGlobal(train, listOf(A), target = 0.34)
        assertThat(thr.getValue(A)).isEqualTo(15f)
        assertThat(eval.farOf(train, thr)).isWithin(1e-9).of(1.0 / 3.0)
    }

    // ---- heldOut never calibrates a fold on its own rows --------------------------------------------

    @Test
    fun `heldOut sets a fold's threshold from the OTHER folds, not its own negatives`() {
        val eval = TorgoEval()
        // Fold 0's OOV (dist 8) is CLOSER than its positive (dist 10). If fold 0 were calibrated on
        // itself at target 0, its threshold would drop below 8 and reject its own positive → FAR 0.
        // Held-out, fold 0 is scored with fold 1's threshold (fold 1's only negative is far away at 100),
        // so the threshold is ~10 and fold 0's dist-8 OOV IS accepted → FAR > 0 proves no self-calibration.
        val rows = listOf(
            row(A, mapOf(A to 10f), fold = 0),
            row(null, mapOf(A to 8f), fold = 0),
            row(A, mapOf(A to 10f), fold = 1),
            row(null, mapOf(A to 100f), fold = 1),
        )
        val point = eval.heldOut(rows) { train -> eval.fitGlobal(train, listOf(A), target = 0.0) }
        // Held-out FAR is 0.5 (fold 0's OOV accepted); an in-sample fit would have made it 0.0.
        assertThat(point.far).isWithin(1e-9).of(0.5)
    }

    // ---- front-end grid winner obeys the stated prior (ties → simpler) ------------------------------

    @Test
    fun `renderFrontEndGrid picks the simpler front-end on a rank-1 tie`() {
        val eval = TorgoEval()
        val cells = listOf(
            TorgoEval.GridCell("none", DeltaOrder.NONE, NoiseReduction.NONE, rank1 = 0.70, perSpeaker = listOf("F01" to 0.70)),
            TorgoEval.GridCell(
                "delta_delta",
                DeltaOrder.DELTA_DELTA,
                NoiseReduction.NONE,
                rank1 = 0.70,
                perSpeaker = listOf("F01" to 0.70),
            ),
        )
        val md = eval.renderFrontEndGrid(cells)
        // On a tie the simpler (fewer deltas) front-end wins.
        assertThat(md).contains("`none` at 70.0%")
        assertThat(md).contains("optimistically selected")
    }
}
