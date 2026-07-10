# Round-3 plan — 30 experiments to push dysarthric in-vocab over band 900 (FRR ≤ 10% @ FAR ≤ 5%)

**2026-07-10.** Continuation under `/journey`. Round-2 established: cohabitant-rejection out-of-scope →
binding wall = **dysarthric in-vocab confusion** (57% FRR@FAR≤5%, band 500); G1 within-word whitening is a
directional +10.6pp lever (band 500→600), small vocab N≈5 → band 700; blocked from banking by **n=3 TORGO**.

## 0. Two enabling moves this round (OSS-first, per journey step 2)

1. **REAL male dysarthric speakers.** TORGO M01–M05 (+ MC01–MC04 controls) are freely downloadable
   (`M.tar.bz2` 2.5 GB, `MC.tar.bz2` 3.4 GB — verified HTTP 200). Downloading now. This turns n=3 → **up to
   n=8 real dysarthric speakers** and gives a genuine held-out 2nd population (fit on F → confirm on M, and
   vice-versa) with **zero simulation circularity**. This is the primary asset; it is what unblocks banking.
   *Scope caveat (advisor):* M is still TORGO → it confirms speaker-generalization, NOT channel-independence.
2. **First-principles dysarthric simulator (complementary scaffold, NOT centerpiece).** The user's fallback
   condition ("simulate if you don't find OSS assets") is technically *not triggered* (real M found), but the
   simulator fills two roles M/TORGO cannot: (a) **non-TORGO-channel dysarthric audio** (degrade clean GSC) —
   the missing 2×2 corner to disentangle "G1 helps dysarthria" from "G1 helps the TORGO channel"; (b)
   **arbitrary rep count** — TORGO is rep-capped (~5), too rep-poor to measure the multi-attempt/SPRT gain
   curve. Built only if G1 stays load-bearing, under strict guardrails (§S).

## 1. Feasibility gate (M1, run F-only, cached) — is band 900 even reachable?

Band 900 (FRR≤10%) is BELOW the full-vocab rank-1 confusion floor (15.6%, L26), so single-shot full-vocab
is impossible. M1 measured whether small-vocab + design + multi-attempt can escape:

| speaker | N5 random floor | N5 pair-aware floor | multi-attempt k=1→k=2 | modal-confusor conc. |
|---|---|---|---|---|
| F01 | 16.6% | **4.9%** | rep-poor | 0.50 (n=2 src, noisy) |
| F03 | 5.0% | **1.2%** | 17→17% (systematic) | 0.58 (n=15, reliable) |
| F04 (severe) | 6.0% | 19.6% (centroid fails) | **5→0%** | 0.83 (n=3, noisy) |

**Verdict — >900 is REACHABLE at small vocab, but heterogeneously by severity, and only as a STACK:**
- Confusion is *concentrated on identifiable word-pairs* (modal conc 0.64 ≫ 0.04 random; control similar →
  partly universal phonetic confusability) → **designable around at enrollment**, not random noise.
- Confusion-aware small vocab drives the threshold-free floor ≤5% for F01/F03; multi-attempt drives it →0%
  for severe F04 (its confusions *are* somewhat random). No single mechanism covers all three.
- **Necessary-but-not-sufficient:** rank-1 floor ≤10% is the classification floor; the operating-point
  FRR@FAR≤5% still carries L26's ~42pp threshold gap → within-word contraction (G1) and adaptive thresholds
  are still required to *reach* the floor.

## 2. Definition of Done (pre-registered, honest)

**PRIMARY (ONE hypothesis, N1):** on a small (N≈5) **confusion-aware** command vocabulary, the stack
{confusion-aware selection + G1 within-word contraction + per-command adaptive threshold + margin-zone SPRT
multi-attempt} drives **dysarthric in-vocab D2 FRR@FAR≤5% ≤ 10% (band 900)**, fit on TORGO-F and **confirmed
on held-out real TORGO-M**, adjudicated by paired McNemar at matched FAR. Component ablations are the
exploratory family (NOT banked individually without their own pre-registered confirmation). SPRT must be a
proper FAR-preserving sequential test (multi-attempt gives impostors extra shots too — 2-of-3 voting does
NOT preserve the budget). Primary metric = FRR@matched-FAR; report the partial-AUC curve as the low-variance
summary (EVAL-005). **Honest ceiling statement up front:** >900 on the *full* vocab is impossible (floor
15.6%); the claim is scoped to a small deployment vocab, which is a legitimate product regime.

---

## 3. The 30 experiments (ordered by information-per-cost)

### N — the operating-point stack toward 900 (cached F; confirm on M) — highest value
- **N1 — PRIMARY: the full stack** (above). ✅ (assembles N2–N4 + P6/P7)
- **N2 — Confusion-aware vocab on HELD-OUT confusion** (not centroid distance — that failed F04, M1). Select
  the ≤N words with lowest mutual held-out confusion. Gate: N5 floor ≤5% all speakers incl. severe. ✅
- **N3 — Per-command adaptive threshold** (K21): per-word genuine/impostor stats, not a global θ. Gate:
  close ≥50% of the ~42pp operating-point gap at matched FAR. ✅
- **N4 — FAR-preserving SPRT multi-attempt.** Proper sequential test; impostors get the same extra shots.
  Gate: severe-speaker FRR −15pp at *matched task-FAR* (not per-attempt FAR). ✅
- **N5 — Margin-zone confirmation** ("did you mean X?") only when in the ambiguity band. Gate: task-FRR
  −15pp at matched task-FAR. ✅

### P — real male-dysarthric confirmation (the unblocking asset) — after download
- **P6 — Embed M01–M05, re-measure the dysarthric baseline** (in-vocab D2, within-word scatter, fisher,
  floors, confusion stability) on real male dysarthric. Extends n=3→n=8. ◐ (download+embed)
- **P7 — G1 cross-speaker confirmation:** fit contraction on F, confirm on held-out M (and vice-versa).
  Gate: dys in-vocab −5pp holds cross-speaker, paired. ◐
- **P8 — Severity stratification** using TORGO intelligibility scores: which levers work at which severity. ◐
- **P9 — F↔M leave-one-speaker-out** for every bank-candidate lever (the real replication Round-2 lacked). ◐
- **P10 — M1 replication on M** (is confusion systematic/concentrated for males too?). ◐

### Q — within-word contraction beyond G1 (representation) — cached
- **Q11 — G2 per-user Mahalanobis metric** (learned within/between contrast). Gate: beat G1 by ≥3pp. ✅
- **Q12 — Cross-validated G1 regularization** (pick r/eps by inner CV per user, NOT swept-on-test). ✅
- **Q13 — Frame-level SSL-DTW (J16)** on `large_frames_L14` — alignment-tolerant; could be the lever that
  *generalizes* where G1 is TORGO-scoped. Gate: −5pp vs mean-pool, and check GSC sign. ✅
- **Q14 — Robust prototype + outlier rejection (G4):** geometric-median centroid, drop most-variant rep. ✅
- **Q15 — Enrollment augmentation (H8):** small seeded acoustic perturbations of the user's OWN reps to fill
  the within-word manifold (unlike F29's destructive warp). Gate: −3pp. ✅

### R — decision layer (close the operating-point gap) — cached
- **R16 — Per-command per-user adaptive threshold** (detailed K21; feeds N3). ✅
- **R17 — Per-user score normalization** (T-norm / Z-norm over the user's impostor stats). ✅
- **R18 — Conformal / quantile calibration per command** (distribution-free FAR guarantee). ✅
- **R19 — Two-stage cascade:** coarse accept, then a confusable-pair disambiguator for the concentrated
  confusors M1 found. Gate: −5pp on the confusable subset with no FAR cost. ✅
- **R20 — Duration-likelihood scoring (J20):** penalize by per-word genuine duration likelihood (A4 axis as
  signal). ✅

### S — first-principles dysarthric simulator (scaffold; STRICT circularity guardrails) — ◐ build
- **S21 — Waveform-domain simulator.** Degradations grounded in dysarthria phonetics, applied to clean GSC:
  per-token independent draws of time-stretch (slow/variable rate), formant/vowel-space compression,
  spectral tilt (breathiness), F0 jitter/flattening, aspiration noise, intensity perturbation. Seeded →
  fully reproducible. **NEVER an embedding/feature-space additive nuisance** (that would make G1 work by
  construction). ◐
- **S22 — FIDELITY GATE (two-sided, non-circular):** dial severity so synthetic-dys-GSC D2 FRR lands in
  TORGO's 50–57% band (decision-level calibration), THEN *independently verify* the embedding geometry
  (fisher≈1.0, within-word scatter ~2.5× clean) **emerges unfit** — do NOT calibrate on the statistic G1
  exploits. If geometry doesn't emerge, the simulator is not a valid proxy → do not use it. ◐
- **S23 — G1 on synthetic-dys-GSC (the 2×2 corner):** dysarthric-degraded NON-TORGO channel. Resolves
  Round-2's open question — does G1 help *dysarthria* or the *TORGO channel*? ◐
- **S24 — Multi-attempt/SPRT gain curve at arbitrary rep count** (10–20 reps/word) — the curve TORGO is too
  rep-poor to measure. Validates N4's FAR-preserving SPRT. ◐
- **S25 — Controlled severity sweep:** lever behavior (G1, small-vocab, SPRT) vs a monotone severity axis. ◐

### T — dysarthria-tuned front-end (representation) — ◐ download/compute
- **T26 — Layer re-selection with F+M LOSO** (proper; avoids the C15/L21 n=3 trap that already burned us). ◐
- **T27 — Multi-encoder fusion** (wavlm + MFCC-DTW + articulatory). Gate: fusion −3pp vs best single. ✅
- **T28 — LoRA/adapter contrastive fine-tune on F+M** (CPU-feasible small adapter; within-vs-between-word
  contrastive loss; held-out speaker). Gate: dys in-vocab −5pp, LOSO. ◐
- **T29 — Articulatory / phonological-feature front-end** (place/manner features robust to distortion). ◐
- **T30 — Dysarthria-pretrained SSL encoder eval** (frozen QbE, if an OSS impaired-speech model exists). ◐

**First wave (run order):** P6 (embed M — unblocks everything) → N2 (confusion-aware selection, fixes F04) →
N3/R16 (adaptive threshold, closes the operating-point gap) → N4 (FAR-preserving SPRT) → **N1 assembled,
confirmed on held-out M (P7/P9)**. S21/S22 (simulator + fidelity gate) in parallel as the channel corner.
Every bank-candidate goes through F↔M LOSO (P9) before any bank — the real 2nd population Round-2 lacked.

> **Honest status:** M1 shows band 900 is reachable at small vocab as a per-severity STACK, not a single
> lever — and only if the operating-point threshold gap is also closed. Real M is the asset that lets this
> be *banked* rather than left directional. The simulator is a scaffold for the two things TORGO can't do
> (non-TORGO channel, arbitrary reps), fenced by a two-sided fidelity gate to stay non-circular.
