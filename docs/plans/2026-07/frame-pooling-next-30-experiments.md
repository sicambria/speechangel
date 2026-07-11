# Frame-level pooling — next 30 experiments (ranked by EV toward composite-900)

**Status:** planned (authored 2026-07-11; advisor-gated). Successor to the banked frame-pooling journey
(`docs/testing/2026-07-11_frame-pooling-second-moment.md`). Executes the four named next levers —
attentive statistics pooling, cross-cohort replication, production-Kotlin std pooling, and second-moment
on the dysarthric D2 tail — inside a single binary Definition of Done.

## Where we are (the one-paragraph state)

Typical composite = **band 800, gated by D2 alone** (un-walled, AUC 0.988; D5-reverb and D3-ambient were
resolved to band 900 by the 2026-07-11 confound-resolution — do **not** reuse the population-split's stale
three-way tie). Frame-level **second-moment (std) pooling is BANKED** as a lever: teacher wavlm-large L12
**5.81 → 4.71% FRR @ FAR≤5%** (−19% rel, McNemar p=1.4e-4, both cohorts), deployable distilhubert student
**9.32 → 8.22%**. But the composite **stays 800** for two reasons this program must resolve: (a) the
**deployable student is band 800** (8.22%), and (b) the teacher's 4.71% clears the band-900 line (≤5%) by
only **~3 false-rejects on one 19-speaker cohort** — a textbook curve-extreme knife-edge (EVAL-005), so the
**900 label is provisional / unbankable** until it replicates on a disjoint cohort. Dysarthric voice-only
D2 is a **confirmed information-theoretic wall** (12 dead levers, AUC ~0.65); the second moment has **never
been tested there**.

---

## Goal — define the win (binary DoD; every experiment ranked by how much it moves it)

> **composite-900 ⟺**
> **(1) a _deployable-config_ typical D2 < 5% FRR @ FAR≤5%, cross-cohort stable (≥2 disjoint cohorts, same
>   direction — EVAL-005), _AND_**
> **(2) mean⊕std / the chosen pooling does NOT regress the currently-900 domains D1 / D4 / D5 / D6 on their
>   own metrics.**

Both clauses are hard. Clause (1) has two independent gates that are **co-priority**:

- **The LABEL gate (cross-cohort):** 4.71% is a ~3-FR knife-edge on n=19. Until mean⊕std replicates
  same-direction on a **disjoint** cohort, no band-900 label is bankable *regardless of what else wins*
  (EVAL-005). → **Tier A.**
- **The COMPOSITE gate (deployable config):** the shipped recognizer's D2 is what bands the composite. Which
  config ships is **currently undefined in the repo** (see §"Definitional fork") — resolving it changes the
  target by an order of magnitude. → **Tier 0 settles it; Tier B pushes it.**

**A valid banked outcome includes the negative:** if no deployable config reaches robust <5% even with ASP
and the best ≤150 MB encoder, the composite is **honestly capped at 800 by the teacher→student deployment
gap** — that is a trustworthy result, not a failure (journey step 9).

## The definitional fork (resolve FIRST — it re-ranks everything)

The repo carries **two conflicting notions of "the shipped config"** and the DoD is ill-formed until one is
chosen:

| Convention | Shipped D2 today | This program's job | Cost |
|---|---:|---|---|
| **Teacher** — wavlm-large behind the VAD gate (population-split report's basis) | **4.71%** (band-900 knife-edge) | just **replicate cross-cohort** (Tier A) | cheap |
| **Student** — ≤150 MB INT8 encoder (frame-pooling report's basis) | **8.22%** (band 800) | push a 94 MB student **8.2% → <5%** (Tier B) | hard |

**Experiment #1 settles it** by measuring wavlm-large's *actual* INT8 on-device feasibility on a 2026
sub-300 EUR phone (CONSTRAINT-001). A YES collapses the whole program to Tier-A cross-cohort replication; a
NO makes the student the binding config and Tier B the main event. **Do not rank the other 29 until #1 is
answered.**

## Context & Constraints

- **Binding metric (EVAL-007):** typical D2 = held-out (leave-one-fold-out) **FRR @ FAR≤5%, FAR-matched**
  (realized held-out FAR printed on every verdict; McNemar re-thresholds both arms to a common realized
  FAR). Bands (`DomainBands.kt` spec 2): 900 = ≤5%, 800 = ≤15%. Adjudicate on FRR@FAR; AUC diagnostic only.
- **Admissibility (hard filter, unchanged):** on-device, speaker-dependent, language/vocab-agnostic,
  few-shot, **deterministic** (frozen weights at ship — the Play-policy line; a learned pooling head is
  admissible only frozen), NNAPI/INT8 ≤~150 MB. Real corpora only (no simulator for a banked number).
- **Two rigor buckets:** *parameter-free* pooling (std, moments, VLAD-with-fixed-anchors) confirms with a
  fresh FAR-matched McNemar. *Learned* pooling (ASP, attention, adapters) additionally needs **disjoint-
  speaker training + EVAL-006 cross-demographic held-out** — ASP-trained-on-eval-speakers vs mean⊕std is a
  confounded comparison, and in a tiny-training few-shot regime a learned head can **overfit and lose** to
  parameter-free mean⊕std. Pre-register the null for every learned lever.
- **EVAL-008 scope discipline:** the frame axis is now **open and productive**; do not launder any new
  negative into "pooling axis closed" — scope each to the specific pooling substrate it varies.
- **Runnability:** ▶ runnable now (frames cached: `gsc_wavlm_large_frames_L{6,9,12,15}.npz`,
  `gsc_distilhubert_frames_L{1,2}.npz`; torch + encoders present for fresh extraction) · ◐ needs a
  prototype/model/frame-extraction pass or a device · ⛔ needs a corpus or hardware not present.

## Approach

Seven tiers, run in EV order toward the binary DoD, **but the ranking is conditional on Tier 0** (the
deployable-config fork re-ranks everything). Once the convention is fixed, the two composite-900 clauses are
attacked by **co-priority** tiers — Tier A gates the band-900 *label* (cross-cohort), Tier B pushes the
deployable config to move the *composite*, and Tier C is the *gate* both must clear (no channel regression).
Tier D deepens the newly-open pooling axis (SOTA variants — flagged where they move only the teacher); Tier E
ships the banked lever in production Kotlin (A-bucket, no measurement dependency); Tier F characterizes the
dysarthric wall with the second moment (NOT-bankable until UASpeech); Tier G is interactions + enabling
corpora + synthesis. The first-session discriminating subset (below) is sufficient to decide the binary DoD.

## Steps

### Tier 0 — Settle the deployable convention (gates the entire program's target)

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 1 | **wavlm-large INT8 on-device feasibility** — export the encoder INT8 (`onnx_export.py`), measure size + per-utterance latency behind the VAD gate on the emulator scaled by the cited `DEVICE_SCALE=2.6` (D11) + a first-principles battery delta (D12), vs the ≤150 MB / latency / battery budgets. | ◐ | **Binary verdict** that fixes "the shipped config". YES (fits a 2026 sub-300 EUR phone, CONSTRAINT-001) ⇒ target = replicate teacher 4.71% cross-cohort; NO ⇒ target = deployable student <5%. Deliverable: size/latency/battery table + the convention decision. **Run before ranking #2–#30.** |

### Tier A — Bank the band-900 LABEL: cross-cohort replication of mean⊕std (the EVAL-005 gate; co-#1)

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 2 | **Cross-cohort replication of mean⊕std** on a **disjoint** typical cohort — the relaxed-bar GSC-6 set (the 6 speakers below the strict rep bar) + a second word-repeat corpus. Frozen config (L12/K5, mean⊕std, cosine 1-NN). | ▶/◐ | mean⊕std beats mean same-direction, FAR-matched McNemar, on a cohort with **no speaker overlap** with GSC-19. **This is the gate that de-provisionalizes the band-900 label** (EVAL-005: ≥2 disjoint cohorts agree). Null here ⇒ the label stays provisional even if the improvement replicates in magnitude. |
| 3 | **Larger-n cohort for the knife-edge** — mine a ≥40-speaker word-repeat set (MSWC keyword corpus / Common-Voice repeated tokens) so the ~3-FR band-900 label rests on more than 19 speakers. | ◐ | band-900 label **stable** (teacher <5% with a per-speaker CI that does not straddle the line) on n≥40. Directly attacks the EVAL-005 fragility the report flagged. |
| 4 | **Per-encoder std-vs-mean⊕std pre-registered confirm** — the report left the best *variant* (mean⊕std best on wavlm-large; std-alone best on distilhubert) as **NOT-banked mined tuning**. Pre-register per-encoder and confirm on fresh folds. | ▶ | closes the mined-tuning gap: a pre-registered per-encoder winner, FAR-matched, or an honest "variant is within noise, ship mean⊕std as the safe default". |

### Tier B — Move the COMPOSITE: push the deployable student < 5% (the composite gate)

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 5 | **Joint deployable push** — grid `{best ≤150 MB encoder (wavlm-base-plus 94 MB was best in C3) × pooling (std / mean⊕std / ASP) × few-shot K}`, pre-registered, held-out. Extract frames for the deployable encoders. | ▶/◐ | **the composite-gate experiment.** Any deployable config reaches **robust <5%** ⇒ composite 900 candidate. If none does even at best-encoder × ASP × best-K ⇒ **composite honestly capped at 800** (banked negative). |
| 6 | **Second-moment × few-shot-K interaction** — does std pooling lower the ~5% K-plateau (K6/K7 flattened at ~5% with mean-pool) or move the band-900 crossover to a **deployable** K? | ▶ | band-900 at a deployable K with std, or an honest "std shifts the whole curve down by a fixed offset but the plateau shape is unchanged". |
| 7 | **Distillation with a stats-pooling teacher** — distill wavlm-large **mean⊕std** into a ≤150 MB student with the pooling objective baked in (`distill_student.py`), vs post-hoc std on a mean-trained student. | ◐ | closes the teacher→student gap (4.71 vs 8.22). Student **<5%** ⇒ composite 900 without shipping the teacher. |
| 8 | **Student-specific pooling** — the moment that wins flips by encoder (std-alone best on distilhubert). Pre-register the deployable student's own best pooling on fresh folds. | ▶ | the deployable student's banked pooling variant, FAR-matched (not mined). |

### Tier C — The NO-REGRESSION gate (must pass before banking std pooling globally)

> It is **one shipped recognizer**: changing the pooling changes *every* domain's embedding. std = within-word
> dispersion, which noise/reverb/band-limit **inflate** — so mean⊕std plausibly **hurts** the channel domains
> and could lower the composite even while D2 improves. This is a **gate**, not a nice-to-have.

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 9 | **No-regression on D1 rank-1 (clean)** under mean⊕std | ▶ | D1 rank-1 not worse than the mean-pool 900 baseline (≥ its own band-900 threshold). |
| 10 | **No-regression under channel stress D4/D5/D6** (noise 20 dB, reverb rt60≈250 ms, band-limit 300–3400 Hz) under mean⊕std | ▶/◐ | each of D4/D5/D6 holds band 900 on its own metric. **A regression here blocks a global bank** — fall back to std-pooling-for-D2-only if it survives per-domain. |

### Tier D — Deepen the pooling axis (SOTA variants; ⚠ mostly moves the TEACHER unless it moves the deployable config)

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 11 | **Attentive statistics pooling (ASP)** — learned frame weights over mean+std (the SOTA of this axis; **named lever #1**). Pre-registered **skeptically**: disjoint-speaker training, EVAL-006 cross-demographic held-out, frozen at ship. | ◐ | ASP > mean⊕std, held-out, FAR-matched, on the **deployable** encoder — or the pre-registered **null** (learned head overfits the tiny few-shot regime and loses to parameter-free mean⊕std). Both bankable. |
| 12 | **Multi-order moments** — mean⊕std⊕skew (⊕kurtosis); parameter-free. | ▶ | ≥3pp over mean⊕std, or "2nd moment is the ceiling of this family". |
| 13 | **Segment-wise / multi-scale statistics pooling** — split each utterance into S segments, pool each, concat (recovers temporal structure global std discards). | ▶ | ≥3pp over global mean⊕std. |
| 14 | **NetVLAD / GhostVLAD-lite aggregation** — the other SOTA speaker-verification aggregation family; fixed anchors = parameter-free-ish. | ◐ | ≥3pp over mean⊕std. |
| 15 | **Per-layer stats-pooling fusion** — compute mean⊕std **per layer**, concat top-K layers (multi-layer fusion was closed on mean-pool, **untested on std** — EVAL-008 untested corner). | ▶ | ≥3pp over single-layer mean⊕std. |
| 16 | **Channel-attention (SE-style) before stats pooling** — lighter learned variant than full ASP; frozen at ship. | ◐ | ≥3pp over mean⊕std at a fraction of ASP's parameters; else prefer parameter-free. |

### Tier E — Production-Kotlin std pooling (named lever #3; A-bucket — ships the banked lever, no measurement needed)

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 17 | **Implement mean⊕std / std pooling in `QbeSpeechBackend`** — `Qbe.kt` `meanNormalized` → a `PoolingMode`-selected `meanStdNormalized`, behind a config flag (default mean for safety until banked). | ▶ | `:core:enrollment:test` green; `make verify` green; the banked lever is now expressible in the shipped recognizer. |
| 18 | **Kotlin↔Python parity/fidelity test** (EVAL-004 for the production path) — the Kotlin std pooling reproduces the Python `frame_qbe.py` FRR on a committed fixture. | ▶ | parity within tolerance on a fixture; a `RecognizerPoolingParityTest`. |
| 19 | **2×-wide template vector through storage** — `FeatureCodec` / Room width for the concatenated mean⊕std vector (the only stated cost of the lever). | ▶ | codec round-trips the 2H vector; migration test green. |
| 20 | **On-device INT8 latency / size / battery delta** of the 2×-wide stats-pooled student (D11/D12) vs the mean-pool baseline. | ◐ | the 2×-wide vector + std computation stays within the latency/battery budget; deploy-validated. |

### Tier F — Second-moment on the dysarthric D2 tail (named lever #4; wall-CHARACTERIZATION — NOT-bankable until UASpeech *regardless of outcome*)

> Frames it as **wall characterization, not a wall-break bet.** A **null is bankable-as-characterization**:
> it separates "recoverable hard-voice info the mean discards" (typical, where std won) from "corrupted
> disorder scatter" (dysarthric, where the info itself is degraded) — sharpening the information-theoretic
> bank. A win would reopen the dysarthric route (huge). Either way, **all positives are NOT-BANKED until
> UASpeech (#28)** and every lever needs **EVAL-006 cross-gender held-out**.

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 21 | **mean⊕std on moderate dysarthric TORGO** — the exact banked lever, on the AUC-0.65 wall. | ▶ | honest verdict: ≥8pp @ matched FAR (cross-gender held-out) = wall breach; null = characterization ("moment helps typical hard-voice, not disorder scatter → different tails"). |
| 22 | **std-alone / higher-moment on dysarthric** — if mean⊕std is null, does discarding the *corrupted mean* (std-alone) differ? | ▶ | secondary characterization; same NOT-banked-until-UASpeech caveat. |
| 23 | **ASP on dysarthric** — does *learning* which frames matter suppress the high-variance corrupted frames? **⚠ single highest false-positive risk in the program** (n=8, learned head, hardest tail). | ◐ | **strict EVAL-006 cross-gender held-out or DO NOT RUN.** Bar: ≥8pp moderate, held-out, FAR-matched. Default expectation = overfits/null. |
| 24 | **Within-word std as an abstain/confidence gate** on dysarthric — the wall's *cause* (high within-word scatter) is exactly a per-command confidence signal; reject/confirm when a user's own reps scatter (ties to the Tier-A+E product route in `d2-wall-30-experiment-program`). | ▶ | turns the wall's cause into a reject signal: ≥8pp fewer hard errors at abstain <20%, or null. |

### Tier G — Interactions, enabling corpora, synthesis

| # | Exp | Run | Hypothesis / success bar · DoD |
|--:|---|:--:|---|
| 25 | **Second-moment × multi-condition enrollment** — the composite already uses noise/reverb-augmented enrollment; is std pooling **additive** on top, or redundant with it? | ▶ | ≥3pp on top of aug-enroll (additive) or an honest "redundant — pick one". |
| 26 | **OSS survey + adopt a proven ASP/pooling impl** (SpeechBrain / WeSpeaker / asteroid statistics + attentive pooling; Apache/MIT) **before** hand-rolling #11/#16 (journey step 2). | ▶ | an adopted, license-cleared reference impl (or a documented gap justifying build). Precondition to #11. |
| 27 | **Hard-speaker-tail root-cause (typical)** — the 2–3 hard GSC speakers carry the residual; is their std-pooling residual a specific phoneme/confusor-pair or global? | ▶ | diagnostic that routes the *next* lever (e.g. targeted vocab co-design vs a per-speaker calibration). |
| 28 | **Acquire UASpeech** (⛔; graded dysarthric cohort) — gates banking any Tier-F positive; fixes the n=8 single-speaker fragility. Same blocker as `uaspeech-acquisition.md`. | ⛔ | corpus in hand ⇒ Tier-F positives become bankable. |
| 29 | **Composite re-score with the banked lever** — run `SotaScorecard` / `typical_composite.py` with the chosen pooling in the D1/D2/D4/D5/D6 pipeline (gated by the Tier-C no-regression result). | ▶ | the composite either moves to 900 (both DoD clauses pass) or is banked at 800 with the binding clause named. |
| 30 | **SOTA-reference + memory update** — record the stats-pooling result and its place vs x-vector / ASP prior art in `docs/product/2026-07-08_sota-wake-word-reference.md` §11; update the memory with the banked verdict + next lever. | ▶ | docs/memory synced to the banked state (journey step 10). |

---

## Definition of Done (per experiment + program-level)

- **Per experiment:** an adjudicated verdict on the binding metric **stated as both FRR and realized FAR**
  (never a bare %), FAR-matched, held-out (LOFO). BANKED only at the per-experiment success bar on a
  held-out cohort; else NULL / KILLED / NOT-BANKED **with numbers**. Each lands a committed evidence JSON
  under `scripts/eval/ssl_frontend_spike/_ceiling_cache/`. Learned levers additionally report EVAL-006
  cross-demographic held-out.
- **Program-level (the binary DoD):** the composite moves to **900 iff** a *deployable* config reaches robust
  <5% cross-cohort **and** mean⊕std does not regress D1/D4/D5/D6 — else the composite is **banked at 800**
  with the binding clause named (deployment gap and/or channel regression and/or label fragility). A
  trustworthy negative closes the program as validly as a win.

## Risks & Mitigations

- **Curve-extreme knife-edge banked as a label** (EVAL-005) → Tier A gates the band-900 label on ≥2 disjoint
  cohorts before any 900 claim; #3 adds n≥40.
- **Learned-head self-deception** (ASP, #11/#16/#23) → disjoint-speaker training + EVAL-006 cross-demographic
  held-out; pre-register the null; frozen weights at ship (determinism / Play-policy line).
- **std regressing the channel domains** (Tier C) → the no-regression gate blocks a global bank; fall back to
  D2-only pooling if a domain regresses.
- **Teacher-only wins mistaken for composite wins** → Tier D flagged as teacher-moving unless it moves the
  deployable config; only the deployable path (Tier B) + no-regression (Tier C) band the composite.
- **Dysarthric false positive** (#23) → NOT-bankable until UASpeech regardless; strict cross-gender held-out
  or don't run.
- **EVAL-008 over-scoping** → a new pooling negative bounds only that pooling; the frame axis stays open.

## Test & Verification

Verdicts via the frame-pooling harness (`frame_qbe.py` build/confirm/ablate + new pooling modes), the
D2 harnesses (`t1_typical_d2_900.py`, `held_out_d2.py`, `auc_unbiased.py`), the composite scorer
(`typical_composite.py` / `SotaScorecard`), and — for Tier E — the JVM path (`Qbe.kt` + a parity test).
Every banked positive requires a fresh, pre-registered, FAR-matched confirmation on a held-out cohort
(EVAL-002/003/005), and every learned lever an EVAL-006 cross-demographic held-out.

## First-session recommendation (the discriminating subset)

Run **#1 → then {#2, #5, #11, #9+#10}** — settle the convention, then in one session hit the two co-priority
gates (cross-cohort **label** gate + deployable-student **composite** push, with ASP as the lever) and the
**no-regression gate**. That set is sufficient to decide the binary DoD: if the deployable student cannot
reach robust <5% even with ASP and the best ≤150 MB encoder, the composite is honestly **capped at 800** —
a valid banked verdict. Tier E (Kotlin) can proceed in parallel (A-bucket, no measurement dependency).
Defer Tier F until UASpeech (#28) unless run purely as wall-characterization with the NOT-banked caveat.
