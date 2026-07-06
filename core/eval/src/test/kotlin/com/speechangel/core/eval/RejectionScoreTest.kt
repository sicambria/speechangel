package com.speechangel.core.eval

import com.google.common.truth.Truth.assertThat
import com.speechangel.core.model.CommandId
import com.speechangel.core.model.VoiceCondition
import org.junit.Test

class RejectionScoreTest {

    private val a = CommandId("A")
    private val b = CommandId("B")
    private fun row(truth: CommandId?, fold: Int, vararg d: Pair<CommandId, Float>) =
        DistanceRow(truth, VoiceCondition.NORMAL, 700, d.toMap(), fold)

    @Test
    fun `common-mode differs from raw and is not a no-op`() {
        // Winner A at d1=7 (far from everything today) but distinctly closer to A than B.
        val r = row(a, 0, a to 7.0f, b to 12.0f)
        assertThat(RejectionScore.RawDistance.score(r)).isEqualTo(7.0f)
        // common-mode = d1 - median(others) = 7 - 12 = -5  → a different, lower score.
        assertThat(RejectionScore.CommonMode.score(r)).isEqualTo(-5.0f)
    }

    @Test
    fun `winner command is identical across scorers (rank-1 invariant)`() {
        val rows = listOf(
            row(a, 0, a to 7.0f, b to 12.0f),
            row(b, 0, a to 9.0f, b to 3.0f),
            row(null, 0, a to 6.5f, b to 6.8f),
        )
        for (r in rows) {
            val w = RejectionScore.winnerCommand(r)
            // Every scorer keeps argmin d1 as the winner; only the accept/reject score changes.
            assertThat(w).isEqualTo(r.bestByCommand.minByOrNull { it.value }!!.key)
        }
    }

    @Test
    fun `common-mode separates far-from-everything positives that raw distance cannot`() {
        // Positives are FAR (d1=7) but distinctive (other=12). OOV negatives are CLOSER (d1=6.5) but
        // ambiguous (other=6.8). Raw distance cannot separate (positive d1 > negative d1); common-mode
        // can (positive score -5 << negative score -0.3).
        val rows = ArrayList<DistanceRow>()
        for (fold in 0..1) {
            repeat(6) { rows += row(a, fold, a to 7.0f, b to 12.0f) }
            repeat(6) { rows += row(b, fold, a to 12.0f, b to 7.0f) }
            repeat(6) { rows += row(null, fold, a to 6.5f, b to 6.8f) }
            repeat(6) { rows += row(null, fold, a to 6.8f, b to 6.5f) }
        }
        val bySpeaker = listOf("spk" to rows)
        val eval = RejectionEval(target = 0.05)

        val raw = eval.pooled(bySpeaker, RejectionScore.RawDistance)
        val cm = eval.pooled(bySpeaker, RejectionScore.CommonMode)
        // Raw is forced to reject the positives to hold FAR (their d1 exceeds the negatives' d1).
        assertThat(raw.frr).isGreaterThan(0.9)
        // Common-mode accepts them while still rejecting the ambiguous OOV.
        assertThat(cm.frr).isLessThan(0.1)
        assertThat(cm.far).isAtMost(0.05)

        val mc = eval.mcNemar(bySpeaker, RejectionScore.RawDistance, RejectionScore.CommonMode)
        assertThat(mc.n01).isGreaterThan(mc.n10) // hypothesis rescues more than it regresses
        assertThat(mc.significantAt05).isTrue()
        assertThat(mc.direction).isEqualTo("hypothesis better")
    }

    @Test
    fun `identical scorers yield a null McNemar result (no discordance)`() {
        val rows = (0..1).flatMap { fold ->
            listOf(row(a, fold, a to 3.0f, b to 9.0f), row(null, fold, a to 20.0f, b to 21.0f))
        }
        val mc = RejectionEval(target = 0.5).mcNemar(listOf("s" to rows), RejectionScore.RawDistance, RejectionScore.RawDistance)
        assertThat(mc.n01).isEqualTo(0)
        assertThat(mc.n10).isEqualTo(0)
        assertThat(mc.significantAt05).isFalse()
    }
}
