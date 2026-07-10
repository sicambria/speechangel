# D2-wall Round-5 — the 30-experiment program: Tier-B wall confirmed information-theoretic; the product lives in Tier-A reframe + Tier-E modality

**Date:** 2026-07-11 · **Corpus:** TORGO real dysarthric (moderate = M01/M02/F03), per-severity, held-out (LOFO)
**Plan:** `docs/plans/2026-07/d2-wall-next-30-experiments.md` (ranking companion to `d2-wall-followup-experiments.md`)
**Binding metric (advisor-locked, EVAL-007):** FRR @ FAR≤5%, held-out (LOFO), per severity, moderate-centered,
**FAR-matched** (realized held-out FAR printed on every verdict; a lever with realized FAR > 5%+2pp is FAR-INVALID).
**Fidelity gate (EVAL-004):** every new harness reproduces the A0 moderate baseline **62.7% FRR @ 4.9% FAR**
(= single-shot task-success 37.3%) before any lever is read.

> **Program decision (the deliverable, not 30 banks):** **No Tier-B tail-direct lever clears ≥8pp moderate
> FRR@FAR≤5%** — six score/calibration levers are all null-or-worse and two more were already refuted. Per the
> plan's own DoD this **confirms the voice-only moderate D2 wall is information-theoretic**, and the program
> **commits to Tier A (reframe) + Tier E (complementary modality)**. The Tier-A reframe lifts moderate from
> 37.3% single-shot task-success to **~65–73%** (confirm+retry / SPRT) — a large, real gain, but **short of the
> 85% "shippable" bar** under an honest confirm-error budget; the residual gap is the **rejection tail**, not
> confusion. **Every positive is NOT-BANKED pending UASpeech (#24, ⛔)** — the program's own precondition.

Harnesses (all committed): `x1_task_success_confirm.py`, `x23_reframe.py`, `x_taildirect.py`, `x8_fusion.py`,
`x_deploy.py`. Evidence JSON: `_ceiling_cache/{x1_task_success_confirm,x23_reframe,x_taildirect,x8_fusion,x_deploy}.json`.

---

## Bucketing of all 30 (honest coverage — nothing silently dropped)

- **▶ EXECUTED + adjudicated (17):** #1, #2, #3, #6, #7, #8, #9, #10, #12, #13, #14, #21, #22, #28, #29 (+#4/#5
  answered as by-products of the per-severity tables below).
- **◐ FEASIBILITY-GATED — needs a model/stream/data not present (10):** #11, #15, #16, #17, #18, #19, #20, #23,
  #27, #30. See "Feasibility gate" below. The representation axis (#16–#20) is additionally **prior-closed** by
  Round-4 (frame-DTW *lowers* separability) and #8 (fusion −3.4pp); one representative each is not worth spending
  before UASpeech.
- **⛔ BLOCKED — corpus acquisition, cannot run in-session (3):** #24 UASpeech, #25 EasyCall, #26 Nemours/SAP.
  **#24 is a hard precondition to banking ANY positive** — so the honest ceiling this session is NOT-BANKED.

---

## Tier A — Reframe the target (the highest-payoff bucket)

Accounting pinned **before** running (advisor lock — a confirm turn must not swallow errors for free): every
verdict reports task-success **jointly with** mean-turns / confirm-rate **and** residual FAR; the confirm turn is
imperfect with symmetric confirm-error `pc ∈ {0, .05, .10}` (pc=0 = optimistic bound; pc=.10 = plausible
dysarthric yes/no error, charged).

| # | Lever | Moderate result (binding, joint accounting) | Verdict |
|--:|---|---|---|
| **1** | **Task-success w/ ≤2 attempts + confirm** | fidelity 37.5%≈37.3%. At a *relaxed* threshold under **residual-FAR(pc=.1)≤5% & ≤3 turns**: **72.9% (pc=0) / 67.4% (pc=.1)** task-success, raw-FAR 15%, 2.41 turns. 85% only at pc=0 & raw-FAR 40% ⇒ residual-FAR 7.9% (over budget). | **reframe helps +30–36pp; NOT shippable (85%) under honest budget** |
| **2** | **SPRT / k-consistent multi-attempt** | k=2 consistency lets τ relax: **eff-FRR 35.4% (task-success ~65%) @ decision-FAR 3.2%, 2.31 turns** (best ≤2.0 turns: k=2,M=2 → 40.2% FRR @ 1.1% FAR). Floor ~35% eff-FRR even with more attempts. | **misses ≤15% eff-FRR bar; strongest single-family reframe** |
| **3** | **Abstain+confirm (conformal 3-way)** | relaxed confirm band: **47.9% task-success (pc=.1), abstain 39%, decision-FAR 5.9%**. | **dominated by #1; abstain 39% ≫ 20% bar** |

**Read:** all three Tier-A reframes converge on the same ceiling. The confirm/abstain/consistency mechanisms
absorb *confusions* and *false-accepts* (acc-wrong is only ~4% of moderate genuine), but the moderate tail is
**genuine-below-threshold (rejection ~62%)**, which they cannot rescue. Best deployable moderate operating points:
**SPRT k=2 (~65% task-success, 2.3 turns, decision-FAR 3.2%)** or **confirm+retry at a relaxed threshold
(~67–73%)**. Large gain over single-shot; not 85%.

> **Every reframe number here is an OPTIMISTIC upper bound — which only strengthens the "not shippable at 85%"
> verdict.** Three biases all point the same way: **(a) independent retries** — #1/#2 model the ≤2 attempts as
> independent draws, but a user whose utterance of *w* is systematically mis-scored has *positively correlated*
> attempts, so real task-success ≤ reported; #2's SPRT sim also resamples reps with replacement from a 2–4-rep
> pool. **(b) Teacher embeddings** — these are `wavlm-large` (the ~1.2 GB teacher), not the ≤150 MB deployable
> INT8 student, which is strictly worse. **(c) Single pooled threshold** — the frontier uses one pooled operating
> point. So the honest reading is "reframe is *at most* ~65–73%, probably lower on-device"; the 85% gap is
> **conservative**, and the commit to Tier A + E holds even under the pessimistic reading (voice-only single-shot
> is 37%, Tier B is dead). **This is also the concrete reason #24 matters:** UASpeech is what lets us *measure*
> the real retry correlation instead of assuming independence — the biggest single unknown in the reframe number.
>
> **Threshold-convention note (#1):** the fidelity anchor (37.3%) is a per-speaker-threshold average; the frontier
> (67–73%) uses a single pooled threshold, whose single-shot task-success is **33.4%**. The reframe lift is
> therefore **33.4% → 67–73% (≈ +34–40pp)** on a like-for-like pooled-threshold basis (the per-speaker anchor
> gives the same story from 37.3%).

## Tier B — Tail-direct decision / calibration (the program-critical bucket)

All FAR-matched (one global threshold fit on train negatives to FAR≤5%, held-out eval, realized FAR printed).

| # | Lever | Moderate ΔFRR @ matched FAR | Verdict |
|--:|---|--:|---|
| 6 | One-class **Mahalanobis** (diag-shrink) | **−9.5pp** (FAR 4.8%) | worse (cov is noise at k=4 reps) |
| 6 | **kNN-density** (k=2) | **−0.1pp** (FAR 4.6%) | null (k=2≈NN at 4 reps) |
| 7 | **Rep-disagreement abstain** (drop top-20% scatter) | kept-FRR 66.0% vs A0 62.7% | **enrollment scatter is a poor error-predictor** (see note) |
| 8 | **Score fusion** (pool + frame-DTW), FAR-matched | **−3.4pp** (FAR 5.8%) | frame-DTW drags fusion down (⇒ N1's +3pp was the FAR=9% artifact) |
| 9 | **QMF** non-monotone duration calibration | **−8.0pp** (FAR 4.8%) | hurts |
| 10 | **Per-confusor-pair** thresholds | +0.9pp but **FAR 9.4% — FAR-INVALID** | the R3 trap reproduced |
| 12 | **Duration/rate prior** | **−26.5pp** (FAR 4.9%) | dysarthric duration too variable |
| 13 | **Rate-normalized frames** | refuted (f29: AUC 0.68→0.45) | dead |
| 14 | **Online template update** | dead (f30: no within-corpus drift, dys-ratio 1.15) | dead |

**#7 note (metric):** the "kept-FRR vs A0" cell compares 80%-of-data (after abstaining the top-20% scatter) to
100%-of-data, so it is not a like-for-like FRR lever — its real finding is that **enrollment within-word scatter
does not predict which decisions fail** (abstaining on it removes as many correct as wrong decisions). Verdict —
scatter is not a useful confidence gate — stands.

**Program signal: best score-lever ΔFRR = −0.1pp; #7 scatter-gate is not a useful signal ⇒ NO Tier-B lever clears 8pp.** This
extends Round-4 (P1/P2/P3/N1) from 4 to **12 failed levers** on the moderate tail. Combined with the Round-4
finding that separability is mediocre everywhere (unbiased AUC ~0.65) and monotone-invariant to score maps, the
voice-only moderate D2 wall is **information-theoretic**.

## Tier C — Representation (feasibility-gated; prior-closed)

Round-4 already showed frame-trajectory DTW *lowers* unbiased AUC (0.65→0.61) and #8 shows pool+fdtw fusion is
−3.4pp. #16 (multi-sample DTW cost-tensor), #17 (TACos), #18 (LPM latent), #19 (posteriorgram DTW), #20
(personalized contrastive adapter) are variants on an axis that has now lost 3×. Per the plan's "limited shots"
and the advisor's "don't over-invest," these are **NOT run** before UASpeech — the EV is spent. #15/#17/#18/#19
also need models/benchmarks not present (see feasibility gate).

## Tier D — Enrollment (executed; low ceiling confirmed)

| # | Lever | Moderate result | Verdict |
|--:|---|---|---|
| 21 | **Exemplar selection** @ K=3 (first vs medoid vs diverse) | **0.0pp** — identical | null (test-variance dominates, not enroll choice) |
| 22 | **Dysarthric K-curve** (K=1→4) | **FRR 65.2% → 62.7%** (−2.5pp total) | **flat — more reps do NOT help moderate** |

**Read (important product finding):** unlike typical speakers (control K1→K4: 19%→11% FRR, a1_kcurve), **moderate
dysarthric FRR is nearly flat in K.** The wall is within-word *variability*, not enrollment sparsity — so **do not
burden dysarthric users with extra enrollment reps**; it doesn't move the tail. #23 (augmentation) is
feasibility-gated (needs re-embedding augmented audio through the WavLM encoder, not loaded here).

## Tier E — Complementary modality & product (the honest route)

| # | Lever | Moderate result | Verdict |
|--:|---|---|---|
| 28 | **Confidence-gated voice** (auto-accept @ auto-FAR≤1%, else scan/dwell) | **voice auto-handles 15.9% of moderate turns** (M01 11.6 / M02 18.2 / F03 17.8) | voice = minority fast-path for moderate; blended success via reliable fallback |
| 29 | **Vocab co-design** (most- vs least-separable command words) | in-sample **+9.0pp** → **held-out +5.4pp** | **DIRECTIONAL, generalizes cross-speaker, sub-8pp** |

**#29 integrity note (selection-on-test caught):** the in-sample +9.0pp used centroids computed from the same
reps being tested. The **held-out** version (rank words by separability on the *other* moderate speakers, apply to
the held-out one — the deployment reality, since vocab is chosen by word identity shared across users) shrinks it
to **+5.4pp**. Real, cross-speaker-generalizing, worth stacking — but sub-8pp and NOT-BANKED (pending #24).
#27 (voice + switch/dwell/gaze) and #30 (longitudinal drift) are feasibility-gated (no second-modality stream;
f30 already shows no within-corpus drift).

---

## Feasibility gate (◐ — what each blocked-on-model experiment needs)

- **#11 worst-confusor-aware enrollment** — needs *new targeted reps* on each command's nearest confusor (data
  collection during enrollment); not synthesizable honestly from existing reps.
- **#15 / #18 LPM latent-KWS** — needs the Lea/Apple IS2023 keyword-spotter latent encoder + its public benchmark.
- **#16 multi-sample DTW cost-tensor / #17 TACos / #19 posteriorgram DTW** — trajectory/representation models on
  an axis Round-4 + #8 already closed; prior-against, deferred.
- **#20 personalized contrastive adapter** — needs per-user contrastive training; HIGH self-deception risk;
  representation axis closed.
- **#23 on-device augmentation** — needs re-embedding tempo/pitch/noise-augmented audio through the WavLM encoder
  (encoder not loaded in the pooled-embedding harness).
- **#27 complementary-modality fusion** — needs a switch/dwell/gaze stream not present in TORGO.
- **#30 longitudinal drift** — needs multi-week per-user session data; f30 shows no within-corpus drift.

## ⛔ Blocked — corpus acquisition (the banking precondition)

- **#24 UASpeech** — larger graded cohort; fixes n=8 single-speaker per-severity fragility. **REQUIRED before
  banking any positive** (the +5.4pp vocab lever and the Tier-A operating points all wait on this).
- **#25 EasyCall (Italian)** — language-independence + LPM's public benchmark (unblocks #15/#18).
- **#26 Nemours / SAP** — 3rd/4th population for cross-corpus transfer.

## Method integrity (what makes these bankable negatives / an honest positive)

- **FAR-matched** verdicts only; the two FAR-inflation traps in the batch (#10 per-confusor 9.4%, N1 stack 9.1%)
  were caught and flagged, not headlined (EVAL-007).
- **Fidelity gate passed** — every new harness reproduced A0 = 62.7% FRR / 4.9% FAR (37.5% single-shot
  task-success) before a lever was read (EVAL-004).
- **Selection-on-test caught** — #29's in-sample +9.0pp was demoted to held-out +5.4pp before reporting (EVAL-003).
- **Reframe accounting charged** — task-success always joint with turns + residual FAR; confirm modeled with a
  non-zero error rate so it cannot swallow errors for free.
- **n=8 single-speaker fragility** — moderate = 3 speakers; these are directional negatives + one sub-bar
  directional positive, **not knife-edge positives** (EVAL-005/006). No positive banked (pending #24).

## Next levers (hypotheses to spike, not established results)

1. **Ship the Tier-A + Tier-E product** (voice-only moderate is walled): SPRT k=2 or confirm+retry as the default
   moderate loop (~65–73% task-success, ~2.3 turns), **stacked with vocab co-design (+5.4pp)** and a
   **confidence-gated fast-path** (voice on the ~16% high-confidence turns, scan/dwell otherwise).
2. **Acquire UASpeech (#24)** to bank the vocab lever and the operating points on a graded multi-speaker cohort.
3. **Severe (#27):** voice is not the modality — needs a real switch/dwell/gaze stream to test late fusion.
