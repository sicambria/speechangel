# Plan: CP-2 per-template calibration spike

- **Date:** 2026-07-07
- **Phase:** CP-2 (deployability)
- **Roadmap item:** Per-template/per-word threshold calibration or dedicated rejection model
- **Status:** done  <!-- 2026-07-07: H1 REFUTED — per-template calibration is a significant regression. See docs/testing/2026-07-07_cp2-per-template-calibration.md -->
- **Worktree:** n/a (docs-only + Python spike)
- **Plan quality:** 94/100 (self-scored; measurement-only, no feature build)

## Goal

Test whether per-template (per-word) distance thresholds reduce false-reject rate (FRR) at matched
≤0.5 FA/hr by ≥30% relative vs the global-threshold baseline on WavLM-L12 pooled-cosine embeddings,
recovering the rank-1 headroom the CP-2 spike identified (rank-1 84.4% vs gate detection 75.0% on F01).
Pre-register ONE hypothesis; label everything else as exploratory NOT-banked family.

## Context & Constraints

- **Binding axis:** FA/hour on continuous ambient audio (not per-utterance OOV FAR). CP-2 spike
  (`docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md`) showed no arm clears the deployable bar
  (best FRR 25% at 0.5 FA/hr, need <5%).
- **The identifed gap:** WavLM F01 has 9-pt slack between rank-1 (84.4%) and gate detection at ~0
  FA/hr (75.0%) — global-threshold calibration cannot recover this because a single threshold for
  all words is dominated by the permissive (high-variance) words that cause background FAs.
  MFCC has zero slack (rank-1 = gate detection) — per-template calibration only makes sense with
  the WavLM embedding.
- **Constraint-preserving:** Per-template calibration is a thresholding strategy, not a model change.
  Language-independence + 1-shot enrollment intact. No new dependencies.
- **Fidelity gate (EVAL-004):** Must reproduce the committed CP-2 WavLM global-threshold results
  to the decimal before trusting any per-template delta.
- **EVAL-003 discipline:** Pre-register H1; rest is NOT-banked family. McNemar at matched FAR.
- **EVAL-005 discipline:** Require ≥2 speakers agreeing in direction for extreme operating points.
  Prefer curve-area summary.

## Approach

Per-template calibration: each enrolled word gets its own distance threshold θ_w = α × median(in-class
cosine distances among its own templates). The single global parameter α is swept to produce the
detection vs FA/hr curve. The hypothesis is that words with tight intra-class similarity can use
much stricter thresholds (rejecting more background) while words with high intra-class variance get
looser thresholds (accepting their genuine queries), improving the aggregate detection vs FA/hr
trade-off compared to a single one-size-fits-all global threshold.

**Rejected alternatives:**
- Percentile-based thresholds (θ_w = p-th percentile of in-class distances): equivalent to α-sweep
  but with a less interpretable parameter; α × median is simpler and directly comparable.
- Leave-one-fold-out threshold calibration per word: adds complexity but the problem is not
  overfitting (thresholds are calibrated on in-class data, not OOV data); the α sweep on all
  templates is the cleanest and fastest measurement.

**Modules touched:** `scripts/eval/ssl_frontend_spike/per_template_cal.py` (new, measure-only).

## Steps

1. **Write `per_template_cal.py`** — extends the `in_regime.py`/`inregime_paired.py` protocol:
   - Load TORGO via `harness.scan()`, compute WavLM-L12 pooled-cosine embeddings once.
   - Load LibriSpeech background (≥1 h), pre-compute embeddings for all windows.
   - For per-template arm: compute per-word in-class distance distributions,
     set θ_w(α) = α × median(in_class_dists_w), sweep α.
   - For global baseline arm: sweep single θ_global.
   - Report FRR @ 0.5 FA/hr, FRR @ 1.0 FA/hr, FA/hr for 95% detection.
   - Paired McNemar (continuity-corrected) + exact two-sided binomial at matched ≤0.5 FA/hr.
   - **Fidelity check:** global baseline must reproduce `in_regime.py` WavLM F01 results
     (det 75.0% @ ~0 FA/hr, det 96.9% @ 5 FA/hr) to within sampling tolerance.
2. **Exploratory family (NOT-banked):**
   - `margin` scorer (best - gap_to_second) combined with per-template thresholds.
   - Multi-template enrollment (test 2/3/5 templates per word vs single).
3. **Run spike**, collect results, adjudicate significance.
4. **Write testing report** `docs/testing/2026-07-07_cp2-per-template-calibration.md`.
5. **Update** `ACTIVE_DEV_RULES.md` if a new rule is warranted; `docs/plans/INDEX.md` with result.

## Definition of Done

- [x] **Fidelity gate:** Global baseline reproduces committed CP-2 WavLM F01 numbers to the decimal.
- [x] **H1 REFUTED:** McNemar at matched ≤0.5 FA/hr (FAR budget) — per-template calibration is a significant
  REGRESSION on all 3 speakers (aggregate p<0.0001, discordant 94:6). Honest negative.
- [x] **FRR FAR reported:** FRR 25.0%→56.2% (F01), 53.5%→89.7% (F03), 54.0%→76.0% (F04) at matched
  FAR ≤0.5 FA/hr. Significant regression on all speakers.
- [x] **Honest negative documented:** Mechanism identified — in-class distances underestimate
  cross-session query-template distances by 2–5×, making per-word thresholds systematically too strict.
- [x] **Testing report** `docs/testing/2026-07-07_cp2-per-template-calibration.md` with full results,
  significance, per-speaker breakdown, mechanism analysis, what-is-banked, next levers.
- [x] **NOT-banked family table** — margin scorer also worse (F01 FRR 59.4% vs 25.0%).
- [x] **McNemar** includes exact two-sided binomial for small discordant counts.
- [ ] **No runtime change** to the app; this is `[measure-only]`.

## Risks & Mitigations

- **Risk: Per-template thresholds don't help (H1 falsified).** Mitigation: Honest negative is a
  valid, bankable result — it tells us the CP-2 lever is elsewhere (dedicated rejection model or
  model-level change). Per the journey skill, a refuted hypothesis saves building the wrong thing.
  Rollback: none; spike is measure-only.
- **Risk: Fidelity gap — baseline not reproduced.** Mitigation: Run both arms in the same process
  on identical data; verify global-threshold arm against `in_regime.py` before drawing conclusions.
  If the baseline doesn't match, fix the reproduction first — don't proceed.
- **Risk: Underpowered significance at n≈32 (F01).** Mitigation: Accept that small n limits
  precision; headline the aggregate across speakers; do NOT chase significance with more speakers
  on a small delta (suboptimization per journey skill §11). The test answers the strategic question.
- **Risk: Per-word thresholds overfit to in-class distances (too loose).** Mitigation: The α sweep
  is the control — we measure whatever FA/hr point α produces, not a pre-committed α. No
  threshold-selection bias (EVAL-002).

## Test & Verification

- **Fidelity:** Run `python per_template_cal.py --baseline-only --speaker F01` and verify
  det@~0FA/hr = 75.0% and det@5FA/hr = 96.9% (± 2% sampling tolerance).
- **Spike:** Run `python per_template_cal.py --speakers F01,F03,F04,FC01` on ≥1 h LibriSpeech.
- **Reproducibility:** `python per_template_cal.py` with no args reproduces the committed report.
- **Platform:** `/home/arsvivendi/git/speechangel/research/.venv/bin/python3` (torch 2.12.1,
  transformers 5.13.0); TORGO @ `~/torgo`; LibriSpeech @ `~/picovoice-benchmark/prepared/librispeech/`.
- **Corpus:** `[measure-only]` — never committed. The spike script is committed; data paths are
  host-local.

- **Benchmark impact:** Not applicable (this is a measurement spike for CP-2, not a matcher/DSP
  change). The `make bench-picovoice` output is unchanged.
