# Dysarthric composite re-score (deployment-real negatives) + Round-2 plan to push dysarthric > 800

> **Status: Round-2 STARTED 2026-07-10.** Threat-model decision (user): cohabitant-rejection **OUT OF
> SCOPE** → drops the 87% other-speaker wall + L27/L29/K22-speaker/L28-security; binding wall = in-vocab
> confusion only. Diagnostic (L26) + pre-registered primary (G1) + upper bound (H6) executed; results in
> **`2026-07-10_dysarthric-round2-results.md`**. G1 per-user within-word whitening = **directional positive**
> (dys in-vocab −10.6pp, 57→45%, p=0.004, gate-able on scatter≥0.03), NOT banked pending UASpeech. Small
> vocab (N≈5) → band 700 (H6). Remaining 26 experiments = next-iteration hypotheses. No banked dys-800 on
> n=3 TORGO — UASpeech confirmation is the pre-registered critical-path step.

**2026-07-10.** Follow-through on A2 (the "0.70 wall" is a negative-set artifact) — re-score the dysarthric
D2 axis under deployment-real negatives, locate the true binding wall, then a 30-experiment Round-2 plan
targeting it. Harness: `scripts/eval/ssl_frontend_spike/dys_d2_redux.py`, `g3_nuisance_subspace.py`.
Discipline: EVAL-003 (pre-registered gate, FAR-matched, replicate before banking — the Round-1 campaign
retired 6 refinements that failed cross-corpus, so every Round-2 lever below carries a replication step).

## 1. Re-score result — where the dysarthric wall actually is

Dysarthric D2 FRR@FAR≤5% (wavlm-large L15, few-shot held-out) under each negative distribution:

| negative set | FRR (ALL cmds) | FRR (vocab-distinct ≤25) | band | deployment meaning |
|---|---|---|---|---|
| **ambient (DEMAND)** | **3.0%** | 4.3% | **900** | idle false-accept — the dominant-volume FA source |
| other-speaker OOV | 43.4% | 37.6% | 600 | a bystander says a non-command word |
| **in-vocab confusor** | 68.2% | 57.4% | **500** | the user says a *different* enrolled command (substitution) |
| **other-speaker SAME-word** | 86.9% | 82.3% | **500** | a household member says the command word |

**Verdict — A2 was half right.** Against *ambient* (what actually fires while idle) dysarthric is **band 900**:
idle-reject is solved. **But the composite MIN is still bound at ~500** by two real walls the re-score
isolates:
1. **In-vocab command confusion (68%)** — dysarthric within-word variability ≈ between-word variability, so
   the user's own repeats of command A land as close to command B's templates as to A's. Vocab-distinct
   selection helps only 68→57%.
2. **Other-speaker same-word (87%)** — the cruel one: a dysarthric user's own repeats are *more scattered
   than a clean speaker saying the same word*, so any threshold that rejects the impostor rejects the user.
   A naive speaker gate cannot fix this (it would reject the genuine user too).

**⇒ Re-scoring alone does NOT reach 800.** It proves the wall is **command-confusion + speaker-overlap**, not
idle noise — a much sharper target than "the disorder caps separability at 0.70." The idle-reject axis (900)
is banked-adjacent; the composite needs a lever that contracts within-word scatter *relative to* between-word
and between-speaker distance.

## 2. Scout run (informs the plan): G3 nuisance-subspace removal — REFUTED (a leak artifact)

A4 showed the within-word scatter is *structured* in aggregate; F29 tried to remove it by warping audio and
failed. **G3 removes it in embedding space** — fit the within-word residual subspace, project it out, match.

| dysarthric in-vocab D2 FRR@FAR≤5% (vocab-distinct) | k=0 | k=4 | k=8 |
|---|---|---|---|
| basis **includes** the query (leaked, optimistic) | 57.4% | 31.9% | **22.0%** |
| basis **fold-held-out** (honest) | 57.4% | 64.5% | 63.1% |

**🔴 REFUTED.** The −35 pp "win" was **entirely a leak** — fitting the residual basis on data that includes
the query removes query-specific signal. Under honest fold-based fitting (basis never sees the query fold),
projecting out the subspace **hurts** (57.4→63.1%). This is the **4th** artifact this campaign's honest-eval
discipline caught (after C15/L21, B6/mean2, C21/L10).

**What it teaches (a real characterization of the wall):** the dysarthric within-word scatter is structured
*in aggregate* (A4) but **not along a stable per-speaker direction you can estimate from enrollment and
project out** — the variability is high-dimensional and utterance-inconsistent. That is *why* both F29
(warp) and G3 (project) fail, and it raises the bar for Round-2: the wall needs **per-user discriminative /
verification** methods (learn what separates genuine from confusors/impostors for THIS user), not a fixed
linear nuisance removal. **No quick lever reached dysarthric 800 in scouting — the plan below is genuine open
research, not a solved problem.** The lead shifts to G1/H6/K22/K25/L-series.

---

## 3. Round-2 plan — 30 experiments to push dysarthric > 800

Ordered by information-per-cost. Each: hypothesis · method · pre-registered gate · runnable-status
(✅ cached / ◐ needs asset / ⛔ blocked). The binding walls are **in-vocab confusion** and **speaker-overlap**;
idle-reject (900) is done, so nothing here re-litigates it.

### G — Personalized representation contraction (attack within-word scatter directly) — cached, highest value
- **G1 — Per-user whitening/LDA.** Fit a per-user linear transform (LDA over the user's own words, or ZCA
  whitening of within-word covariance) that contracts within-word / expands between-word. Gate: dys in-vocab
  D2 −5 pp vs raw, held-out. ✅
- **G2 — Per-user Mahalanobis metric.** Learn a metric M from the user's repeats (within-word small,
  between-word large); score under M. Gate: beat G1 by ≥3 pp. ✅
- **G3 — Nuisance-subspace projection. 🔴 SCOUTED & REFUTED (§2):** honest fold-held-out fitting reverses the
  leaked win (hurts). Retained here only as the documented dead-end — a fixed linear nuisance-removal does not
  work because the scatter is not a stable removable direction. Do NOT re-run as-is.
- **G3b — Learned (not fixed) per-user nuisance removal.** Since the *fixed*-basis projection failed, the open
  question is whether a *learned*, regularized within/between contrast (G1/G2) transfers where the eigenbasis
  didn't. Fold-held-out from the start. Gate: dys in-vocab D2 −5 pp, honestly, replicated on a 2nd corpus. ◐
- **G4 — Robust prototype + outlier rejection.** Enroll with a robust centroid (drop the most-variant rep,
  geometric median). Gate: −3 pp with no FAR cost. ✅

### H — Discriminative command-set co-design (raise between-word separation) — cached
- **H6 — Per-user optimal command set.** Given a user's enrollment, greedily pick the ≤N maximally-separable
  commands in *their* embedding space; measure the achievable D2. Answers "what is the best a dysarthric user
  can do with a well-chosen vocabulary?" Gate: report the D2 vs a random ≤N set (expect a large gap). ✅
- **H7 — Confusable-pair remediation.** Detect enroll-time confusable command pairs; suggest a phonetically
  distinct replacement; measure D2 improvement. Gate: −5 pp on the confusable subset. ✅
- **H8 — Enrollment augmentation (effort/tempo perturbation of the user's OWN reps).** Fill the within-word
  manifold with plausible variants (unlike F29's destructive warp — small perturbations). Gate: −3 pp. ✅
- **H9 — Guided re-enrollment.** Reject the most inconsistent enrollment reps and prompt re-record until the
  within-word spread is below a threshold; measure D2 as a function of enforced consistency. Gate: monotone. ✅
- **H10 — Longer / multi-word commands for severe users.** More acoustic content → more separation (heeding
  C20's caution). Gate: 2-word dys commands beat 1-word by ≥5 pp on in-vocab D2. ◐ (TORGO ≤2-word subset)

### I — Dysarthria-tuned front-ends (better representation for disordered speech) — ◐ download/GPU
- **I11 — LoRA/adapter fine-tune of wavlm on dysarthric speech.** Small adapter (CPU-feasible) on TORGO/
  UASpeech, contrastive within-vs-between-word loss. Gate: dys in-vocab D2 −5 pp, held-out speaker. ◐
- **I12 — Dysarthria-pretrained SSL model eval.** Download an impaired-speech-fine-tuned encoder; frozen QbE
  eval. Gate: beat wavlm-large on dys in-vocab D2. ◐ (model download)
- **I13 — Articulatory/phonological-feature front-end.** Features robust to distortion (place/manner). Gate:
  fuse with SSL for −3 pp. ◐
- **I14 — Dysarthric layer/pooling re-selection (done properly).** Per-layer dys D2 with leave-one-speaker-out
  selection + GSC-style replication (avoid the C15/L21 n=3 trap). Gate: a layer beats L15 and replicates. ✅
- **I15 — Multi-encoder fusion.** Score = fusion of wavlm + MFCC-DTW + articulatory. Gate: fusion beats best
  single by ≥3 pp on dys in-vocab D2. ✅

### J — Alignment-aware matching (smarter than F29's naive warp) — ✅ cached frames
- **J16 — Frame-level SSL-DTW for dysarthric.** DTW over `large_frames_L14` frames (not mean-pool) — content
  alignment tolerant of insertions/deletions. Gate: −5 pp vs mean-pool on dys in-vocab D2. ✅
- **J17 — Rate-adaptive DTW band.** Estimate syllable rate, widen the DTW band adaptively (don't warp audio).
  Gate: −3 pp vs fixed band. ✅
- **J18 — Subsequence / partial-match matching.** Match the most-consistent sub-segment of the word. Gate: −3 pp. ✅
- **J19 — Segment-level (phone-like) voting.** Split into pseudo-phone segments, vote — robust to a few bad
  segments. Gate: −3 pp. ◐
- **J20 — Duration-conditioned scoring.** Model the genuine duration distribution per word; penalize by
  duration-likelihood (uses A4's duration axis as *signal*, not nuisance-to-remove). Gate: −3 pp. ✅

### K — Decision layer for the high-overlap regime — ✅ cached
- **K21 — Per-user, per-command adaptive thresholds.** From the user's own genuine/impostor stats (not a
  global θ). Gate: −5 pp at matched FAR. ✅
- **K22 — Contrastive verification head (per-user).** Train a tiny verifier to separate genuine from
  same-word-other-speaker for THIS user — directly attacks the 87% wall. Gate: other-spk-same-word D2
  −10 pp. ✅
- **K23 — Online template adaptation.** Update templates from confirmed accepts (grows the genuine manifold).
  Gate: D2 improves over a session. ◐ (multi-session)
- **K24 — Confirmation in the overlap zone (task-level).** Ask "did you mean X?" when in the margin zone
  (B8/B9 sequential, dysarthric). Gate: task-FRR −15 pp at matched task-FAR. ✅
- **K25 — SPRT multi-attempt for dysarthric.** B9 SPRT measured on the dys population with real n. Gate:
  task-FRR ≤ 15% (band 800) at matched task-FAR. ✅

### L — Personalized speaker-security (fix the other-speaker-same-word 87% wall) — ✅ cached
- **L26 — Why is other-speaker-same-word closer than genuine? (diagnostic).** Decompose within-speaker vs
  between-speaker vs between-word variance for dysarthric. Decides whether L27/L28 are even possible. ✅
- **L27 — Joint content+speaker embedding.** Accept iff BOTH a content match AND a speaker match; the speaker
  channel uses features orthogonal to content. Gate: other-spk-same-word D2 −15 pp with ≤3 pp genuine cost. ◐
- **L28 — Enrollment-consistency gate.** If the user's own reps are too scattered, the account is inherently
  insecure → flag for longer enrollment or a PIN fallback (honest product decision, not a metric hack). ✅
- **L29 — Speaker-adversarial template selection.** Choose templates that a clean speaker's rendition matches
  *least* while the user's own reps match most. Gate: other-spk-same-word D2 −10 pp. ✅
- **L30 — Cross-session personalization curve.** How much does D2 improve as the user accumulates sessions/
  reps? Sets the re-enrollment/adaptation cadence (F30 said dys drift is low → gains come from volume). ◐

**Priority ordering (run first):** **L26** (diagnostic — decompose the within/between/speaker variance; decides
which of L27/K22 is even possible), **K22** (per-user contrastive verification — directly attacks the 87%
other-speaker wall), **H6** (per-user optimal command set — upper-bounds what vocabulary co-design can buy),
**K25** (SPRT multi-attempt — the one Round-1 sequential lever that could reach band 800 at task level),
**G1/G2** (learned per-user contraction — the honest successor to the refuted fixed-basis G3), **J16** (frame
DTW). Every one is **fold-held-out from the start and replicated on a 2nd population before banking** — the
G3 refutation (and Round-1's four caught artifacts) is the standing reminder that single-population scouts on
this data lie. I-series (front-end retrain) + UASpeech-gated items are the second wave.

> **Honest status:** the re-score solved the *idle-reject* axis (band 900) and sharpened the target to
> command-confusion + speaker-overlap, but **no scouted lever cleared dysarthric band 500→800**; G3, the most
> promising, refuted under honest evaluation. Round-2 is real open research with a well-characterized wall,
> not a victory lap.
