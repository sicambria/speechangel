# D2-wall Round-4 — the three deep-research bets (P1/P2/P3) all fail the binding metric; the wall is a *tail* phenomenon

**Date:** 2026-07-10 · **Corpus:** TORGO real dysarthric (3F + 5M, n=8), per-severity, held-out
**Anchor:** `docs/research/2026-07-10-move-d2-wall.md` (deep-research shortlist: P3 > P2 > P1)
**Binding metric (advisor-locked):** FRR @ FAR≤5%, held-out (LOFO), **per severity**, moderate-centered.
AUC is a secondary diagnostic only. **Live population = moderate** (M01/M02/F03); mild is already band 700,
severe/very-severe (M04/M05) are plausibly information-capped.

Harnesses: `scripts/eval/ssl_frontend_spike/{r1_frame_dtw_d2,r2_backend_d2,r3_scorenorm_d2}.py`.
Evidence JSON: `_ceiling_cache/{r1_frame_dtw_d2,r2_backend_d2,r3_scorenorm_d2}.json`.

---

## TL;DR

All three top-ranked untried attacks on the D2 wall were run on real dysarthric data with the
leakage/FAR/held-out controls the refuted G1/G3 taught us. **None moves the binding metric on the live
moderate population.** The unifying finding is mechanistically new and sharper than "the wall is real":

> **The D2 wall is a TAIL phenomenon, not a central-separability one.** Every lever that raised central
> separability (pooled ROC-AUC rose 0.70 → 0.88–0.96 under P2 and P3) left the **FRR @ FAR≤5% operating
> point unmoved or worse**, because that operating point is set by the *worst* in-vocab confusors (the 5th
> impostor percentile), not by the mean. Raising average genuine/impostor separation does not thin the
> confusor tail.

| Bet | Lever | Moderate D2 result (binding) | Central AUC | Verdict |
|---|---|---|---|---|
| **P3** | frame-trajectory DTW vs pooled cosine | fdtw **−1.7pp** (worse) | 0.83→0.89 (↑) | **NOT-BANKED** |
| **P2** | LDA+WCCN backend on frozen WavLM | +0.6pp (loso) / +1.3pp (xgender) | +0.02…+0.07 (↑) | **KILLED** (same family as G1/G3) |
| **P1** | AS/S-norm + per-command thresholds | snorm −1.5pp; per-cmd "gain" = FAR artifact | invariant (monotone) | **NULL** at matched FAR |

---

## P3 — frame-trajectory DTW (the highest-ranked, only dysarthria-validated bet) — NOT-BANKED

`r1_frame_dtw_d2.py`. The deferred "run the full D2 frame-DTW" from `frame_dtw_sep.py`. Both scorers do
best-of-exemplars (min over templates), so the isolated variable is **trajectory-DTW vs mean-pooling**
(advisor lock). Frame features = frozen wavlm-large L14 `frames_norm`; males newly extracted
(`male_frames_L14.npz`, `extract_male_frames.py`).

| spk | sev | npos | nneg | pool FRR | pool AUC | fdtw FRR | fdtw AUC | ΔFRR |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| M01 | moderate | 86 | 60 | 59.3% | 0.830 | 62.8% | 0.888 | **−3.5pp** |
| M02 | moderate | 88 | 60 | 58.0% | 0.894 | 58.0% | 0.934 | 0.0pp |
| M03 | mild | 96 | 60 | 31.2% | 0.904 | 36.5% | 0.963 | −5.2pp |
| M04 | severe | 82 | 60 | 84.1% | 0.743 | 91.5% | 0.543 | −7.3pp |
| M05 | very severe | 151 | 60 | 90.7% | 0.767 | 88.7% | 0.750 | +2.0pp |

**Verdict:** moderate (M01/M02) pooled 58.6% → frame-DTW 60.4% = **−1.7pp (worse)**; mild+moderate (M01/M02/M03)
−3.7pp (committed JSON verdict). Pre-registered success was ≥8pp *better*. **NOT-BANKED.** Frame-DTW lifts central AUC (M01 +0.06, M02 +0.04,
M03 +0.06) yet the tail FRR is equal-or-worse — the tail/central split again. This is the strongest
dysarthria-validated candidate in the literature (LPM, Apple IS2023), and it does not transfer to the
FRR@FAR≤5% in-vocab-confusor task on TORGO. (Females carry no D2 here — the female frame cache holds command
wavs only, no negatives — so males, which include the live moderate cell, carry the verdict.)

## P2 — trainable backend on frozen WavLM (LDA+WCCN) — KILLED

`r2_backend_d2.py`. Same family (learn a linear transform of the embedding) as the two levers already dead
on this problem: G1 (per-user whitening, refuted on held-out males p=0.63) and G3 (nuisance-subspace,
leakage artifact). Backend trained **leave-one-speaker-out** on (speaker,word) classes; two regimes: `loso`
(all other speakers) and `xgender` (train females → test males, the strict G1-style transfer guard).

Moderate mean ΔFRR (positive = improvement): **loso +0.6pp, xgender +1.3pp** — both below the 3pp kill line.
Per-speaker the only real FRR gains land on **mild** speakers already at band 700 (F04 +6pp, M03 +7–10pp),
not where the wall lives; F01 (severe) got *worse* (−6.2pp). Meanwhile pooled AUC rose everywhere
(+0.02…+0.07). **KILLED** — a central-AUC lift that does not reach the FAR≤5% tail on the live population;
any positive is **NOT-BANKED** as it fails the same transfer test that sank G1.

## P1 — score normalization + per-command thresholds (the deferred R-series) — NULL at matched FAR

`r3_scorenorm_d2.py`. AS/S-norm (Z-norm per-command impostor cohort + T-norm per-query) and per-command
adaptive thresholds — the single most-direct untried attack on a fixed-AUC-at-fixed-FAR wall.

The naive per-command lever looked like a **+15.7pp** moderate win — **but its realized held-out FAR was
23.8%** (F03 33%, M01 20%, M02 18%), a 5× budget blow-out; the "gain" was spurious. This is exactly the
EVAL-003 trap. At **matched FAR≤5%**:

| lever | moderate FRR | moderate FAR | ΔFRR vs A0 | valid? |
|---|--:|--:|--:|:--:|
| A0 (global thr) | 62.7% | 4.9% | — | ✓ |
| per-command budget | 47.0% | **23.8%** | +15.7pp | ✗ FAR-invalid |
| per-command FAR-matched (`pcfm`) | 61.8% | 9.4% | +0.9pp | ✗ (slightly over) |
| AS/S-norm | 64.3% | 5.9% | **−1.5pp** | ✓ |

**Verdict: NULL.** The only FAR-valid lever (S-norm) is −1.5pp; FAR-matched per-command centering is +0.9pp.
Consistent with theory — a monotone/affine per-command score map cannot add separability, so at matched FAR
the moderate tail does not move.

---

## Why this is a stronger result than "the wall is real"

The Round-3 characterization was "within-word variance ≳ between-command distance ⇒ AUC≈0.70 ⇒ wall." This
round shows AUC is **not** the binding quantity: P2 and P3 both *raised* central AUC to 0.88–0.96 on the
moderate speakers while the FRR@FAR≤5% tail stayed at 58–63%. The wall is set by the **worst-case confusor
mass at the 5th impostor percentile**, and none of the admissible representation/score levers thins that
mass. Corollary: future work should target the **tail directly** (per-confusor abstain, tail-loss training,
worst-case-confusor enrollment) or reframe (P5), not chase mean separability. See the follow-up plan
`docs/plans/2026-07/d2-wall-followup-experiments.md`.

## Method integrity notes (what makes these bankable negatives)

- **FAR-matched** verdicts only; any lever whose realized held-out FAR exceeds 5%+tol is flagged
  FAR-invalid (caught the P1 false positive).
- **Held-out speaker + cross-gender transfer** for P2 (the exact condition that refuted G1).
- **Per-severity, raw counts printed** (npos/nneg), moderate-centered; n=8 with per-severity cells
  dominated by single speakers ⇒ these are directional negatives, not knife-edge positives (EVAL-005/006).
- **Real corpus only** (TORGO); no simulator (S22 unfit).
