package com.speechangel.core.eval

/**
 * Machine-readable SOTA domain-band **thresholds** — the single source of truth for the 15-domain
 * `SOTA=1000` ladder documented in `docs/product/2026-07-08_sota-wake-word-reference.md` §11 and
 * `docs/product/2026-07-08_sota-domain-bands.md`. [SotaScorecard] maps measured values to bands against
 * these; the doc's hand-typed "Current band" column should agree (a future consistency guardrail can
 * enforce equality — see the scorecard plan).
 *
 * ## Composite rule — WALL-DOMINATED, never a mean
 * The composite is the **minimum** band over measured performance domains, not their average: one `<600`
 * wall (e.g. ambient FA/hr) blocks deployment regardless of how strong the other domains are. A mean
 * would report ~650–700 while the product is `<600`-blocked — the exact inflation this project's EVAL
 * discipline exists to prevent.
 */
object DomainBands {
    enum class Direction { HIGHER_BETTER, LOWER_BETTER }

    /** Band score below the 600 floor. Sorts lowest so it dominates the wall-dominated composite. */
    const val BELOW_FLOOR: Int = 500

    /**
     * One domain's band thresholds. [cutoffs] are `(bandScore, threshold)` pairs; a measured value earns
     * the highest band whose threshold it satisfies (≥ for [Direction.HIGHER_BETTER], ≤ for
     * [Direction.LOWER_BETTER]). Some domains have no 600 rung (their ladder starts at 700).
     */
    data class Spec(val id: Int, val name: String, val unit: String, val direction: Direction, val cutoffs: List<Pair<Int, Double>>)

    /**
     * The 15 domains, transcribed verbatim from the "Composite SOTA band map" in
     * `docs/product/2026-07-08_sota-domain-bands.md`. Fractions are 0–1 (rank-1, FRR, detection); FA/hr is
     * an absolute per-hour count; latency is ms; battery is %/hr; language is a percentage-point delta;
     * guardrail coverage is a count out of 5.
     */
    val specs: List<Spec> = listOf(
        Spec(
            1,
            "Closed-set rank-1",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.55, 700 to 0.65, 800 to 0.75, 900 to 0.85, 950 to 0.90, 1000 to 0.95),
        ),
        Spec(
            2,
            "FRR @ FAR≤5% (held-out)",
            "fraction",
            Direction.LOWER_BETTER,
            listOf(600 to 0.55, 700 to 0.35, 800 to 0.15, 900 to 0.05, 950 to 0.02, 1000 to 0.005),
        ),
        Spec(
            3,
            "Ambient FA/hr",
            "per_hour",
            Direction.LOWER_BETTER,
            listOf(600 to 5.0, 700 to 2.0, 800 to 0.5, 900 to 0.1, 950 to 0.05, 1000 to 0.01),
        ),
        Spec(
            4,
            "Noise robustness @ 20 dB",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.55, 700 to 0.60, 800 to 0.70, 900 to 0.80, 950 to 0.85, 1000 to 0.95),
        ),
        Spec(
            5,
            "Reverb robustness",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(700 to 0.65, 800 to 0.75, 900 to 0.85, 950 to 0.90, 1000 to 0.95),
        ),
        Spec(
            6,
            "Bandwidth robustness",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(700 to 0.65, 800 to 0.75, 900 to 0.85, 950 to 0.90, 1000 to 0.95),
        ),
        Spec(
            7,
            "Wake detection @ ≤0.5 FA/hr",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.50, 700 to 0.65, 800 to 0.75, 900 to 0.85, 950 to 0.90, 1000 to 0.95),
        ),
        Spec(
            8,
            "Dual-cascade rejection (rel FRR reduction)",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.10, 700 to 0.20, 800 to 0.30, 900 to 0.40, 950 to 0.50, 1000 to 0.60),
        ),
        Spec(
            9,
            "SSL embedding quality (rank-1)",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.60, 700 to 0.65, 800 to 0.70, 900 to 0.75, 950 to 0.80, 1000 to 0.85),
        ),
        Spec(
            10,
            "Language independence (rank-1 Δ vs English)",
            "pp_delta",
            Direction.LOWER_BETTER,
            listOf(700 to 30.0, 800 to 20.0, 900 to 15.0, 950 to 10.0, 1000 to 5.0),
        ),
        Spec(
            11,
            "Latency (P50)",
            "ms",
            Direction.LOWER_BETTER,
            listOf(600 to 1000.0, 700 to 500.0, 800 to 200.0, 900 to 150.0, 950 to 100.0, 1000 to 50.0),
        ),
        Spec(
            12,
            "Battery / resource per hour",
            "percent_per_hour",
            Direction.LOWER_BETTER,
            listOf(600 to 30.0, 700 to 20.0, 800 to 12.0, 900 to 8.0, 950 to 5.0, 1000 to 2.0),
        ),
        Spec(
            13,
            "Enrollment efficiency",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.60, 700 to 0.70, 800 to 0.80, 900 to 0.85, 950 to 0.90, 1000 to 1.00),
        ),
        Spec(
            14,
            "Vocab-size scaling",
            "fraction",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.50, 700 to 0.60, 800 to 0.70, 900 to 0.80, 950 to 0.90, 1000 to 0.90),
        ),
        Spec(
            15,
            "Guardrail coverage",
            "count_of_5",
            Direction.HIGHER_BETTER,
            listOf(600 to 0.0, 700 to 1.0, 800 to 2.0, 900 to 3.0, 950 to 4.0, 1000 to 5.0),
        ),
    )

    fun spec(id: Int): Spec = specs.first { it.id == id }

    /** Highest band whose threshold the [value] satisfies, or [BELOW_FLOOR] if it clears none. */
    fun bandFor(spec: Spec, value: Double): Int {
        var best = BELOW_FLOOR
        for ((score, thr) in spec.cutoffs) {
            val meets = when (spec.direction) {
                Direction.HIGHER_BETTER -> value >= thr
                Direction.LOWER_BETTER -> value <= thr
            }
            if (meets && score > best) best = score
        }
        return best
    }

    fun bandFor(domainId: Int, value: Double): Int = bandFor(spec(domainId), value)

    fun bandLabel(score: Int): String = if (score <= BELOW_FLOOR) "<600" else score.toString()
}
