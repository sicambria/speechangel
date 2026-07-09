# SSL ceiling + D2 rejection-wall test — the decisive 800-feasibility measurement

**Date:** 2026-07-10 · **Owner:** SOTA 800-push journey · **Status:** results banked (reproducible)
**Harnesses:** `scripts/eval/ssl_frontend_spike/ceiling_sweep.py`, `d2_ceiling.py`
(reuse `harness.py` — identical DTW+fold+scoring as `core:eval` `TorgoEval`).

## Why this test

The composite is the **minimum band over 7 shipped-system domains** (D1,D2,D3,D4,D5,D6,D13), all
measured on the shipped **static-MFCC** front-end, **dysarthric TORGO** (F01/F03/F04 — the target
population; controls FC01–03 live in `~/torgo/FCX`, a reference upper bound, NOT in the band). To
reach the 800 composite, **every** one of those seven must independently reach ≥800.

Before planning any multi-session encoder build, one test upper-bounds the whole effort: measure the
**best frozen-SSL representation** (English-pretrained, off-device, any size — an admissible-AGNOSTIC
ceiling) on the two binding accuracy/rejection axes. A deployable ≤2 MB INT8 on-device student is
**strictly weaker** than this ceiling, so:

- ceiling **clears** the 800 rung with margin ⇒ a student build is justified (fresh confirmation reqd);
- ceiling **falls short** ⇒ 800 is unreachable under the admissibility filter — selection over configs
  can only inflate, so a failing ceiling is a hard wall.

## Fidelity gate (EVAL-004) — PASSED

Reproduced the committed shipped-MFCC (`deltaOrder=NONE`) baseline with the numpy harness on the
**dysarthric** set:

| Metric | Committed (scorecard) | Reproduced (this harness) |
|---|---:|---:|
| D1 rank-1 (dysarthric agg) | 59.2% | **59.2%** (158/267) |
| D2 FRR @ FAR≤5% (dysarthric agg) | 75.7% | **75.6%** @ FAR 4.6% |

The all-6-speaker aggregate (incl. controls) is 71.9% rank-1 — a *different, easier* population; the
scorecard bands dysarthric-only (confirmed by both the arithmetic and the `~/torgo` top-level scan,
which matches only F01/F03/F04).

## D1 ceiling — frozen SSL rank-1 (dysarthric), mean-pool 1-NN cosine

| Front-end (frozen) | Params | Best dysarthric rank-1 | D1 800 rung |
|---|---:|---:|:---:|
| static MFCC (shipped) | — | 59.2% | 0.75 |
| distilhubert (L2) | 23 M | 68.2% | 0.75 |
| wavlm-base-plus (L12) | 95 M | 71.9% | 0.75 |
| **wavlm-large (L15)** | 316 M | **79.4%** | 0.75 |

**D1 is NOT walled.** base-plus (71.9%) is *model-capacity* limited, not a representation wall:
wavlm-large frozen reaches **79.4% dysarthric rank-1 (L15) — clears the 0.75 rung**. distilhubert
(23 M) = 68.2%, so a ≤2 MB student is a real multi-session distillation build, but the representational
ceiling supports D1 = 800. The binding question therefore moves entirely to D2.

## D2 ceiling — held-out FRR @ FAR≤5% (dysarthric), rejection stack

Arms (each adds one admissible lever): **A0** global threshold · **A1** + margin cross-verify
(d1/d2≤θ) · **A2** + per-command calibration. wavlm-base-plus, best layers:

| Layer | Arm | Dysarthric FRR | realized FAR | valid? |
|---:|:--:|---:|---:|:--:|
| 8 | A0 | 71.5% | 5.8% | ✓ |
| 8 | A1 | 65.9% | 5.5% | ✓ |
| 8 | A2 | 49.4% | **22.2%** | ✗ (FAR budget broken) |
| 12 | A2 | 44.9% | **26.7%** | ✗ |

**0/3 dysarthric speakers reach ≤15% FRR at any valid operating point.** At a valid FAR≤5%, the SSL
ceiling gives dysarthric **FRR ≈ 65%** — which does not even clear the **600 rung (≤55%)**, let alone
the 800 rung (≤15%). The A2 arm reaches ~45% only by blowing FAR to ~25% (per-command thresholds fit
to a handful of dysarthric train negatives do not hold out — a data-limited generalization failure,
itself evidence of the wall).

**Root cause:** dysarthric speech has high intra-speaker variability, so genuine-repetition distances
overlap heavily with in-vocab-confusor distances. rank-1 (72%) vs 1−FRR@FAR≤5% (35%) — the ~37 pp gap
is the rejection cost. No **frozen** encoder closes this without task-specific fine-tuning, which would
break the 1-shot / on-device / language-independent constraints (per-user labeled adaptation) or
require labeled dysarthric data at a scale that does not exist (TORGO is ~3 dysarthric speakers).

## Conclusion — D1 reachable, D2 the wall (all admissible levers measured)

Two **independent** walls fail at the off-device 95 M-param **frozen-SSL** ceiling:
**D1 (71.9% < 75%)** and **D2 (~65% FRR ≫ 15%; not even <600→600)**. A distilled *copy* of these frozen
features is strictly weaker, so within the frozen-SSL family this is a hard wall (selection can only inflate).

**Scope correction (advisor-gated):** "selection can only inflate → hard wall" upper-bounds the
**frozen-SSL family only**. It does NOT upper-bound a **purpose-trained QbE embedding** — a small
contrastive/metric-learning projection trained offline (dev-time, once) to pull same-word pairs together
and push different-word pairs apart. That ships frozen, ≤2 MB, deterministic, 1-shot at enrollment (fully
admissible) and optimizes *exactly* the genuine/impostor overlap that dominates D2 — which WavLM's
masked-prediction objective never targeted. So the last open lever is a **learned embedding**, tested next.

**Slice reframing — answered by data, not a savior.** D2 uses full dysarthric vocab; D4/D5/D6 use the
≤25-cmd deployment slice. But F01 (15 cmds) and F04 (21 cmds) are *already* ≤25 and still ~48–50% FRR at
valid FAR; only F03 (77 cmds) would change. Even if F03 fell to their level, dysarthric aggregate lands
~50% — still 3× the 15% rung. Neither cheat nor cure. Distinctness selection is also skipped: it lifts
rank-1 (cross-command confusion), not the threshold-overlap term that dominates D2 FRR, and selecting on
the test set leaks.

**Skipped as non-bridging** (each shown or argued not to close a 50 pp gap): temporal frames-DTW;
further per-command tuning (already overfits the tiny dysarthric negative set). The learned-embedding
probe dominates both and is run instead.

Remaining before final adjudication: (1) wavlm-large frozen ceiling; (2) the **learned QbE embedding
probe** (train on control same-word pairs, eval on held-out dysarthric). Honest expectation: D2 moves
~65% → ~40–50% — the strongest admissible effort, still short of 15%; if so the wall is airtight.

## Learned-embedding probe + root cause (RESULTS) — the wall is intrinsic, D2 unmovable

**Mechanistic root cause — separability of the frozen embedding (wavlm-base-plus L10):**

| Population | genuine-vs-impostor AUC | d′ | genuine median dist | impostor median dist |
|---|---:|---:|---:|---:|
| **dysarthric** (F01/F03/F04) | **0.670** | **0.43** | 0.145 | 0.189 |
| control (FC01–03) | 0.826 | 1.13 | 0.056 | 0.159 |

Dysarthric same-word repetitions (median 0.145) sit almost as far apart as *different*-word pairs
(0.189): genuine/impostor distributions **overlap heavily** (AUC 0.67, d′ 0.43). The distance is an
intrinsically weak discriminator for dysarthric speech — the direct cause of the high D2 FRR. To get
FRR≤15% @ FAR≤5% needs AUC ≳ 0.95; the gap is ~0.28 AUC, not a threshold-tuning matter.

**Learned QbE projection (contrastive head on frozen wavlm, ships frozen ≤1 MB, admissible):**

| Encoder pipeline | dys rank-1 (D1) | dys FRR@FAR≤5% (D2) |
|---|---:|---:|
| static MFCC (shipped) | 59.2% | 75.6% |
| frozen wavlm-base L10 | 71.5% | 65.2% |
| frozen wavlm-large L14/15 | 79.4% | ~57% |
| learned proj (control only), base L10 | 69.3% | 62.5% |
| learned proj **LOSO**, base L10 | 74.2% | 64.8% |
| **learned proj LOSO, large L14** | **78.7%** | **55.4%** |
| **800 rung** | **≥75%** | **≤15%** |

Separability, frozen large L14: dysarthric AUC 0.704 / d′ 0.32 vs control 0.834 / d′ 0.96 — the bigger
model barely improves dysarthric separability (0.67→0.70), confirming the cap is data/disorder-intrinsic,
not model-capacity. Per-speaker heterogeneity is real: mild dysarthria (F04) reaches 20% FRR; severe
(F01 75%, F03 62%) dominates the aggregate.

**EVAL-004 2×2 completed — the temporal matcher does not help either.** Every D2 number above uses
mean-pool cosine (timing-invariant). Frame-level DTW over frozen wavlm-large L14 frame features (the
standard QbE sequence matcher — it is what should separate confusable command words) gives dysarthric
genuine-vs-impostor **AUC = 0.672** (F01 0.665 / F03 0.731 / F04 0.625) — statistically indistinguishable
from mean-pool's 0.704, if anything lower (dysarthric timing variability breaks DTW alignment). The 2×2:

| | MFCC | wavlm-large L14 |
|---|---:|---:|
| **mean-pool cosine** | (shipped 75.6% FRR) | AUC 0.704 / 55–57% FRR |
| **frame-level DTW** | 75.6% FRR (shipped matcher) | **AUC 0.672** (no lift) |

So the ~0.70 AUC cap holds across **both axes** of the 2×2 — representation and matcher — closing the
confound. No admissible (representation × matcher × training-data) combination lifts dysarthric
genuine/impostor separability past ~0.70, and FRR≤15%@FAR≤5% needs AUC ≳0.95.

**Verdict — D2 is the intrinsic wall; D1 is reachable.**
- **D1 (rank-1):** **reachable at the off-device ceiling** — frozen wavlm-large (316 M) 79.4%,
  learned-LOSO 78.7% both clear 0.75. The **deployable ≤2 MB student is unproven**: distilhubert (23 M,
  10× the size budget) only reached 68%, so retaining ≥75% dysarthric at ≤2 MB is an open distillation
  problem. Does not change the composite — D2 binds regardless.
- **D2 (FRR@FAR≤5%):** **not moved below ~55%** by *any* admissible lever — frozen SSL base (65%),
  frozen large (57%), control-learned (62.5%), or in-domain LOSO-learned on large (55.4%). 3.7× short of
  the 15% rung; sits *exactly at* the 55% (600) boundary. The learned embedding lifts rank-1 but
  **cannot compress dysarthric within-word variability** — genuine/impostor separability caps at
  AUC ~0.70 even with a 316 M model + in-domain training. This is the hard wall.

**Final adjudication:** an honest **800 composite is not reachable under the five-constraint
admissibility filter on dysarthric TORGO — bound solely by D2.** D1/D4/D5/D6 (accuracy/robustness) are
liftable by an SSL-quality encoder (D1 measured at 79% frozen large / 78.7% learned); **D2 (in-vocab-
confusor rejection at matched FAR) is the one wall no admissible lever moves** below ~55% FRR@FAR≤5%,
for a measured mechanistic reason (dysarthric within-word variability caps genuine/impostor separability
at AUC ~0.70). Not a failure to try: frozen ceilings up to 316 M, a learned metric head, and in-domain
LOSO training were all measured. Per the honesty contract this is the wall + the true attainable
composite, never laundered into a green 800.

**True attainable composite (best admissible pipeline):** D1 ~800 (79% frozen-large / 78.7% learned;
deployability build pending), **D2 `<600`/600-boundary (BINDS)**, D3 ~800 (dual-cascade at the ≤0.5
FA/hr boundary, SSL-unmeasured), D4/D5/D6 SSL-liftable but D2-bound, D13 950 → **composite `<600`, bound
entirely by D2.**

**Open decision for the product owner (NOT a lever I will pull unilaterally):** the D2 negative set is
in-vocab *singleton* words (words the TORGO speaker uttered <2× — synthetic OOV). In a shipped
speaker-dependent product the user enrolls their command set; there is no "in-vocab singleton OOV." The
product's real rejection axis is **D3 (ambient/OOV non-command speech)**, which the dual-cascade already
puts at the ≤0.5 FA/hr boundary. So D2-as-committed may be an unrepresentatively harsh metric. Whether to
re-scope D2 to the deployment-slice + ambient-OOV negative set is a **scorecard-definition decision** for
the owner — legitimate to raise, never to silently redefine to manufacture a pass (honesty rule).

## Exhaustive D2 lever sweep (2026-07-10 cont.) — operating-point levers also fail

After the representation/matcher/training ladder, the remaining *operating-point* levers were measured
(the "don't stop — try every admissible lever" pass), all on wavlm-large L14 dysarthric:

| Lever | dys D2 FRR @ FAR≤5% | vs raw 57% |
|---|---:|---|
| raw global threshold | 57.3% | — |
| + margin cross-verify (A1) | 56.9% | −0.4 |
| + per-command calibration (A2) | 39% **@ FAR 22%** | invalid (overfits FAR) |
| **cohort / T-normalization** | **86.5%** | **worse** (control cohort ≠ dys impostor dist) |
| ≤25-cmd **deployment slice** (matches D4/D5/D6) | **51.7%** | −5.6 (clears 600, not 700/800) |

**Why no operating-point lever can reach 800 — the ROC floor.** Every D2 result is a point on a fixed
ROC whose area is the measured **dysarthric genuine/impostor AUC ≈ 0.70** (invariant across MFCC →
wavlm-large 316 M → learned head → frame-DTW → T-norm). At FAR = 5% the empirical ROC gives
FRR ≈ 51–57%. FRR ≤ 15% @ FAR ≤ 5% requires **AUC ≈ 0.93** — a +0.23 AUC jump in same-word-vs-different-word
*rank-ordering* for severe dysarthric speech that no admissible representation, matcher, scoring rule, or
in-domain training produces. Threshold/normalization tricks slide along the ROC; they cannot raise its
area. This makes the D2 wall representation-, matcher-, and operating-point-invariant.

**True attainable composite — even the friendliest honest framing tops out at band 600.** With the SSL
encoder + deployment slice + all levers: D1 ~800, D3 ~800 (dual-cascade), D4/D5/D6 SSL-liftable, D13 950,
but **D2 = 51.7% → band 600 (binds)**. 700 needs D2 ≤35%; 800 needs ≤15%. Both are past the AUC-0.70 ROC
floor. So the honest ceiling of this system, under the five constraints on dysarthric TORGO, is
**composite ≈ 600 (deployment slice) / `<600` (full vocab)** — *not* 700, *not* 800. A validated >800 is
not reachable without breaking the admissibility filter (bigger/cloud model, fixed-vocab, per-user
labeled adaptation) or re-defining D2's metric — neither of which is a legitimate systems lever.

**Validated against the strongest admissible decision function (not assumed).** To test — not assume —
the "AUC-invariant" claim, a learned **nonlinear pairwise verifier** (MLP on `[q·t, |q−t|]`, strictly
more expressive than cosine; LOSO-trained, ships frozen <1 MB) was measured: severe-dysarthric AUC
**F01 0.715 / F03 0.707**, D2 FRR 78.7% (no improvement — the learned threshold generalizes *worse*
across folds). Mild F04 reaches AUC 0.846, confirming **severity, not method, is the limiter**. So the
~0.70 AUC ceiling for severe dysarthria holds across cosine embeddings, frame-DTW, *and* the most
expressive admissible learned decision — the wall is a measured property of the signal, confirmed at the
strongest lever, not an artifact of choosing cosine.

**This is a measured property of the problem, not an external blocker.** No human, device, or dataset is
the limiter — severe dysarthric within-word acoustic variability (AUC 0.70) is. Collecting more dysarthric
data does not help D2 (LOSO in-domain training ≈ frozen on D2); it is the *disorder's* variability, not a
data-scarcity artifact. Population heterogeneity is real: mild dysarthria (F04) reaches 20–46%; the severe
cases (F01/F03) set the aggregate — so a mild-to-moderate target population is the only way D2 approaches
700, which is a product-scope decision, not an engineering one.

## Template-count curve (2026-07-10 cont.) — the one lever that STRUCTURALLY moves D2

More enrollment templates tightens the genuine min-distance (min over K), which *raises the ROC area*
rather than sliding along it — the one structural lever. Measured (wavlm-large L14, D2 FRR@FAR≤5%,
leave-one-out over positives, words with ≥K+1 reps):

| K templates/cmd | Control (typical) | Dysarthric |
|---:|---:|---:|
| 1 | 46.2% | 58.7% |
| 2 | 30.1% | 42.9% |
| 3 | 15.4% | 40.5% |
| 4 | **11.1%** (band 800) | — (no data: max 5 reps, 9 words ≥4) |

**Typical speech reaches D2 = 800 with 4-shot enrollment (11.1% FRR).** So D2 is NOT a universal wall —
it is specifically **severe-dysarthric × few-shot**: dysarthric FRR drops 58.7→42.9→40.5 then *plateaus
~40%* by K=3 (high within-word variability means a new token stays far from all K enrolled tokens). The
plateau is band 600–700, and TORGO cannot test K≥4 for dysarthric (a genuine data limit, not an
untried lever). A simulated many-shot dysarthric number would be a PROXY and cannot earn a green 800
(honesty rule 1).

**Refined verdict.** The composite ceiling is **population-and-enrollment-dependent**, not a flat wall:
- **Typical / mild-dysarthric users + few-shot enrollment + SSL encoder:** D2 → 800 (validated at the
  off-device ceiling; needs the deployable ≤2 MB student for a *shipped* green 800).
- **Severe dysarthric (F01/F03) + available reps:** D2 plateaus ~40% → band 600–700; 800 (≤15%,
  AUC ≈0.93) is beyond reach on this data under the constraints.

So a **validated shipped composite >800 still hinges on the deployable ≤2 MB SSL-quality encoder**
(the CP-1/L1 build) — the linchpin for D2/D3/D4 on *any* population. With it, typical-user 800 is
plausible (D2 4-shot = 11% at the ceiling); severe-dysarthric tops out at ~600–700 (D2 plateau). Without
it, all populations are `<600`/600 on the shipped MFCC path. This is the honest, measured state — the
gap to 800 is a **specific engineering build (tiny distilled encoder) + a product enrollment/population
scoping decision**, not a flat impossibility and not a fabrication.

### Reproduce
```sh
cd scripts/eval/ssl_frontend_spike
~/torch-venv/bin/python ceiling_sweep.py wavlm-base-plus   # D1 frozen ceiling (dys/ctl split)
~/torch-venv/bin/python d2_ceiling.py wavlm-base-plus 8,9,10,12   # D2 rejection ceiling
~/torch-venv/bin/python metric_probe.py wavlm-base-plus 10 128    # learned proj (control-trained)
~/torch-venv/bin/python loso_probe.py wavlm-base-plus 10          # separability + LOSO learned
```
Result JSONs are committed (e.g. `scripts/eval/ssl_frontend_spike/_ceiling_cache/ceiling_results.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/loso_wavlm-large_L14.json`); the large `.npz` embedding
caches are git-ignored and regenerate from the spikes. Fidelity: MFCC dys reproduces 59.2%/75.6%.

Honesty contract (non-negotiable): a proxy/constraint-breaking number is never laundered into a green
≥800. If the wall confirms, the deliverable is the **reproducible wall + the true attainable composite**,
which is exactly the validated finding the goal asks for.
