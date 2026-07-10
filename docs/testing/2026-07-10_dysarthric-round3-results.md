# Round-3 results — real male dysarthric speakers refute G1; the wall is confirmed & severity-graded

**2026-07-10.** Execution of the Round-3 plan (`2026-07-10_dysarthric-over900-plan.md`) under `/journey`,
targeting dysarthric in-vocab over band 900. The headline is a **major, high-value negative**: the real
2nd population caught a lever the Round-2 female result would have banked wrongly.

## 0. OSS-first: real male dysarthric speakers acquired (n=3 → 8)

TORGO male dysarthric M01–M05 (`M.tar.bz2`, 2.5 GB) downloaded + embedded (wavlm-large, identical pipeline
to the committed F/FC cache). This is the genuine held-out 2nd dysarthric population Rounds 1–2 lacked — and
categorically better than simulation (see §3). Harnesses: `p6_male_embed.py`, `p7_male_g1_confirm.py`.

## 1. P6 — the in-vocab wall is REAL on male speakers, and severity-graded (banked characterization)

Real male dysarthric baseline (wavlm-large L15, vocab-distinct≤25):

| spk | within-word | fisher | rank-1 conf | D2 FRR@FAR5% | severity |
|---|---|---|---|---|---|
| M03 | 0.026 | 1.86 | 10.9% | **27.3% (band 700)** | mild |
| M01 | 0.046 | 1.04 | 23.6% | 56.4% | moderate |
| M02 | 0.051 | 0.99 | 24.1% | 63.8% | moderate |
| M04 | 0.060 | 0.74 | 44.6% | 82.1% | severe |
| M05 | 0.100 | 0.70 | 27.6% | 89.7% (band 500) | very severe |

**Banked:** the wall (within-word scatter, fisher≈1.0, D2 50–90%) reproduces on 5 new real speakers — the
characterization is now on **n=8 real dysarthric speakers (3F+5M)**, not 3. Female reference: within 0.044,
fisher 1.04, D2 50–57%. Male mean: within 0.056, fisher 1.07, D2 63.8% — the same wall.

**Key reframe — the wall is SEVERITY-GRADED.** M03 (mild) is already D2 27% (band 700) at raw few-shot;
M05 (very severe) is D2 90% (band 500). The intractable case is **severe** dysarthric, *not* dysarthric-in-
general. Mild/moderate dysarthric is much closer to usable than the aggregate implies.

## 2. P7 — G1 does NOT survive held-out male replication (pre-registered generalization REFUTED)

G1 (per-user within-word whitening) was Round-2's directional lever: female TORGO **+10.6pp, p=0.004**,
which even replicated on female *control*. Applying the FROZEN Round-2 config (`zca r=32 eps=0.1`, chosen
before any male data) to the held-out male speakers:

| speaker | raw | G1 | Δ | McNemar |
|---|---|---|---|---|
| M01 | 56.4% | 50.9% | +5.5pp | b=2 c=5 p=0.45 (n.s.) |
| M02 | 63.8% | 75.9% | −12.1pp | b=8 c=1 p=0.039 |
| M03 | 27.3% | 25.5% | +1.8pp | b=3 c=4 p=1.00 |
| M04 | 82.1% | 82.1% | 0.0pp | b=4 c=4 p=1.00 |
| M05 | 79.3% | 81.0% | −1.7pp | b=4 c=3 p=1.00 |
| **pooled** | **62.1%** | **63.5%** | **−1.4pp** | b=21 c=17 **p=0.63** |

**Verdict: the pre-registered generalization claim is REFUTED. G1 is not a speaker-general dysarthric
lever.** The honest per-speaker read is **1 up (M01), 1 down (M02), 3 flat** — direction null. We do **not**
claim "G1 harms males": M02's p=0.039 is one of five tests (multiplicity-fragile), and the pooled effect is
null (p=0.63), not negative. G1's female win (dys *and* control) did not transfer across gender; and as in
Round-2, near-identical within-word scatter (M01 0.046 vs M02 0.051) gives opposite signs — no gating
variable predicts who it helps, so it is not deployable. Had the female directional result been banked, it
would have been wrong. **This is the single highest-value output of the round: the real 2nd population did
exactly its job.**

## 3. Supporting negatives (this round)

- **S22 — dysarthria simulator is UNFIT (fidelity gate failed).** The waveform-domain simulator over-
  degrades: no severity reproduces the real operating point (moderate D2 89%, fisher 0.53 < 1 — within-word
  scatter *exceeds* between-word, worse than real dysarthria). Per the pre-registered two-sided gate it
  cannot validate contraction levers. This vindicates prioritizing real M; the user's fallback condition
  ("simulate *if* no OSS asset") was not triggered.
- **M1 (feasibility) — band 900 reachable only as a per-severity STACK,** not one lever; confusion is
  concentrated on identifiable word-pairs; the operating-point threshold gap (~42pp, L26) dominates the
  rank-1 floor.
- **N2 — confusion-aware vocab selection is rep-limited on TORGO** (worse than random for 2/3 speakers):
  ~2–3 reps/word makes held-out pairwise-confusion estimation noise.

## 4. Verdict on the >900 target — NOT reached, and that is the honest result

Band 900 was not reached, and the round is a **strong negative, not a shortfall**: the wall now survives
every attempted lever on **n=8 real speakers** — representation contraction (G1) fails to transfer across
gender, vocabulary design (N2) is rep-limited, multi-attempt is unmeasurable on rep-poor TORGO, and the
simulator scaffold is unfit. A wall that defeats every lever is a result. The one genuinely positive nuance
is banked: the wall is **severity-graded** — mild/moderate dysarthric (M03 band 700) is far more usable than
the severe aggregate, so the honest product frame is "usable for mild/moderate; severe needs a different
modality," not "dysarthric is uniformly hard."

## What is banked / refuted / next

- **Banked:** the in-vocab wall on n=8 real dysarthric speakers (within-word scatter, fisher≈1.0), and its
  **severity grading** (mild M03 band 700 → severe M05 band 500).
- **Refuted:** G1 within-word whitening as a speaker-general lever (null on held-out male, p=0.63). The
  dysarthria simulator as a proxy for the wall (fidelity gate failed).
- **Methodological lesson (→ rule EVAL-006):** Round-2 treated G1's replication on female *control* as a
  confidence-boosting 2nd population — but same-gender, same-corpus replication gave **false confidence**.
  *Same-demographic control replication ≠ generalization; a personalization lever needs cross-demographic
  (here cross-gender) held-out confirmation before banking.*
- **Next lever (pre-register NEXT session — NOT run this round):** G1 attacked the wall through the
  *representation* and failed to transfer. The dominant term is the operating-point *threshold* gap
  (~42pp), which the **R-series (per-command / per-user adaptive thresholds, T-norm/Z-norm)** attacks
  *without* requiring the representation to generalize across speakers — structurally more likely to survive
  than G1 was. Lead the next round there, with F↔M cross-gender held-out as the standing bar.

> **Honest bottom line:** Round-3 did not reach 900, but it converted the Round-2 directional G1 win into a
> properly-refuted negative using real male speakers, confirmed the wall on n=8, and reframed it as a
> *severity* problem. The real 2nd population — not simulation — was the decisive asset.

---

## Round-4 update (2026-07-10) — the R-series (this doc's "next lever") ran; it is NULL

The R-series (per-command / per-user adaptive thresholds, T-norm/Z-norm) called out above as "structurally
more likely to survive" was run as **R3** alongside the two other deep-research bets (P2 backend = R2, P3
frame-DTW = R1) and the never-run Round-3 primary **N1** (best-admissible stack). Results:
`docs/testing/2026-07-10_d2-wall-p1p2p3-results.md`. **All four fail the binding metric on moderate.** The
R-series is NULL at matched FAR (S-norm −1.5pp; the per-command "gain" was FAR-inflation to 24% — a caught
false positive). N1 confirms **band-900 unreachable** by any admissible stack.

Round-4 also **sharpens the root cause**: the "next lever" premise (attack the *threshold* gap without
requiring the representation to generalize) was reasonable but wrong — the wall is a **tail** phenomenon.
P2/P3 both raised central AUC (0.70→0.9+) yet left the FAR≤5% operating point unmoved, because that point is
set by the worst confusors, not the mean. Forward program pivots to tail-direct + reframe levers:
`docs/plans/2026-07/d2-wall-followup-experiments.md` (W-series), governed by new rule **EVAL-007**.
