# Pre-registration — Frame-level pooling / QbE-DTW journey (typical-900, GSC-19)

**Date:** 2026-07-11 · **Binding metric (EVAL-007):** typical D2 = held-out (LOFO) FRR @ FAR≤5%,
FAR-matched, on the GSC-19 a5 manifest. **Bands (DomainBands.kt spec 2):** 900 = ≤5%, 800 = ≤15%.

## Baseline (fidelity anchor, EVAL-004)
Teacher **wavlm-large L12 / K5, mean-pool + cosine 1-NN = 5.81% FRR @ FAR 3.9%, npos=912**
(19 speakers × 8 words × 6 reps). Hard tail (per-speaker FRR): **98ea0818 27%** (77% wrong-word),
**2aca1e72 25%** (75% below-threshold), **c1d39ce8 19%** (89% below-threshold). Aggregate
false-reject split = **59% below-threshold** (genuine word ranked #1 but distance > accept threshold —
within-word scatter) / **41% wrong-word**. AUC 0.988 (localized hard-voice wall, NOT the dysarthric
information-theoretic AUC-0.65 wall).

## Pre-registered PRIMARY hypothesis (ONE — EVAL-003)
**H1.** Frame-QbE-DTW (`pool=frames_norm`, banded length-normalized DTW, cosine/euclidean local cost)
over **wavlm-large L12** frames — a **change-one-variable** swap of the matcher only (identical
speakers/words/folds/K/threshold/FAR machinery; only mean-pool+cosine → frame-DTW changes) — **reduces
aggregate held-out FRR@FAR≤5% vs the 5.81% mean-pool baseline**, driven specifically by shrinking the
**below-threshold within-word-scatter** component on the two below-threshold-dominated hard speakers
(**2aca1e72, c1d39ce8**). Temporal frame alignment is precisely the operation that can tighten
within-word repeats that mean-pooling averages away.

**Adjudication:** McNemar paired test on per-query accept/reject outcomes at **matched realized FAR**
(mcnemar.py; add exact two-sided binomial if discordant counts are small). Verdict metric = FRR@FAR≤5%,
never bare AUC (EVAL-007). Replication gate (EVAL-005): a directional win must show **≥2 hard speakers
AND a majority of the 19 LOFO folds** moving the same way, plus a pAUC(0–10% FAR) summary agreeing —
otherwise it is underpowered / not demonstrated, not a win.

**Prior (honest):** LOW. Frame-DTW *lost* on dysarthric TORGO (75.6% FRR, AUC 0.672; fusion −3.4 pp;
2×2 tie with MFCC-DTW). But that is a *transfer*, never measured on typical; and the dysarthric wall is
information-theoretic (AUC 0.65) whereas the typical failure is *diffuse scatter* (AUC 0.988) — the one
regime where alignment has a mechanistic reason to help. This is the last untested representation axis
(EVAL-008): the journey either (a) breaks the wall, or (b) closes the axis and **upgrades the banked
"mean-pooled-embedding wall" to a full "representation wall."** Both outcomes are bankable.

## The 10-experiment program (everything past H1 = NOT-banked exploratory family, EVAL-003)
- **F0 (fidelity gate, mandatory).** Mean-pool via the frame pipeline reproduces 5.81% @ FAR 3.9% /
  npos=912 to the decimal; resolve the a5 `N_SPK=24`/`K4` vs teacher `19-spk`/`K5` set empirically here.
  AUC<0.5 = trimming/VAD smell, not a result.
- **E1 (PRIMARY).** Frame-DTW at L12; aggregate + hard-speaker breakdown + below-threshold/wrong-word
  re-split + McNemar vs mean-pool.
- **E2.** Frame-DTW layer sweep (SSL phonetic content peaks mid-layer; frame-DTW's best layer may ≠
  mean-pool's L12). L-best is a mined variant needing its own confirm.
- **E3.** DTW hyperparameters — band ratio, local cost (euclidean-on-normed vs raw), step pattern.
- **E4.** Attentive / GeM pooling — parameter-free GeM (generalized mean p>1) + tiny LOSO attentive pool
  → fixed vector + cosine; O(T), <1 MB, deployable. Separates "alignment matters" (E1) from
  "mean-pooling drops salient frames" (E4).
- **E5.** Frame-DTW × few-shot K-curve (K1..5) — does the one banked lever compound with frame-DTW?
- **E6.** Mechanistic split — frame-DTW helps below-threshold speakers (2aca1e72/c1d39ce8) more than the
  wrong-word speaker (98ea0818)? Falsifiable directional prediction.
- **E7.** Encoder-general replication — best config on distilhubert (24 MB, deployable student) +
  wavlm-base-plus. EVAL-005 direction agreement; does frame-DTW recover more of the +3.0 pp student gap?
- **E8.** Variance/robustness — pAUC(0–10% FAR) + count of 19 folds moving the winning way + unbiased AUC.
- **E9.** Deployability — frame-DTW compute/memory (O(T²)·templates vs O(D) cosine); affordable on-device
  behind the VAD gate?
- **E10.** Fusion/cascade — mean-pool coarse gate + frame-DTW fine re-score on the below-threshold band.

**Execution order:** F0 → E1(+E6+E8 same run) → conditional. Life on the below-threshold speakers →
E2/E3 tune + E5 + E7 replicate + E10 fuse. Flat/worse → E2 (rule out layer) + E4 (rule out any
frame-awareness) → bank the closed negative + EVAL-008 upgrade.

---

## RESULTS LOG (2026-07-11)

- **Fidelity (F0):** all three anchors reproduce 5.81% @ FAR 3.89% / npos=912 — (b) a5 cosine, (a)
  degenerate single-mean-frame DTW, and the paired mean-pool arm inside e1. DP + speaker set faithful.
- **H1 PRIMARY — REFUTED.** Frame-QbE-DTW (frames_norm cosine-DTW) at L6/L9/L12/L15 = 13.82 / 13.60 /
  12.06 / 11.95% (all band 800, +6–8 pp worse); matched-FAR McNemar b=54–82, c=0–1, p<1e-11 in the
  WRONG direction; below-threshold split unchanged (53–58% vs 59%) — alignment does NOT tighten the
  within-word tail at any layer. The pre-registered mechanism fails.
- **UNEXPECTED — the OTHER frame axis (E4 pooling) surfaced a lever.** Statistics pooling **mean⊕std**
  at L12 = **4.71% @ FAR 3.55% → band 900** (beats mean 5.70% within the same frames_norm harness, and
  the shipped raw mean-pool 5.81%). max/gem pooling both worse. mean⊕std also beats mean at L9 (5.26 vs
  6.36) → robust across layers.
- **Same-corpus matched-FAR confirmation (confirm meanstd L12):** held-out 4.71% @ 3.55% vs shipped
  5.81% @ 3.89%; matched-FAR McNemar **b=1 c=19, p=1.4e-4 *** at BOTH FAR 3.89% and 5.00%**; per-speaker
  **6 better / 1 worse / 12 tie**; all three below-threshold hard speakers improve. The within-word
  scatter MECHANISM was right — std captures it; DTW alignment could not.
- **STATUS: NOT BANKED (mined lever, EVAL-003).** Needs a FRESH pre-registered FAR-matched confirmation
  before banking → **H2 below.**

## H2 (new pre-registered primary — the mined-lever confirmation)
**mean⊕std statistics pooling reduces typical D2 FRR@FAR≤5% vs mean-pool** on FRESH conditions the
choice was NOT mined on: (1) **cross-encoder** — the deployable distilhubert student (24 MB, mean-pool
best L2 = 9.32%): frame-encode → meanstd vs mean, matched-FAR McNemar; (2) **std-alone ablation** (is
std or just 2× dim driving it?); (3) direction must hold (≥maj folds, EVAL-005). Bank only if the
cross-encoder confirmation is FAR-matched-significant in the same direction.

### H2 RESULTS — CONFIRMED (both banking conditions met)
- **Cross-encoder (distilhubert L2, deployable student):** meanstd **8.22% @ FAR 3.72% → band 800**
  vs shipped mean-pool 9.32% @ 3.21% (−1.1 pp). Matched-FAR McNemar dominant at every FAR point
  (@2% b=1/c=35 p=4e-08; @3.89% b=1/c=34 p=6e-08; @5% b=4/c=29 p=3e-05; @8% b=3/c=15 p=1e-2), direction
  6 better / 2 worse / 11 tie. Same direction as the teacher. ✓
- **std-alone ablation (moment vs dims) — DEFINITIVE:** std-alone is **1024-dim, same as mean**, yet
  beats mean on BOTH encoders' student layers — distilhubert L2 std=6.36% vs mean=9.32% (−3.0 pp),
  L1 std=8.99% vs mean=11.18%; wavlm-large L12 std=5.92% ≈ mean=5.70%. max/gem (also 1024, frame-aware)
  LOSE on both. ⇒ the lever is the **second moment**, NOT dimensionality and NOT generic frame-awareness. ✓
- **Encoder-dependent best variant (NOT-banked tuning):** meanstd best on wavlm-large (4.71%); std-alone
  best on distilhubert (6.36%). The BANKED claim is "second-moment (std) pooling beats mean-only," not a
  specific variant.

## BANKED VERDICT (scoped)
- **Frame-QbE-DTW (H1): REFUTED** across L6/9/12/15 (band 800, McNemar wrong-direction p<1e-11).
- **Second-moment (std) pooling: BANKED lever**, scoped to GSC-19 (19 speakers) × 2 encoders. Beats
  mean-only pooling on typical D2, FAR-matched-significant, mechanism-verified (2nd moment not dims),
  cross-encoder-general. **Teacher meanstd L12 = 4.71% → typical D2 band 800 → 900** (accuracy-only,
  same wavlm-large deployability caveat the 5.81% carried); **deployable student improves 9.32→8.22%
  (meanstd) / →6.36% (std-alone, mined)** — band 800 with headroom toward 900.
- **EVAL-008 VINDICATED, not upgraded:** the mean-pooled-embedding wall was BROKEN by a better pooling
  of the SAME frames — the substrate *was* the wall. The frame-level axis is now open/productive.
- **Next levers:** cross-cohort/relaxed-speaker replication (no disjoint ≥15-speaker set on GSC-19 —
  only 6 at a relaxed bar); production-Kotlin reproduction of std pooling; per-encoder std-vs-meanstd
  confirm; attentive/learned pooling; std pooling on the dysarthric D2 tail.
