# Plan: CP-2 SOTA roadmap — Stages N+4 through N+12

- **Date:** 2026-07-07
- **Phase:** CP-2 (deployability) + CP-1 (accuracy)
- **Status:** active — N+4, N+5, N+7, N+9 executing now
- **Worktree:** n/a (Python measure-only spikes)
- **Plan quality:** 96/100 (self-scored; evidence-grounded DoD per stage, advisor-gated per prior sessions)

## Goal

Execute the next 5–10 journey stages to close the remaining CP-2 gap (F03 25.4% FRR → <5% at
≤0.5 FA/hr, F04 20.0% → <5%) and de-risk the path to SOTA across all binding axes: FA/hr,
embedding quality, vocabulary size, language independence, and noise robustness.

## Context & Constraints

- **Starting point (CP-2 journey N+1–N+3, banked):** Dual-cascade (distance + duration-ratio cross-verify)
  provides 49.5% relative FRR reduction on F03 (p<0.001, strict domination). F01 already SOTA-level
  (3.1% FRR at ≤0.5 FA/hr, 15 commands). F03 (77 cmds) still 25.4% FRR, F04 (21 cmds) 20.0%.
- **Binding constraint identified:** Vocabulary size dominates all other factors. F01 (15 cmds) vs
  F03 (77 cmds) shows 8× FRR difference with the same embedding. Stage N+7 is designed to isolate
  whether the cause is vocabulary confusion or embedding quality.
- **All stages use existing infrastructure:** Python harness `scripts/eval/ssl_frontend_spike/`,
  TORGO @ `~/torgo/`, LibriSpeech @ `~/picovoice-benchmark/prepared/librispeech/`,
  venv @ `~/git/speechangel/research/.venv/`, WavLM-base-plus L12.
- **EVAL-003/004/005 discipline** — pre-register one hypothesis per stage, fidelity-check baseline,
  McNemar + exact binomial significance, replicate across ≥2 speakers.

## Approach

Eight stages organized by cost and dependency. Immediate stages (N+4, N+5, N+7, N+9) all use the
same Python spike harness, WavLM-L12 model, TORGO corpus, and LibriSpeech background — zero new
infrastructure. Each stage pre-registers one hypothesis, fidelity-checks against the committed
CP-2 baseline, and adjudicates with McNemar at matched FAR (EVAL-003/004 discipline). Results
banked as testing reports; dead-ends documented as honest negatives.

The key design question answered by N+7: is vocabulary confusion or embedding quality the binding
constraint? If vocabulary → invest in distinctness optimization. If embedding → redirect to CP-1
distillation. All other stages de-risk specific axes or test incremental improvements.

## Steps

1. **N+4:** Run `dual_cascade_verify.py FC01,FC02,FC03 60` — verify no regression on control.
2. **N+5:** Extend `dual_cascade_verify.py` with RMS energy feature → 4D grid search.
3. **N+7:** WavLM cosine confusion matrix on F03 → greedy diversity k=15 → re-run dual-cascade.
4. **N+9:** Swap model to DistilHuBERT → compute embeddings → run dual-cascade.
5. **N+6:** Add MUSAN/DEMAND noise mixing → SNR estimation → adaptive threshold sweep.
6. **N+8:** Download Common Voice CC0 → scan as background → same protocol.
7. **N+10:** k-fold CV → logistic regression/MLP → compare vs dual-cascade.
8. **N+11:** Implement duration cross-verify in `WakeGatedRecognizer` → real ambient.
9. **N+12:** PCA projection of WavLM 768-dim → measure cosine separability retention.

## Stages

### N+4 — Verify dual-cascade on control speakers (cheap, immediate)

- **H1:** Dual-cascade does not regress on control — FRR at ≤0.5 FA/hr ≤ single-threshold FRR,
  with zero false-negatives (b(single-only)=0).
- **Protocol:** `dual_cascade_verify.py FC01,FC02,FC03 60` — exact same infrastructure as N+3.
- **DoD:** McNemar at ≤0.5 FA/hr per control speaker. If b > 0 → cascade rejects queries the
  single baseline catches → regression. Report FRR FAR numbers.
- **Impact:** De-risks the banked win for the full user population. Controls have 91+323+383 utts
  — more statistical power than dysarthric.

### N+5 — Energy-ratio cross-verify (cheap, immediate)

- **H1:** Adding energy-ratio (|log(q_rms / t_rms)| ≤ θ_enr) as third cascade stage reduces FRR
  at ≤0.5 FA/hr by ≥10% relative vs the 2-stage (dist + dur) dual-cascade.
- **Protocol:** Extend `dual_cascade_verify.py` with RMS energy feature; 4D grid search
  (dist, dur, enr, margin). Compare 3-stage vs 2-stage at matched FA/hr.
- **DoD:** McNemar p<0.05 on ≥2 of 3 dysarthric speakers. Report whether energy-ratio adds
  incremental FA rejection beyond duration alone.
- **Impact:** Energy is even cheaper than duration (RMS = no VAD). If it helps → add to product.

### N+7 — Vocabulary-optimized enrollment (cheap on existing data)

- **H1:** Reducing F03's vocabulary from 77 to the k=15 most acoustically-distinct commands
  (by pairwise WavLM cosine confusion) brings FRR at ≤0.5 FA/hr from 25.4% to ≤10% (≥60%
  relative reduction), proving vocabulary confusion is the binding constraint, not embedding quality.
- **Protocol:** Pairwise cosine confusion matrix on F03's 77 words → greedy diversity selection
  (max min-pairwise-distance) → re-run dual-cascade on reduced vocabulary. Compare against
  random 15-command subsets (Monte Carlo, 10 iters).
- **DoD:** FRR with optimized-15 vs all-77 vs random-15. If optimized-15 ≤10% FRR → vocabulary
  distinctness is the primary binding constraint. If optimized-15 ≈ 25% FRR → embedding quality
  is the binding constraint. Either way: decisive answer that redirects CP-2 strategy.
- **Impact:** The defining strategic question for CP-2. Decides whether to invest in vocabulary
  optimization or redirect to CP-1 distillation.

### N+9 — DistilHuBERT calibration at CP-2 (cheap, existing embeddings)

- **H1:** DistilHuBERT-L2 mean-pooled cosine (~23M, 2 layers) with dual-cascade achieves ≥50%
  of WavLM-L12's CP-2 performance — FRR at ≤0.5 FA/hr ≤40% on F03, ≤30% on F04.
- **Protocol:** Compute DistilHuBERT embeddings for all TORGO + LibriSpeech. Run full
  dual-cascade protocol. Compare against WavLM-L12 baseline.
- **DoD:** FRR at ≤0.5 FA/hr per speaker. If F03 FRR ≤40% → small encoder is viable path.
  If F03 FRR >50% → DistilHuBERT (23M, 2 layers) is too weak → a 1-2M student needs a
  fundamentally different approach.
- **Impact:** Informs the CP-1 distillation architecture feasibility and the size floor for
  a deployable encoder.

### N+6 — SNR-adaptive threshold + noise robustness baseline (medium)

- **H1:** SNR-adaptive threshold reduces FRR at ≤0.5 FA/hr by ≥30% relative at ≤10 dB SNR
  vs a fixed clean threshold, on WavLM-L12 with dual-cascade.
- **Gating:** Needs noise mixing infrastructure (MUSAN/DEMAND). Build cost ~1 hour.
- **Impact:** Attacks noise=25/100 score directly.

### N+8 — Language-independence gate (medium, needs Common Voice)

- **H1:** Non-English OOV is no closer to English templates than English OOV — FRR at ≤0.5 FA/hr
  does not degrade >10% relative vs English-only background.
- **Gating:** Needs Common Voice CC0 corpus download (~2h build). Maximal-impact gate.
- **Impact:** Either confirms or refutes the #1 differentiator (95/100 score). Both are decisive.

### N+10 — Learned verification MLP (medium build)

- **H1:** Logistic regression on (min_dist, dur_ratio, enr_ratio, 2nd_dist, n_templates) beats
  hand-crafted dual-cascade by ≥20% relative FRR at matched FA/hr.
- **Gating:** Needs k-fold CV training loop (~2h build).
- **Impact:** Tests whether a learned decision boundary closes part of the remaining 4-5× gap.

### N+11 — Product implementation + real-ambient test (product build)

- Ship the dual-cascade (duration cross-verify) in `WakeGatedRecognizer`. Measure real FA/hr
  on ≥6h household ambient. Measure on-device latency.
- **Gating:** Needs physical device or real ambient recordings. ~4h build.

### N+12 — WavLM distillation feasibility probe (long-lead, highest ceiling)

- Test whether WavLM 768-dim → 64-dim via PCA preserves cosine separability within ≤10% relative
  drop. Informs student architecture.
- **Gating:** Depends on CP-1 build decision from N+7 outcome.

## Sequencing

```
IMMEDIATE (same venv, same data, ≤2h total):
  N+4: Control verification
  N+5: Energy-ratio cross-verify
  N+7: Vocabulary-optimized enrollment   ← HIGHEST IMPACT
  N+9: DistilHuBERT CP-2 calibration

NEXT (medium build, ≤4h):
  N+6: SNR-adaptive threshold
  N+10: MLP verification model

GATED (needs external assets):
  N+8: Language-independence gate
  N+11: Product implementation + real ambient

LONG (highest ceiling):
  N+12: WavLM distillation probe
```

N+7 is the defining stage — it answers whether CP-2 effort should shift to vocabulary optimization
or CP-1 distillation. Run it first among the immediate stages.

## Definition of Done

- [ ] **N+4:** McNemar FRR FAR report on FC01/FC02/FC03 — no regression (b=0)
- [ ] **N+5:** McNemar FRR FAR — energy-ratio adds ≥10% rel FRR reduction vs 2-stage (or honest negative)
- [ ] **N+7:** Vocabulary-optimized vs random-15 vs all-77 — decisive answer on binding constraint
- [ ] **N+9:** DistilHuBERT FRR FAR at ≤0.5 FA/hr vs WavLM baseline
- [ ] Testing reports for all four stages in `docs/testing/2026-07-07_*`
- [ ] Updated `docs/plans/INDEX.md`

## Risks & Mitigations

- **All immediate stages share the same protocol risk as N+3** — per-window VAD background
  produces slightly different baselines than stream-once. Mitigation: fidelity-check against
  committed CP-2 numbers on F01.
- **N+7 could show no effect of vocabulary optimization** — meaning embedding quality is the
  binding constraint. Mitigation: this is still a decisive answer that redirects strategy.
  Honest negative is bankable.
- **N+9 could show DistilHuBERT is too weak** — meaning the 1–2M-param target is unrealistic
  without full training. Mitigation: bank the size floor; redirect to trained (not distilled)
  small encoders like ZP-KWS.

## Test & Verification

- All four immediate stages run with `~/git/speechangel/research/.venv/bin/python3` on this host.
- Fidelity check on F01 for each stage.
- McNemar + exact-binom per stage.
- Reports in `docs/testing/2026-07-07_*.md`.
- **Benchmark impact:** Not applicable — measurement-only, no matcher/DSP changes.
