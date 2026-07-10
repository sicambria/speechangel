# D2-wall — next 30 most-promising experiments (ranked by EV/cost)

**Status:** active (design; ranking companion to `d2-wall-followup-experiments.md`)

## Goal

Rank the next 30 experiments by **expected value per unit cost** = P(moves the binding metric FRR@FAR≤5%
on moderate dysarthric **OR** yields a shippable product **OR** decisively closes a question). Grounded in
Round-4 (`docs/testing/2026-07-10_d2-wall-p1p2p3-results.md`): voice-only single-shot verification is
tail-capped (unbiased AUC ~0.65 moderate, no admissible lever moves the FAR≤5% tail), so the product likely
lives in **reframing the target (Tier A)** and **complementary modality (Tier E)**, while the best remaining
shot at the raw metric is **tail-direct decision rules (Tier B)** — which are cheap.

## Context & Constraints

- **Binding metric:** FRR@FAR≤5% held-out (LOFO), per severity, moderate-centered, **FAR-matched**
  (EVAL-007 — verify realized held-out FAR; a per-command budget does NOT control global FAR).
- **Adjudicate on FRR@FAR, not AUC** (EVAL-007); AUC only as an all-genuine diagnostic (`auc_unbiased.py`).
- **Admissibility (hard filter):** on-device, speaker-dependent, language/vocabulary-agnostic, few-shot,
  deterministic, NNAPI/INT8 ≤~150 MB. Real corpora only (no simulator). Cross-gender report is a diagnostic,
  not a kill-guard, for backends (P2 passes transfer, dies on magnitude).
- **Runnability:** ▶ runnable now on TORGO + cached embeddings / CPU · ◐ needs a model or prototype ·
  ⛔ needs a corpus or hardware not present.

## Approach

Five tiers, run in EV order. First session should execute the Tier-A/B ▶ set (#1, #2, #3, #6, #7, #8) —
all attack or reframe the tail with no new model — before touching another representation or backend.

## Steps

### Tier A — Reframe the target (highest payoff; the single-shot FAR≤5% metric may be wrong for AAC)

| # | Exp | Run | Hypothesis / success bar |
|--:|---|:--:|---|
| 1 | **Task-success-with-confirm metric** — re-score TORGO under "≤2 attempts + 1 confirm turn" | ▶ | moderate reaches ≥85% task-success once a confirm turn absorbs the tail. **Likely the highest-value single experiment.** |
| 2 | **SPRT / sequential multi-attempt** — accept after k consistent repeats | ▶ | moderate effective FRR≤15% at ≤2.0 mean turns |
| 3 | **Abstain+confirm (conformal reject at the confusor tail)** — accept/reject/"did you mean X?" | ▶ | ≥85% task-success, abstain-rate <20% |
| 4 | **Per-severity operating points + auto-route** (mild→direct, moderate→confirm, severe→modality) | ▶ | deployable policy w/ FRR+FAR+confirm-rate per severity cell |
| 5 | **Severity auto-detector** from enrollment within-word scatter / fisher → routes #4 | ▶ | ≥80% agreement with D2-band label, held-out |

### Tier B — Tail-direct decision / calibration (cheap; the one under-explored class)

| # | Exp | Run | Hypothesis / success bar |
|--:|---|:--:|---|
| 6 | **One-class density per command** (Mahalanobis / kNN-density on genuine reps) vs NN-distance | ▶ | ≥8pp moderate ΔFRR @ matched FAR (reshapes tail not mean) |
| 7 | **Enrollment-rep disagreement as an abstain signal** (reject when the user's own reps scatter) | ▶ | turns the wall's *cause* into a confidence gate; ≥8pp fewer hard errors at abstain <20% |
| 8 | **Score fusion** (pooled-cosine + frame-DTW + backend) | ▶ | complementary errors thin the tail even though no scorer alone does; ≥5pp ΔFRR |
| 9 | **QMF non-monotonic quality calibration** (duration/SNR/energy) | ▶ | the one P1 sub-lever not killed by monotone-invariance; ≥5pp ΔFRR |
| 10 | **Per-confusor-pair thresholds** w/ enrollment-time synthetic confusors (warp/splice own reps) | ▶ | ≥8pp moderate ΔFRR @ matched FAR |
| 11 | **Worst-confusor-aware enrollment** — 1–2 targeted extra reps on each command's nearest confusor | ▶ | ≥8pp moderate ΔFRR @ matched FAR |
| 12 | **Duration/rate prior** — reject on utterance-length inconsistency w/ enrollment | ▶ | cheap side-channel; ≥3pp ΔFRR @ matched FAR |
| 13 | **Rate-normalized frames before DTW** (reuse `f29` rate-norm embeddings) | ▶ | ≥5pp ΔFRR vs plain frame-DTW |
| 14 | **Online template update** across a session (test-time adaptation; reuse `f30` session data) | ▶ | ≥5pp ΔFRR by session end |

### Tier C — Representation, tail-targeted (encoder-invariance prior is strong → limited shots)

| # | Exp | Run | Hypothesis / success bar |
|--:|---|:--:|---|
| 15 | **LPM keyword-spotter latent-space frame-DTW** (not WavLM L14) | ◐ | tests whether the *space*, not the DTW, was missing; ≥8pp moderate ΔFRR |
| 16 | **Tail-loss adapter** — small head on soft-quantile/minDCF surrogate, cross-gender held-out | ▶ | ≥8pp moderate ΔFRR judged on tail (not AUC) |
| 17 | **Multi-sample DTW cost-tensor** (joint over all exemplars, vs best-of-min) | ▶ | ≥8pp moderate ΔFRR vs pooled |
| 18 | **Two-covariance / constrained PLDA** — one shot | ▶ | killed/banked on ≥8pp **tail** movement (not AUC, not transfer) |
| 19 | **Multi-layer WavLM fusion** for verification (concat vs single L14; `gsc_alllayers` cached) | ▶ | ≥5pp ΔFRR |
| 20 | **Personalized contrastive adapter** on the user's own within-word pairs, held-out speaker | ▶ | HIGH self-deception risk; strict tail kill-guard; ≥8pp ΔFRR |

### Tier D — Enrollment & data (enabling; high leverage on *confidence*; precondition to bank)

| # | Exp | Run | Hypothesis / success bar |
|--:|---|:--:|---|
| 21 | **Variance-aware exemplar selection vs augmentation** | ▶ | ≥5pp moderate ΔFRR at fixed rep count |
| 22 | **Dysarthric K-curve** (reps vs FRR at fixed FAR, per severity) + UX-fatigue cost model | ▶ | optimal K per severity with stated fatigue cost |
| 23 | **On-device enrollment augmentation** (tempo/pitch/noise) — child-ASV analogue | ▶ | ≥5pp moderate ΔFRR |
| 24 | **Acquire UASpeech** (larger graded cohort) | ⛔ | fixes n=8 single-speaker fragility; **REQUIRED before banking any positive** |
| 25 | **Acquire EasyCall (Italian)** | ⛔ | language-independence + LPM's public benchmark (#15) |
| 26 | **Acquire Nemours / SAP** | ⛔ | 3rd/4th population for cross-corpus transfer |

### Tier E — Complementary modality & product (severe tail; the honest route)

| # | Exp | Run | Hypothesis / success bar |
|--:|---|:--:|---|
| 27 | **Voice + switch/dwell/gaze late fusion** for severe | ◐ | severe task-success ≥85% @ FAR≤5% |
| 28 | **Confidence-gated voice** — use voice only when confident, else fall back to scan/dwell | ▶ | ≥85% task-success with voice used on ≥X% of turns |
| 29 | **Command-set co-design UX** — steer users to maximally-separable command words (confusion graph) | ▶ | ≥8pp moderate ΔFRR from vocab choice alone |
| 30 | **Longitudinal drift study** — does within-word variance / D2 improve as a user adapts? | ◐ | measurable D2 improvement over sessions/weeks |

## Definition of Done

Per executed experiment: an adjudicated verdict on the binding metric **stated as both FRR and realized
FAR** (never a bare %), or — for Tier A/E — as task-success + confirm/abstain-rate + FAR. BANKED only at the
per-experiment success bar above, on a held-out speaker, at matched FAR≤5%; else NULL/KILLED/NOT-BANKED with
numbers. Each lands a committed evidence JSON under
`scripts/eval/ssl_frontend_spike/_ceiling_cache/`. Program-level: if no Tier-B lever clears ≥8pp moderate at
matched FAR, the voice-only D2 wall is confirmed information-theoretic for moderate and the program commits
to Tier A + E.

## Risks & Mitigations

- **FAR inflation false positive** (the R3 trap) → every verdict prints realized held-out FAR (EVAL-007).
- **AUC mistaken for a tail win** → adjudicate on FRR@FAR; all-genuine AUC only as diagnostic (EVAL-007).
- **n=8 single-speaker fragility** (EVAL-005/006) → acquire UASpeech (#24) before banking any positive;
  per-severity cells reported with raw counts.
- **Same-family self-deception** (Tier C backends/adapters) → kill-guard is tail movement ≥8pp, not
  cross-gender survival (which P2-family passes); one representative shot each.

## Test & Verification

Verdicts computed by the R-series harnesses (`scripts/eval/ssl_frontend_spike/r1_frame_dtw_d2.py`,
`r2_backend_d2.py`, `r3_scorenorm_d2.py`, `n1_stack_d2.py`, `auc_unbiased.py`) and their extensions, which
print FRR **and realized FAR** per severity and flag FAR-invalid levers. Every banked positive requires a
fresh, pre-registered, FAR-matched confirmation on a held-out speaker (EVAL-002/003).

## First-session recommendation

Run the Tier-A/B ▶ set — **#1, #2, #3, #6, #7, #8** — first: all attack or reframe the tail with no new model,
and #1 (task-success-with-confirm) is the likeliest single move to convert "moderate is walled" into
"moderate is shippable."
