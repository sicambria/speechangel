# Frame-pooling 30-experiment program — the composite is honestly capped at band 800 (deployment gap), and second-moment (std) pooling is the banked deployable-D2 lever

**Date:** 2026-07-11 · **Journey:** execute `docs/plans/2026-07/frame-pooling-next-30-experiments.md` (the
next 30 after the banked second-moment lever). · **Corpus:** GSC-19 (typical, npos=912) + TORGO (dysarthric
M01–M05 + F01/F03/F04). · **Binding metric (EVAL-007):** typical/dysarthric D2 = held-out (LOFO) FRR @
FAR≤5%, FAR-matched (realized held-out FAR on every verdict; McNemar re-thresholds both arms to a common FAR).
Bands (`DomainBands.kt` spec 2): 900 = ≤5%, 800 = ≤15%.

> **Headline.** The binary DoD asked: *is a deployable-config typical D2 < 5% reachable, without regressing
> the 900 domains?* Answer, decisively: **not this round — the composite is honestly capped at band 800 by
> the teacher→student deployment gap.** The band-900 result (teacher wavlm-large L12 **mean⊕std = 4.71%**) is
> **not deployable under the current admissibility bound** (wavlm-large INT8 ≈ 317 MB > the ≤150 MB bound,
> #1) and its 900 label is triple-gated anyway (deployability unresolved, cross-cohort label gate unrun,
> on-device INT8 unvalidated). **Every ≤150 MB config stays band 800:** best = distilhubert-L2 **std-alone
> 6.36%** (−32% rel vs mean 9.32%, McNemar b=10/c=41 @FAR5% p=2.7e-5), safe cross-encoder default **mean⊕std
> 8.22%**; wavlm-base-plus (94 MB) 6.91%. **The SOTA learned pooling loses:** attentive statistics pooling
> (ASP) **overfits at convergence (9.87%)** and is beaten by parameter-free std (p=1.5e-3) — the plan's
> pre-registered null, vindicated. **Higher moments and segmentation lose** (meanstdskew 9.65%, seg2 8.11%);
> **mean⊕std/std is the sweet spot of the parameter-free family.** **Dysarthric:** the second moment is
> **NULL on the deployment-relevant per-speaker metric** (mild+mod mean 48.8% vs meanstd 50.4%) — the two
> tails are confirmed different. **Distillation fails too:** distilling the stats-pooled teacher into a
> trained head on the deployable student = 9.32% (band 800) — so *post-hoc pooling AND distillation* both
> leave the deployable config at 800 (an EVAL-008-clean bank). **Banked:** second-moment (std) pooling as the
> **best deployable-D2 lever** (scoped to D2, 3-encoder-general); **composite stays 800**; **band-900 is
> blocked (not closed) on {cross-cohort label gate #2, teacher on-device feasibility + ≤150 MB cap audit,
> full-backbone distillation}**.

---

## 0. What ran vs what is blocked/deferred (honest coverage of the 30)

The binding question — *is a deployable band-900 reachable* — is answered for **post-hoc pooling** and (§7)
for **distillation**. Not all 30 ran; the split:

- **RAN & adjudicated (10):** #1 (fork), #4/#8 (per-encoder student confirm), #5 (deployable push), #7
  (distillation), #9 (D1 no-regression), #11 (ASP), #12 (multi-order moments), #13 (segment pooling), #15
  (per-layer stats fusion), #21/#22 (dysarthric second-moment).
- **RUNNABLE, not run this session (3):** #2 (cross-cohort — the EVAL-005 label gate; **the single most
  important unrun experiment** — no disjoint ≥15-speaker typical cohort is cached), #3 (larger-n cohort), #6
  (std × few-shot-K).
- **DEFERRED — code/eval work, no measurement blocker (5):** #10 (D4/D5/D6 channel no-regression — needs
  augmented-frame extraction; **the gate std-global-adoption needs**), #16 (SE-attention), #17–#20 (Tier-E
  production-Kotlin — see §9), #29/#30 (composite re-score + docs — this report).
- **CORPUS-BLOCKED (⛔, 2):** #24/#28 (UASpeech — gates the dysarthric positives), #14 (NetVLAD, low prior),
  #23/#25/#26/#27 (dysarthric ASP / interactions — folded into §8 or UASpeech-gated).

## 1. #1 — The deployable-config fork resolves to the STUDENT (size-measured; latency/battery + cap audit open)

The repo carried two conflicting notions of "the shipped config" (population-split report = wavlm-large
teacher behind the VAD gate; frame-pooling report = ≤150 MB INT8 student). The DoD is ill-formed until one is
fixed. INT8 size (1 byte/param):

| encoder | params | fp32 MB | **INT8 MB** | ≤150 MB INT8? |
|---|--:|--:|--:|:--:|
| wavlm-large (teacher) | 316.6 M | 1266 | **317** | **NO — over bound** |
| wavlm-base-plus | 94.4 M | 378 | 94 | yes |
| hubert-base | 94.6 M | 378 | 95 | yes |
| distilhubert (student) | 23.5 M | 94 | 24 | yes |

**Verdict:** under the current ≤150 MB admissibility bound the **teacher is out**, so the composite is banded
on the **≤150 MB student**. Two honesty caveats (advisor): (a) this measured **size only** — the plan's #1
also specified on-device **latency/battery** (D11/D12), **not validated here**; (b) the ≤150 MB bound is
itself a **CONSTRAINT-001 audit item** (a 317 MB INT8 model is ~8% of a 4 GB phone's RAM behind a VAD gate —
arguably admissible). So the precise claim is **"teacher out *under the current bound* (provisional)"**, not
"teacher undeployable (measured)." Either way §4 shows the composite is 800 today regardless of the cap.

## 2. Fidelity gate (EVAL-004)

Every GSC arm reuses `frame_qbe.py`'s manifest/folds/K/threshold machinery; the `mean` pooling cell
reproduces the baseline (frames_norm-mean **5.70%** ≈ mean-pool 5.81%; meanstd reproduces the banked 4.71%).
Dysarthric arms reuse `r1_frame_dtw_d2`'s LOFO rows (the `mean` scorer is r1's exact shipped mean-pooled
cosine). Change-one-variable throughout: only the pooling differs.

## 3. #5 — No parameter-free-pooled ≤150 MB config reaches < 5% (the composite gate)

Deployable students, held-out FRR @ FAR≤5%, K5 (std = the banked deployable pooling; mean⊕std = the safe
cross-encoder default):

| encoder (size) | mean | **std** | mean⊕std | band | note |
|---|--:|--:|--:|:--:|---|
| **distilhubert (24 MB)** | 9.32% | **6.36%** | 8.22% | **800** | std-alone best; confirm McNemar b=10/c=41 @5% p=2.7e-5, 12 better/0 worse/7 tie |
| wavlm-base-plus (94 MB) | 8.77–10.42% | 6.91% (L8, mined) / 8.11% (L12) | 6.91% | **800** | std win is **layer-dependent** — clean at L8, null at the mean-optimal L12 (b=18/c=8 ns) |
| — teacher wavlm-large (317 MB, **not deployable**) | 5.81% | 5.92% | **4.71%** | 900 | aspirational ceiling; §1/§4 |

**No deployable cell clears the band-900 line (≤5%).** The best deployable is distilhubert std-alone
**6.36% @ FAR 3.38%** (band 800). The second moment beats mean on **all three encoders** (confirms the banked
lever generalizes to a third encoder), but the specific winning variant is encoder×layer-specific
(**NOT-banked per-encoder tuning**, as the frame-pooling report flagged) — the robust, safe default is
**mean⊕std**.

## 4. Why the composite is band 800 *today* under either reading of the cap

The band-900 teacher number (4.71%) does not move the composite band this round, independent of the cap
debate, because its 900 label is **triple-gated**:

1. **Deployability unresolved** (§1 — size over the current bound; latency/battery + cap audit open).
2. **Cross-cohort label gate (#2) NOT run.** 4.71% clears 900 by ~2.6 false-rejects on one 19-speaker cohort
   — a textbook EVAL-005 curve-extreme knife-edge; **no band-900 label is bankable until it replicates on a
   disjoint cohort**, which was not run (no disjoint ≥15-speaker typical cohort is cached).
3. **On-device INT8 accuracy unvalidated** (the caveat the 4.71% inherited from the 5.81%).

⇒ **Composite = band 800 today.** The banked *improvement* (second-moment pooling) holds; the discrete
band-900 label does not.

## 5. #11 — Attentive statistics pooling (ASP, learned): the pre-registered NULL is confirmed

ASP (learned frame-attention over mean+std, 4-fold cross-speaker held-out, EVAL-006) on the deployable
distilhubert-L2 student:

| training | ASP held-out FRR | vs std-alone (6.36%) | vs mean (9.32%) |
|---|--:|---|---|
| 20 steps (under-trained) | 6.58% | ≈ tie / slight McNemar edge (p=2e-3) | ASP better (p=8e-11) |
| **400 steps (converged)** | **9.87%** | **std BEATS ASP** (b=44/c=18 @5%, p=1.5e-3) | ≈ tie |

**ASP overfits with training and loses to parameter-free std at convergence.** The 20-step edge is an
under-trained lucky operating point with **no held-out criterion to select it** — banking it would be
selection-on-training-budget. Neither budget reaches <5%. This is **exactly the plan's pre-registered null**
("a learned pooling head can overfit the tiny few-shot regime and lose to parameter-free mean⊕std") —
**vindicated**. Scope: **one representative ASP shot** (att=64, prototypical loss); its hyperparameters were
not exhaustively searched, so this refutes "ASP helps *here*", not "ASP is impossible".

## 6. #12/#13/#15 — mean⊕std is the sweet spot of the parameter-free family

All on the teacher (wavlm-large L12), exploratory screen (EVAL-003 family, `mean` reproduces baseline):

| variant | FRR | vs mean⊕std (4.71%) | verdict |
|---|--:|---|---|
| mean (anchor) | 5.70% | — | fidelity ✓ |
| **mean⊕std** | **4.71%** | — | banked lever |
| #12 mean⊕std⊕skew | 9.65% | +4.9pp | **worse** — higher moments are noisy per-dim |
| #12 +kurtosis | 10.42% | +5.7pp | **worse** |
| #13 segment-wise (seg2) | 8.11% | +3.4pp | **worse** — temporal split fragments the stats |
| #13 seg3 | 9.76% | +5.0pp | **worse** |
| #15 per-layer stats fusion [9,12,15] | 4.39% | −0.3pp | **mined** (best-of-4 combos, teacher-only, NOT-banked, EVAL-005) |

**Adding dimensions to the cosine dilutes it** — the second moment (global mean⊕std) is the parameter-free
ceiling. #15's [9,12,15] edge is a best-of-4-combos selection on one test fold (and teacher-only), not banked.

## 7. #7 — Distillation with a stats-pooled teacher (the EVAL-008 different-substrate check)

_Distills the wavlm-large mean⊕std teacher (2048-d, 4.71%) into a trained attentive-pool+projection head on
the frozen distilhubert-L2 frames; 4-fold cross-speaker held-out; adjudicated vs post-hoc std (6.36%). Scope:
the backbone is frozen (full SSL-backbone distillation is out of host budget) — this is "the pooling objective
baked in" on the deployable features, not a full re-pretrain._

**Result (500 steps, held-out):** the distilled head = **9.32%** FRR @ FAR≤5% (band 800) — **worse than
post-hoc std (6.36%)** and not <5% (post-hoc std better; @FAR5% b=23/c=14, p=0.19 ns). It improved with
training (40 steps 12.17% → 500 steps 9.32%) but converges *above* the parameter-free lever. **Verdict:
head-level distillation of the stats-pooled teacher does NOT reach a deployable band-900 either.** So — the
EVAL-008-clean bank — **both substrates fail**: *post-hoc pooling of a frozen student* (§3) **and**
*distillation of the stats-pooled teacher into a trained head* (§7) leave the deployable config at band 800.
**Scope (kept honest):** this froze the backbone and trained a pooling+projection head; a **full SSL-backbone
re-pretrain** distilling the stats-pooled teacher is the one distillation substrate **not** tested (out of
host budget) — so the negative is "head-level distillation fails", not "distillation is walled".

## 8. #21/#22 — Second-moment on the dysarthric D2 tail: NULL (the two tails are different)

TORGO, wavlm-large L14, males carry the D2 verdict (moderate = M01/M02, the live population), females =
cross-gender AUC context (their frame cache has no negatives). Per-speaker LOFO FRR @ FAR≤5%:

| speaker | severity | mean | std | mean⊕std |
|---|---|--:|--:|--:|
| M03 | mild | 29.2% | **18.8%** | 28.1% |
| M01 | moderate | 59.3% | 69.8% | 61.6% |
| M02 | moderate | 58.0% | 67.0% | 61.4% |
| M04 | severe | 82.9% | 78.0% | 82.9% |
| M05 | very severe | 72.8% | 72.2% | 78.8% |
| **mild+moderate mean** | | **48.8%** | 51.9% (−3.0pp) | 50.4% (−1.6pp) |

**Verdict: NULL on the deployment-relevant per-speaker banding metric** — the second moment does **not**
breach the dysarthric wall. It is speaker-inconsistent (helps mild M03 29→19%, **hurts** the moderate live
population M01/M02) — the EVAL-006 dysarthric sign-flip. **The two tails are confirmed different:** the moment
recovers typical hard-voice information the mean discards (5.81→4.71) but cannot rescue **corrupted** dysarthric
within-word scatter at a per-user operating point — which *strengthens* the information-theoretic bank.

**A real but differently-scoped signal (kept, not dismissed):** at a **shared global threshold** the matched-FAR
McNemar shows mean⊕std strongly dominant (males @FAR5% mean 74.4% vs mean⊕std 65.6%, **b=0/c=44, p=9e-11**) —
i.e. the moment is a genuine **cross-speaker calibration** signal (mean⊕std distances are better-calibrated
*across* speakers). It **washes out under per-user thresholds** (deployment calibrates per speaker), so it is
not a per-user dysarthric tail lever. **NOT-BANKED pending UASpeech** (#28) regardless (n=3 mild+moderate).

## 9. #9 — D1 no-regression (partial gate); global adoption still gated on D4/D5/D6

Clean GSC-19 closed-set rank-1 (threshold-free, the D1 analogue): mean 97.70%, **std 98.25%**, mean⊕std
97.70%. **std does not regress D1** (slightly better). But global-default pooling adoption changes *every*
domain's embedding, and the advisor-flagged risk is the **channel domains** (std = within-word dispersion,
which noise/reverb **inflate**): **#10 (D4/D5/D6 no-regression) was NOT run** (needs augmented-frame
extraction). So the std bank is **scoped to D2**; adopting it as the *global* pooling default is gated on #10.

## 10. Banked / not-banked / scope

- **BANKED (measured):** second-moment **(std) pooling is the best deployable-D2 lever** — distilhubert-L2
  9.32→**6.36%** (−32% rel, McNemar p=2.7e-5), **3-encoder-general** (distilhubert + wavlm-base-plus +
  wavlm-large all show std/mean⊕std < mean somewhere). Safe cross-encoder default = **mean⊕std**. Passes D1
  no-regression. **Scoped to D2**; band **800**.
- **BANKED (negatives):** **ASP loses** (overfits, 9.87% converged; null confirmed). **Higher moments and
  segmentation lose** (mean⊕std is the parameter-free ceiling). **Dysarthric second-moment is NULL** on the
  per-user metric (the two tails are different).
- **NOT banked:** the discrete **band-900 label** (teacher 4.71% — not deployable under the current bound +
  cross-cohort unrun + INT8 unvalidated); per-encoder best variant (std vs mean⊕std) and best layer (mined);
  #15 per-layer fusion (teacher-only, best-of-combos); every dysarthric positive (pending UASpeech).
- **Composite: STAYS band 800.** Band-900 is **blocked, not closed** on {the cross-cohort label gate #2,
  teacher on-device feasibility + the ≤150 MB cap audit (CONSTRAINT-001), full-backbone distillation}.
  Head-level distillation (§7) is now a **run negative**, not an open blocker.

## 11. Method integrity

EVAL-004 (fidelity anchors reproduce 5.70%/4.71% on GSC and r1's mean on TORGO; one variable per comparison) ·
EVAL-003 (screens are exploratory families; the student std lever and ASP were pre-registered and confirmed/
refuted on fresh cross-speaker folds) · EVAL-005 (band-900 label flagged knife-edge; #15 oracle-combo not
banked) · EVAL-006 (ASP + distillation trained on disjoint speakers; dysarthric cross-gender) · EVAL-007
(adjudicated on FRR@matched-FAR, AUC diagnostic only) · EVAL-008 (the negative is scoped to *post-hoc pooling
of frozen encoders*; distillation §7 tests the different substrate before any "walled" claim).

## 12. Next levers (hypotheses, not results)

1. **Cross-cohort replication (#2)** — the unrun EVAL-005 label gate; without it no band-900 label is bankable.
2. **Channel no-regression (#10)** — extract augmented frames; gates global std-pooling adoption.
3. **Teacher on-device feasibility + ≤150 MB cap audit (CONSTRAINT-001)** — if a 317 MB INT8 SSL encoder is
   admissible behind the VAD gate, the deployable-teacher path to band 900 reopens (then #2 gates the label).
4. **Full-backbone distillation** of the stats-pooled teacher on large data (the one distillation substrate
   §7 could not test on this host) — the only remaining shot at a <5% deployable student.
5. **UASpeech (#28)** — banks/refutes the dysarthric positives and the cross-speaker-calibration signal.

**Artifacts:** `scripts/eval/ssl_frontend_spike/frame_qbe.py` (e4 modes + confirm),
`scripts/eval/ssl_frontend_spike/asp_pool.py`, `scripts/eval/ssl_frontend_spike/distill_stats.py`,
`scripts/eval/ssl_frontend_spike/d2_second_moment.py`; evidence JSONs under
`scripts/eval/ssl_frontend_spike/_ceiling_cache/` (measure-only, uncommitted):
`frame_qbe_e4_L{12}.json`, `frame_qbe_confirm_{distilhubert_std,wavlm-base-plus_std}_L*.json`,
`asp_pool_distilhubert_L2.json`, `distill_stats_distilhubert.json`, `d2_second_moment.json`.
