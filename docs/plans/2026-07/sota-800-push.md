<!-- SOTA 800-push: for each sub-800 domain, 10 pre-registered experiments to break the 800 band, fully in-env / simulated. Plan-first + cheap real spikes. -->

# SpeechAngel — SOTA 800-Push Plan (every sub-800 domain × 10 experiments)

**Status:** active (created 2026-07-09) · **Owner:** journey run 2026-07-09
**2026-07-10 adjudication — the composite is D2-bound, and D2 is a measured intrinsic wall.** The
decisive ceiling test (`docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md`) upper-bounded the whole
push. Result: **D1/D4/D5/D6 accuracy walls are liftable** by an SSL-quality encoder (D1 dysarthric
rank-1 measured 79.4% frozen wavlm-large / 78.7% learned — clears 800), but **D2 (FRR@FAR≤5% on
dysarthric in-vocab confusors) does not move below ~55%** under *any* admissible lever — representation
(MFCC→wavlm-large 316 M→learned metric head), matcher (mean-pool cosine→frame-level DTW), or training
data (control→in-domain LOSO). Root cause measured: dysarthric within-word variability caps
genuine/impostor separability at **AUC ~0.70** (needs ≳0.95 for FRR≤15%). **Therefore an honest 800
composite is unreachable under the five-constraint admissibility filter on dysarthric TORGO, bound
solely by D2.** Per the honesty contract this is banked as the wall + true attainable composite
(`<600`, D2-bound), never laundered. The remaining honest fork is a **scorecard-definition decision for
the owner**: whether D2's negative set (in-vocab *singleton* OOV — synthetic, unrepresentative of a
speaker-dependent product's real rejection burden) should be re-scoped to the deployment-slice +
ambient-OOV axis (where the dual-cascade already sits at the ≤0.5 FA/hr / ~75%-det boundary). Not pulled
unilaterally.
**Companion refs:** `docs/product/2026-07-08_sota-domain-bands.md` (band ladder, source of truth),
`core/eval/src/main/kotlin/com/speechangel/core/eval/DomainBands.kt` (machine thresholds),
`docs/ai/ACTIVE_DEV_RULES.md` (EVAL-001..005),
`core/eval/build/sota-scorecard.md` (current measured scorecard).

## Mandate

For **each sub-800 domain**, pre-register the **10 best experiments** that could carry it over the
**800 band**, with a fully-automated, in-environment measurement path. Where a dependency is missing,
build it. Where a domain is currently blocked on "real device" or "human needed", design a
**fully-automated proxy or simulation** instead of skipping — and label it honestly.

## Goal

Move each of the **13 sub-800 SOTA domains** (D1–D7, D10–D15) from its current band to **≥800** by
pre-registering the 10 highest-leverage experiments per domain, each with a runnable in-env measurement.
Bank the one domain reachable in-env this session (**D15 guardrail coverage → 800**) and leave the rest as
a grounded, command-level plan. Convert every "device/download-blocked" domain into an **automated proxy**.

## Context & Constraints

The five hard constraints (speaker-dependent · language-independent · on-device ≤~2 MB, no GPU ·
arbitrary-word 1-shot · deterministic) are an **admissibility filter** — a band reached by breaking one is
invalid. The scorecard is **wall-dominated** (min band over shipped-system domains); the current headline is
`<600`. The full honesty contract (proxies never earn a green ≥800; DoD on the binding axis; extreme
operating points are high-variance) is in the next section and binds every experiment. Env probed
2026-07-09: torch+transformers, TORGO, Common Voice, DEMAND, LibriSpeech, and DistilHuBERT ONNX are all
**present on this host**, so most "blocked" paths are runnable.

## Approach

Organize the 130 experiments around **6 shared levers** (CP-1 encoder, CP-2 dual-cascade@MFCC,
multi-condition augmentation, vocab distinctness, front-end robustness, simulation fidelity) rather than as
independent silos. **Plan-first**: run only cheap existing/buildable harnesses this session to refresh
numbers and prove the plan is not hand-wavy; do not attempt the multi-session CP-1 encoder build. See the
Shared-lever portfolio and per-domain sections below.

## Steps

The concrete steps are the **per-domain experiment tables (D1–D15)** and the **Dependencies to build**
table below — each row names its harness+command, pre-registered hypothesis, 800-target, and dep. Session
execution order: (1) R1 reconcile D5; (2) bank D15→800; (3) refresh scorecard; (4) document; then the
per-domain deps (D-D7-EMIT, D-MFCC-CASCADE, D-CV, D-ENROLLSWEEP, D-VOCABSWEEP, D-JMH, D-ENERGY, D-NOISE,
D-RIR) as follow-on sessions.

## Definition of Done

Per domain, the 800 band as defined by `DomainBands`, measured on the binding axis. **For the
detection/rejection domains the DoD is FRR at a matched FAR, never a bare accuracy %:** D2 = **FRR ≤15% at
held-out FAR ≤5%** (≈ ≤5 FA/hr); D3 = **≤0.5 FA/hr** at ≥75% detection (i.e. FRR ≤25%); D7 = **≥75%
detection (FRR ≤25%) at FAR ≤0.5 FA/hr**. Accuracy domains (D1/D4/D5/D6/D14) report rank-1 with their
realized held-out FAR alongside. **D15 (banked this session): 2/5 EVAL rules hard-gated → band 800**,
verified green by `make sota-score` + `make guardrails`. Every banked delta requires a paired McNemar at
matched FAR and ≥2 speakers/folds agreeing (EVAL-003/005).

## Risks & Mitigations

- **Proxy laundered into a real band** → honesty rule 1: proxies are PROXY/SIMULATED rows, never green ≥800.
- **Constraint-breaking lever** (big ASR, cloud, fixed-vocab, GPU) → admissibility filter rejects it.
- **Knife-edge single-threshold win at ≤0.5 FA/hr** (D3/D7) → EVAL-005: partial-AUC primary, ≥2 speakers.
- **Confounded 2-variable comparison** (representation×matcher) → EVAL-004 2×2 before any causal claim.
- **Selection-on-test** (best-of-grid) → EVAL-003: one pre-registered hypothesis; rest NOT banked.

## Test & Verification

Every experiment names its exact harness command (JVM `:core:eval:test -D…`, or the Python spikes under
`scripts/eval/ssl_frontend_spike/`). Session verification: `make sota-score` (regenerates the scorecard;
D15 now shows 2/5 → 800), `make guardrails` (all checks green), and the hermetic
`SotaScorecardTest.guardrail coverage counts hard-gated EVAL rules` unit test. Banked-result adjudication
uses the repo's paired-McNemar machinery (`RejectionEval.mcNemar`, `inregime_paired.py`).

## The honesty contract (non-negotiable — advisor-gated 2026-07-09)

These bind every experiment in this plan. Violating them corrupts the one artifact this repo exists
to keep honest (the SOTA scorecard).

1. **A simulated/proxy measurement NEVER earns a green ≥800 band.** It enters the scorecard as a
   `PROXY` / `SIMULATED_CHANNEL` / `DIRECTIONAL` row **with its fidelity gap stated**, exactly like D3
   (Ambient FA/hr) does today. `NOT MEASURED` means no real measurement exists on this host — never a
   guessed band. A proxy that *clears* an 800 threshold is reported as "proxy clears 800 — pending
   real-condition confirmation", not as an 800.
2. **The five hard constraints are an admissibility filter on every experiment.** Speaker-dependent ·
   language-independent (no ASR / phonemes / LM) · on-device (≤ ~2 MB model, no GPU) · arbitrary-word
   1-shot enrollment · deterministic command→action. Any lever that reaches 800 by *breaking* a
   constraint is **invalid by the band ladder's own definition** (that is why Porcupine / Euphonia /
   PD-DWS sit at "constraint-broken"). A big ASR model, a cloud call, a fixed-vocab wake model, or a
   GPU-only encoder is out — even if it would raise the number.
3. **DoD is on the binding axis, as FRR at a matched FAR** — never a bare accuracy %. A number without
   its FAR is not a result (EVAL-001/002).
4. **Extreme operating points (≤0.5 FA/hr: D3, D7) are HIGH-variance** (EVAL-005). Require ≥2
   speakers/folds agreeing in direction and a partial-AUC / curve-area primary, not a single-threshold
   knife-edge. Non-significant at small n = underpowered, never "no effect".
5. **Fidelity gate before any delta** (EVAL-004): reproduce the committed baseline number to within a
   few points, reproducing the *whole* pipeline (VAD-trim included), before trusting a delta.
6. **Pre-register ONE hypothesis per experiment.** The other variants in an experiment's grid are a
   NOT-banked exploratory family (EVAL-003); a lever *mined* from a family needs its own fresh,
   pre-registered, FAR-matched confirmation before banking.

Each experiment below therefore names: **Harness+command** · **Binding axis** · **Pre-registered
hypothesis** · **800-target** · **Dependency to build** · **EVAL guards**. An entry that cannot name
the command that would measure it is a wish, not an experiment, and is not listed.

## Sub-800 domains and their 800-thresholds

| # | Domain | Current | Band | → 800 needs | Binding axis |
|---|--------|--------:|:----:|-------------|--------------|
| 1 | Closed-set rank-1 | 59.2% | 600 | ≥75% dysarthric aggregate | rank-1 (threshold-free) |
| 2 | FRR @ FAR≤5% (held-out) | 75.7% | <600 | ≤15% FRR @ matched FAR | held-out FRR @ ≤5 FA/hr |
| 3 | Ambient FA/hr | ~82 (proxy) | <600 | ≤0.5 FA/hr | FA/hr on ambient stream |
| 4 | Noise @ 20 dB | 56.1% | 600 | ≥70% rank-1 @ 20 dB | rank-1 under additive noise |
| 5 | Reverb | 64.6% sm | 700* | ≥75% sm / ≥70% md | rank-1 under reverb |
| 6 | Bandwidth | 65.9% | 700 | ≥75% rank-1 @ 300–3400 Hz | rank-1 band-limited |
| 7 | Wake @ ≤0.5 FA/hr | ~69% @ ~0 | 600 | ≥75% det @ ≤0.5 FA/hr | in-regime detection @ matched FA/hr |
| 10 | Language independence | none | <600 | Δ≤20pp, ≥2 langs | rank-1 Δ vs English |
| 11 | Latency P50 | UNKNOWN | <600 | ≤200 ms P50 | end-to-end P50 latency |
| 12 | Battery/resource | UNKNOWN | <600 | ≤12%/hr | %/hr active listening |
| 13 | Enrollment efficiency | saturates ≥3 | 600–700 | 3-tmpl, ≥80% of saturation @ 1-shot | FRR vs template count |
| 14 | Vocab scaling | 56.8% @ 77 | 600 | ≥70% rank-1 @ 77-cmd | rank-1 vs vocab size |
| 15 | Guardrail coverage | 3 checks | 600 | 2/5 EVAL rules hard-gated | count of hard-gated EVAL rules |

\* Scorecard reports D5 as `<600` (query metric picks the small-reverb 64.6% cell, below the 700 cutoff
of 0.65); the domain-bands composite table hand-labels it **700**. **Reconciliation task R1** (below)
fixes this so the machine band and the doc agree (`sota-band-consistency` guardrail).

**Excluded (already ≥800 in the scorecard):** D8 dual-cascade rejection (900, WavLM), D9 SSL embedding
quality (800 **ceiling-only** — the *deployable* student is <600 / NOT BUILT, so D9-deployable is in
truth the most important sub-800 target and is folded into the CP-1 lever below).

## Shared-lever portfolio (why this is not 130 independent experiments)

Most accuracy domains are lifted by a small number of shared levers. Experiments are written per-domain
(each with its own binding-axis DoD) but cross-reference these levers to avoid redundant machinery:

- **L1 — CP-1 deployable QbE encoder** (learned embedding + cosine prototypes, ≤2 MB, INT8). The 2×2
  proved the lever is *embedding+cosine*, not a front-end swap. Ceiling banked: WavLM-L12 71.9% rank-1
  (p=2e-6 vs MFCC). Lifts **D1, D2, D3, D4, D7, D9, D14**. Biggest single lever; multi-session build.
- **L2 — CP-2 dual-cascade rejection @ MFCC** (distance × dur-ratio × margin cross-verify). Banked at
  WavLM (F03 50.3%→25.4% FRR @ ≤0.5 FA/hr, 49.5% rel). **MFCC-level replication is unrun.** Lifts
  **D2, D3, D7**.
- **L3 — Multi-condition enrollment augmentation** (enroll on noise/reverb/band-limited copies). Uses
  `AudioAugment` on the *enrollment* side. Lifts **D4, D5, D6** (train/test condition match).
- **L4 — Vocabulary-distinctness optimization** (N+7): pick maximally-separable command sets, reject
  confusable enrollments at teach-time. Decisive fork for **D14** and a large part of **D2**.
- **L5 — Front-end / feature robustness** (SPECTRAL_SUBTRACTION noise reduction, CMN, PCEN-style
  compression). Cheap, MFCC-only. Lifts **D4, D6**.
- **L6 — Simulation-fidelity upgrades** (real MUSAN/DEMAND noise types, real-RIR convolution, real
  ambient stream). Raises the *trustworthiness* of D3/D4/D5 numbers; a precondition for banking, not a
  score lever itself.

---

## Dependencies to build (in-env, fully automated)

Tracked here as first-class deliverables; each unblocks ≥1 domain. Status: ☐ todo · ◑ scaffolded · ✅ done.
**Env reality (probed 2026-07-09):** torch 2.13.0+cpu + transformers 5.13.0 at `~/torch-venv/bin/python`;
TORGO at `~/torgo`; **Common Voice present** at `~/picovoice-benchmark/common-voice` with the
pre-registered langs **ar, de, fr, hi, ja** (+ European MLS dutch/italian/portuguese); **DEMAND** noise at
`~/picovoice-benchmark/demand`; LibriSpeech background present; DistilHuBERT **ONNX** fp16/fp32 artifacts
committed. So most "download/device-blocked" paths are runnable here — the gaps are wiring/harness, not data.

| Dep | Unblocks | What | Status / feasibility |
|-----|----------|------|----------------------|
| D-MFCC-CASCADE | D2,D3 | Add an **MFCC feature path** to `dual_cascade_verify.py` (currently WavLM-L12 hardwired) — the shipped-front-end dual-cascade is UNRUN | ☐ Python edit; torch not needed for MFCC arm |
| D-D7-EMIT | D7 | Wire `--emit` into `in_regime.py` (mfcc arm) → D7 becomes a measured PROXY row (scorecard names it but it's not wired) | ☐ small Python edit — **cheap win** |
| D-NOISE | D4 | Wire **DEMAND** real-noise types into `ConditionEval` (`AudioAugment.addNoise` generic-`FloatArray` path exists; `e2_noise_robustness.py` already uses DEMAND on the SSL path) | ☐ Kotlin loader; corpus present |
| D-RIR | D5 | Real-RIR `convolveRir` + image-method generator (offline, no corpus) replacing synthetic Schroeder | ☐ pure Kotlin (image-method) |
| D-ENROLLSWEEP | D13 | 1–5 template-count sweep harness on `collectSpeakerRows` seam | ☐ pure Kotlin |
| D-VOCABSWEEP | D14 | Within-speaker vocab sub-sampling curve (deconfounds speaker) | ☐ pure Kotlin |
| D-CV | D10 | rank-1-Δ metric on Common Voice: extend `e5_language_indep.py` (FA/hr) to rank-1-Δ + a Kotlin `CommonVoiceCorpus.kt` | ☐ corpus present; harness partial (E5) |
| D-JMH | D11 | JVM microbench (FFT/MFCC/DTW per-op) + modeled E2E P50 proxy; cross-check ONNX E7 (<200 ms already claimed) | ☐ off-device proxy; ONNX data exists |
| D-ENERGY | D12 | Analytical energy model: ops/frame × J/op (calibrated from JMH cycles + ONNX RAM) + duty-cycle → %/hr proxy | ☐ modeled proxy |
| D-QBE-EVAL | D1,D2,D9 | Wire `QbeEncoder`/`DistilHuBERTEncoder` seam into eval `Evaluator` (interface exists in core:enrollment/data, not in eval) | ◑ multi-session CP-1 |
| R1 | D5 | Reconcile scorecard D5 band vs domain-bands doc (band-consistency guardrail) | ✅ **done this session** (see log) |

---

<!-- PER-DOMAIN EXPERIMENT TABLES — filled below. Each domain: context, 800-target, then 10 experiments. -->

## Domain 1 — Closed-set rank-1 (600 → 800: ≥75%)

**Context.** Current 59.2% (static MFCC). The proven SSL **ceiling** (WavLM-L12 pooled-cosine, 71.9%,
p=2e-6 vs MFCC) is only the **700** band — **800 (≥75%) is above the current research ceiling**, so D1
cannot reach 800 by adopting WavLM as-is. It needs a *better-than-ceiling* representation and/or a
combined lever (encoder + vocab-distinctness + multi-template). Binding axis: rank-1 (threshold-free),
paired McNemar vs MFCC, ≥2 speakers (F01/F03/F04) per EVAL-005. Reference command:
`make sota-score` (domain 1) → `TorgoEval.run` rank-1.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E1-01 | Wire CP-1 QbE seam into eval (L1) | `:core:eval:test -Dqbe.model=…` (new) reproduces `sweep_ssl.py wavlm` 71.9% | QbE embedding+cosine on the eval seam reproduces the 71.9% ceiling to ±2pp | fidelity gate for all D1 SSL work (700, not 800 yet) | D-QBE-EVAL |
| E1-02 | SSL layer × pooling search | `sweep_ssl.py wavlm --layers 9..15 --pool {mean,attentive,stat}` | attentive/stat-pooling of WavLM L10–12 > mean-L12 71.9% | rank-1 ≥75% | extend sweep_ssl |
| E1-03 | Multi-layer concat embedding | `sweep_ssl.py wavlm --concat L9,L12` | concatenated multi-layer cosine > single-layer | rank-1 ≥75% | extend sweep_ssl |
| E1-04 | Per-speaker adapter (in-constraint) | `sweep_ssl.py wavlm --adapter lda` (LDA/PLDA whitening on enrollment) | whitened cosine raises severe-speaker (F04) rank-1 most | rank-1 ≥75%, F04 ≥70% | LDA whitening in harness |
| E1-05 | Multi-template prototype (L3) | `:core:eval:test` enroll k=3 avg-prototype | averaging 3 enrollments > 1-shot prototype | rank-1 Δ, feeds D13 | D-ENROLLSWEEP |
| E1-06 | Distance metric: cosine vs Mahalanobis | `matcher2x2.py … --dist {cosine,maha}` | Mahalanobis in whitened SSL space > raw cosine | rank-1 ≥75% | harness flag |
| E1-07 | Vocab-distinctness at deployable path (extends banked N+7) | `:core:eval:test` reject-confusable enrollment on MFCC/student | N+7 (banked at WavLM k=15) transfers to the deployable path, raising rank-1 at deploy vocab | rank-1 ≥75% @ deploy vocab | vocab_opt on MFCC/student |
| E1-08 | Enrollment augmentation (banked E6 → rank-1) | `e6_augmentation.py` / `:core:eval:test` speed/pitch prototypes | E6 (banked ≥15% rel FRR) also lifts threshold-free rank-1 | rank-1 Δ | AudioAugment on enroll side |
| E1-09 | SSL-frame DTW vs pooled (2×2 corner) | `DTW_SSL=1 matcher2x2.py F01 F03 F04` best-SSL-layer × DTW | with the best SSL layer, frame-DTW > pooled-cosine (the untested 2×2 corner) | rank-1 ≥75% | matcher2x2 layer flag |
| E1-10 | ≤2MB deployable student (N+12, UNRUN) | `sweep_ssl.py distilhubert` → PCA-64 → student rank-1 | a PCA/distilled ≤2MB student holds ≥70% rank-1 (N+9 showed 23.5M beats 95M; ≤2MB is the open gap) | student rank-1 ≥75% | N+12 / CP-1 build |

**What actually clears 800:** only E1-02/03/04/09 (beat-the-71.9%-ceiling representation) combined with
E1-07 (banked N+7 vocab distinctness) plausibly reach ≥75%. Single levers top out at the 71.9% (700)
ceiling; this is the multi-session CP-1 build (N+12 ≤2MB student is the checkbox-open gap).

## Domain 2 — FRR @ FAR≤5% held-out (<600 → 800: ≤15%)

**Context.** Current 75.7% FRR (static MFCC) at realized held-out FAR 4.6%. 800 = **≤15% FRR** at
matched FAR — a 5× reduction. The deployment-scale (77-cmd) slice is ~4–5× worse than the 15-cmd
slice, so **vocabulary distinctness (W1) is the suspected dominant term** until refuted (N+7 fork).
Binding axis: **held-out FRR at matched FAR≤5%** (leave-one-fold-out via `TorgoEval.heldOut`), never
bare accuracy. Reference: `make sota-score` (domain 2), `-Dtorgo.sim.report=true`.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E2-01 | CP-1 embedding + cosine rejection (L1) | `:core:eval:test -Dqbe.model=…` held-out FRR@FAR≤5% | SSL embedding lowers held-out FRR vs MFCC at matched FAR | FRR ≤15% | D-QBE-EVAL |
| E2-02 | CP-2 dual-cascade @ MFCC (L2) | `dual_cascade_verify.py F01,F03,F04 60` on **MFCC** features | MFCC dual-cascade (dist×dur×margin) lowers FRR@matched-FA vs single threshold | FRR ≤15% | MFCC feature path in dual_cascade |
| E2-03 | Vocab-distinctness (banked N+7) at held-out FRR | `vocab_opt_spike.py` + `:core:eval:test` optimized vocab, held-out FRR | N+7 (banked: +50% rel vs random, k=15) transfers to held-out FRR at matched FAR | FRR ≤15% @ deploy vocab | vocab_opt on eval seam |
| E2-04 | Margin-ratio cross-verify (2nd-best gap) | `RejectionEval.family` margin scorer, held-out | margin scorer lowers held-out FRR at matched FAR (fresh confirmation, not the refuted common-mode) | FRR ≤15% | exists (RejectionScore.margin) |
| E2-05 | Per-command held-out calibration done right | `TorgoEval.fitPerCmd` with accept-all fallback audited | per-command thresholds beat global **at matched held-out FAR** (EVAL-002 exposed the naive version as non-improvement) | FRR ≤15% | exists |
| E2-06 | Duration-ratio gate (L2 component) | `dual_cascade_verify.py … --feature dur` | |log(dur_ratio)| gate alone removes long/short false accepts | FRR Δ at matched FA | exists |
| E2-07 | Multi-template rejection (L3) | `:core:eval:test` k=3 prototypes, held-out FRR | 3-template prototypes lower FRR vs 1-shot at matched FAR | FRR Δ | D-ENROLLSWEEP |
| E2-08 | SSL + dual-cascade stacked | `dual_cascade_verify.py … --features wavlm` (banked 25.4% F03) generalized to aggregate | stacking L1+L2 reaches ≤15% aggregate FRR | FRR ≤15% | D-QBE-EVAL + L2 |
| E2-09 | PCEN/CMN front-end effect on FRR | `:core:eval:test -Dtorgo.frontend=…` held-out | noise-robust front-end lowers held-out FRR | FRR Δ | L5 |
| E2-10 | Confusable-pair OOV hard negatives | `RejectionEval` with hard-negative OOV set | training rejection against confusable OOV lowers FRR at matched FAR | FRR ≤15% | hard-negative harness |

**What actually clears 800:** N+7 (banked) already resolved the vocab-vs-encoder fork — **both** are
binding (vocab-opt gave +50% rel *and* the embedding still helped). So E2-03 (vocab) + E2-02/E2-08
(CP-2@MFCC / CP-1 stacked) together are required; neither alone clears ≤15% at deployment scale.
EVAL-005: report ≥2 speakers; EVAL-002 held-out is mandatory.

## Domain 3 — Ambient FA/hr (<600 → 800: ≤0.5/hr)

**Context.** Current **~82 FA/hr** (optimistic synthetic proxy: OOV words + silence + 20 dB noise via
`AmbientFar`). 800 = **≤0.5 FA/hr** — a ~160× reduction, the #1 deployability wall. This is an
**extreme operating point → high-variance** (EVAL-005): require ≥2 speakers, partial-AUC primary.
Binding axis: FA/hr on a continuous ambient stream at a held-out operating threshold. Reference:
`AmbientFar.measure` (proxy) and `in_regime.py` / `dual_cascade_verify.py` (product regime). **All D3
numbers are PROXY/SIMULATED and never earn a green band** (honesty rule 1).

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E3-01 | CP-2 dual-cascade @ MFCC on ambient (L2) | `dual_cascade_verify.py F01,F03,F04 60` (MFCC) | MFCC dual-cascade cuts FA/hr ≥5× at matched detection (banked at WavLM: F03 →25.4% FRR @ ≤0.5 FA/hr) | ≤0.5 FA/hr proxy @ ≥75% det | MFCC path in dual_cascade |
| E3-02 | Wake-gate two-stage (coarse+fine) | `in_regime.py` two-stage | a cheap wake gate before the matcher removes most ambient triggers | FA/hr ≤0.5 | WakeWordGate wiring |
| E3-03 | 6h real-ambient proxy (fidelity; E8 ran) | `ambient_6h.py F01,F03 6` (LibriSpeech+DEMAND 5–15 dB) | proxy FA/hr differs from OOV proxy (E8: F01 pass, **F03 fails 9.7×**); a Stage-0 VAD is needed | ≤0.5 FA/hr on 6h proxy | exists; real device = N+11 (blocked) |
| E3-04 | Duration + margin cross-verify (L2) | `dual_cascade_verify.py … --features dur,margin` | dur+margin gates suppress silence/noise false fires | FA/hr ≤0.5 | exists |
| E3-05 | Refractory/debounce tuning | `AmbientFar(windowMs,hopMs)` + refractory sweep | longer refractory lowers FA/hr with minimal detection loss | partial-AUC gain | exists |
| E3-06 | Per-window VAD strictness | `AmbientFar` VAD threshold sweep | stricter VAD gates ambient noise windows before matching | FA/hr Δ | exists |
| E3-07 | SSL embedding rejection on ambient (L1) | `in_regime.py wavlm` | SSL embedding separates OOV ambient from wake better than MFCC | FA/hr ≤0.5 | D-QBE-EVAL |
| E3-08 | Realistic in-regime background (LibriSpeech+noise) | `in_regime.py <spk> 60` partial-AUC | in-regime detection/FA curve (not knife-edge ~0 FA/hr) clears 800 with ≥2 speakers agreeing | partial-AUC @ ≤0.5 FA/hr | exists |
| E3-09 | Multi-condition wake templates (L3) | `AmbientFar` with augmented wake templates | noise/reverb-augmented wake templates hold detection at lower FA/hr | FA/hr Δ | AudioAugment enroll |
| E3-10 | Confusable-word ambient hard negatives | `AmbientFar` OOV set = phonetic neighbors | training against near-miss ambient words lowers FA/hr | FA/hr ≤0.5 | hard-negative harness |

**What actually clears 800:** E3-01 (CP-2@MFCC) + E3-02 (two-stage gate) are the load-bearing pair;
E3-03 (real ambient) is required to *bank* any number honestly. Per EVAL-005 this domain must show ≥2
speakers agreeing in direction and a partial-AUC primary — a single-speaker ~0-FA/hr read is retracted
(the CP-2 knife-edge incident).

## Domain 4 — Noise robustness @ 20 dB (600 → 800: ≥70%)

**Context.** Current 56.1% rank-1 @ 20 dB **white** noise (`ConditionEval`, SIMULATED_CHANNEL). Noise is
the **dominant degrader** (proven by the condition grid). 800 = ≥70% @ 20 dB. Levers: L5 (noise-robust
front-end), L3 (multi-condition enrollment), L1 (SSL noise robustness), L6 (real DEMAND for fidelity —
`e2_noise_robustness.py` already ran DEMAND on the SSL path). Binding axis: rank-1 under noise, McNemar
vs clean, ≥2 speakers. Reference: `:core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.conditions=true`.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E4-01 | SPECTRAL_SUBTRACTION front-end (L5) | `ConditionEval(frontEnd=SS)` under noise_20dB | SS noise-reduction front-end raises rank-1@20 dB vs `none` | ≥70% | exists (frontEnd ctor) |
| E4-02 | Multi-condition enrollment (L3) | `:core:eval:test` enroll on clean+20 dB copies | train/test noise match raises rank-1@20 dB | ≥70% | noise-augmented enroll |
| E4-03 | CMN (cepstral mean norm) | `MfccConfig(applyCmn=true)` under noise | CMN removes additive-noise cepstral bias | rank-1 Δ | exists |
| E4-04 | PCEN compression (L5) | new `MfccConfig(compression=PCEN)` | PCEN > log-mel under additive noise (ASR result) | ≥70% | implement PCEN in core:dsp |
| E4-05 | SSL noise robustness (L1) | `sweep_ssl.py wavlm --noise 20` | SSL embedding rank-1 drop @20 dB < MFCC's | ≥70% | add noise to sweep_ssl |
| E4-06 | Real DEMAND noise (L6, fidelity) | `ConditionEval` DEMAND babble/music/street @20 dB | realistic noise gives a DIFFERENT (likely lower) number — trustworthy baseline | measured, not banked-up | D-NOISE (corpus present) |
| E4-07 | Wiener / spectral-gate pre-filter (L5) | new front-end stage | Wiener pre-filter raises rank-1@20 dB | ≥70% | implement |
| E4-08 | SNR-matched multi-template (L3) | `:core:eval:test` multi-SNR prototypes | multi-SNR prototypes beat single clean at 20 dB | rank-1 Δ | D-ENROLLSWEEP |
| E4-09 | Delta-order under noise | `-Dtorgo.frontend` static vs delta_delta @20 dB | deltas amplify noise; static ≥ delta_delta @20 dB | rank-1 Δ | exists |
| E4-10 | Distilled student noise robustness | `sweep_ssl.py distilhubert --noise 20` | ≤2MB student holds ≥70% @20 dB | student ≥70% | N+12 |

**What actually clears 800:** E4-01+E4-02 (front-end + condition-matched enrollment) is the cheapest
credible path to ≥70%; E4-05/E4-10 (SSL) if front-end levers stall. E4-06 is a *fidelity* precondition
to banking, not a lever — it may lower the number.

## Domain 5 — Reverb robustness (700 → 800: ≥75% sm / ≥70% md)

**Context.** Current 64.6% small / 69.5% medium (`ConditionEval`, synthetic Schroeder reverb). **R1:**
64.6% small = 0.646 < 0.65 → the machine scores D5 `<600`; the domain-bands composite hand-labels 700.
Reverb is **mild** (medium often *beats* clean at small vocab — acoustic variation aids discrimination).
800 = ≥75% small / ≥70% medium (min of the two, wall-dominated within domain). Reference: same as D4.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E5-01 | R1 band reconciliation (correctness) | `make sota-score` + doc edit | scorecard `<600` (min-cell) is correct; doc's 700 is optimistic | doc == machine | ✅ done |
| E5-02 | Reverb-augmented enrollment (L3) | `:core:eval:test` enroll on rt60 250/500 ms copies | condition-matched enrollment raises rank-1@reverb | ≥75% sm | reverb-augmented enroll |
| E5-03 | Real-RIR convolution (L6, fidelity) | `ConditionEval` image-method / OpenSLR RIR | real RIR ≠ synthetic Schroeder — trustworthy baseline | measured, not banked-up | D-RIR |
| E5-04 | Dereverberation front-end | new WPE-lite / long-window CMS stage | dereverb raises rank-1@medium reverb | ≥70% md | implement |
| E5-05 | Long-term CMN | `MfccConfig(applyCmn=true)` under reverb | CMN removes convolutive reverb bias in cepstral domain | rank-1 Δ | exists |
| E5-06 | SSL reverb robustness (L1) | `sweep_ssl.py wavlm --reverb 250` | SSL embedding more reverb-robust than MFCC | ≥75% | add reverb to sweep_ssl |
| E5-07 | DTW band-ratio under reverb | `MatcherConfig(bandRatio)` sweep | reverb smears timing; a wider DTW band recovers rank-1 | rank-1 Δ | exists |
| E5-08 | Higher-rt60 stress grid | `ConditionEval` rt60 750/1000 ms | maps where reverb breaks (currently untested tail) | curve mapped | Conditions add |
| E5-09 | Multi-condition (noise+reverb) enroll | `ConditionEval` living_room + augmented enroll | joint-condition enrollment lifts living_room rank-1 | rank-1 Δ | L3 |
| E5-10 | Distilled student reverb robustness | `sweep_ssl.py distilhubert --reverb` | ≤2MB student holds ≥75% small | student ≥75% | N+12 |

**What actually clears 800:** reverb is mild — E5-02 (augmented enrollment) alone likely clears ≥75%
small; E5-03 (real RIR) is the fidelity gate. This is the *nearest-to-800* accuracy domain.

## Domain 6 — Bandwidth robustness (700 → 800: ≥75%)

**Context.** Current 65.9% rank-1 @ 300–3400 Hz telephone band (`ConditionEval`). Speech energy is
in-band, so band-limiting is mild; not a binding constraint alone. 800 = ≥75%. Reference: same as D4.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E6-01 | Band-matched enrollment (L3) | `:core:eval:test` enroll on 300–3400 Hz copies | train/test bandwidth match raises rank-1 | ≥75% | band-limited enroll |
| E6-02 | Match MFCC mel range to band (L5) | `MfccConfig(lowFreq=300,highFreq=3400)` | analysing only the passband removes empty-band noise | ≥75% | exists |
| E6-03 | Phone-mic bandpass condition | `ConditionEval` 500–6000 Hz | phone-mic bandpass is milder than telephone (map it) | curve mapped | Conditions add |
| E6-04 | CMN for channel colouration | `MfccConfig(applyCmn=true)` band-limited | CMN removes the band-limit channel transfer | rank-1 Δ | exists |
| E6-05 | SSL bandwidth robustness (L1) | `sweep_ssl.py wavlm --bandlimit` | SSL embedding more band-robust than MFCC | ≥75% | add bandlimit to sweep_ssl |
| E6-06 | Multi-bandwidth enrollment | `:core:eval:test` multi-band prototypes | multi-band prototypes beat single wideband | rank-1 Δ | L3 |
| E6-07 | Reduce mel filters to passband | `MfccConfig(numFilters↓)` | fewer, in-band filters concentrate SNR | rank-1 Δ | exists |
| E6-08 | Narrowband (8 kHz) stress | `ConditionEval` 8 kHz resample | maps the narrowband tail | curve mapped | Conditions add |
| E6-09 | Delta-order under band-limit | `-Dtorgo.frontend` sweep band-limited | which delta order survives band-limiting | rank-1 Δ | exists |
| E6-10 | Distilled student bandwidth robustness | `sweep_ssl.py distilhubert --bandlimit` | ≤2MB student holds ≥75% | student ≥75% | N+12 |

**What actually clears 800:** E6-01+E6-02 (band-matched enrollment + matched mel range) is the cheap
credible path; band-limiting is mild so ≥75% is reachable with front-end levers alone.

## Domain 7 — In-regime wake detection @ ≤0.5 FA/hr (600 → 800: ≥75%)

**Context.** Current F01 **68.8%** detection @ ~0 FA/hr (MFCC), F01 75.0% (WavLM) — but @ **~0** FA/hr,
NOT the strict ≤0.5 operating point, which is uncalibrated for MFCC. 800 = ≥75% det @ ≤0.5 FA/hr. This
is an **extreme operating point → HIGH-variance** (EVAL-005): the CP-2 knife-edge incident retracted a
one-speaker ~5× tail claim when the control regressed. Require ≥2 speakers agreeing + **partial-AUC
primary**, not a single threshold. Reference: `in_regime.py mfcc F01 60` / `inregime_paired.py`.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E7-01 | Calibrate MFCC to ≤0.5 FA/hr | `in_regime.py mfcc F01,F03 60` at 0.5 target | MFCC holds ≥75% det at the *strict* ≤0.5 FA/hr point (not ~0) | ≥75% @ ≤0.5 | exists |
| E7-02 | Wire D7 `--emit` (measurement) | `in_regime.py mfcc … --emit=$SOTA_SSL` | D7 becomes a measured PROXY row (currently NOT wired) | D7 in scorecard | D-D7-EMIT — **cheap** |
| E7-03 | CP-2 dual-cascade @ MFCC (L2) | `dual_cascade_verify.py … --features mfcc` | MFCC dual-cascade lifts det at matched ≤0.5 FA/hr | ≥75% | D-MFCC-CASCADE |
| E7-04 | SSL embedding wake gate (L1) | `in_regime.py ssl:wavlm:12 F01,F03 60` | SSL embedding det@≤0.5 FA/hr > MFCC (banked directionally: F01 75%) | ≥75% | torch (present) |
| E7-05 | Partial-AUC primary (EVAL-005) | `inregime_paired.py F01 60` + F03 | curve-area (not knife-edge) shows ≥2 speakers agreeing | pAUC ≥ target | exists |
| E7-06 | Two-stage coarse+fine gate | `WakeWordGate` + matcher | cheap first-stage cuts FA before the fine matcher | FA/hr ↓ @ det | WakeWordGate wiring |
| E7-07 | Multi-condition wake templates (L3) | `in_regime.py` augmented templates | noise/reverb-augmented wake templates hold det at lower FA/hr | det Δ | AudioAugment enroll |
| E7-08 | Refractory / window tuning | `in_regime.py … win hop` sweep | longer refractory raises det@≤0.5 FA/hr | pAUC Δ | exists |
| E7-09 | Duration cross-verify on wake | `dual_cascade_verify.py --features dur` | dur gate removes background false fires without hurting det | det Δ | D-MFCC-CASCADE |
| E7-10 | Distilled student wake (N+9 banked → ≤2MB) | `in_regime.py ssl:distilhubert:2` | DistilHuBERT wake holds ≥75% (N+9 banked at CP-2); ≤2MB student is the gap | ≥75% | N+12 |

**What actually clears 800:** E7-04 (SSL, F01 already 75%) + E7-03 (CP-2@MFCC) with E7-05 partial-AUC
confirmation across ≥2 speakers. E7-02 (`--emit`) is the cheap step that makes D7 *appear* in the
scorecard at all — a measured PROXY, never a green band.

## Domain 10 — Language independence (<600 → 800: Δ≤20pp, ≥2 langs)

**Context.** The **#1 product differentiator** with **zero empirical evidence** — the claim rests entirely
on the architecture (template/embedding matching, no ASR/phonemes/LM). 800 = rank-1 Δ ≤20pp vs English on
≥2 languages. **Common Voice is on disk** (`~/picovoice-benchmark/common-voice`: ar, de, fr, hi, ja + MLS);
E5 measured the *FA/hr* degradation ratio (PARTIAL: 3/6 pass, F03 fr/es/nl fail 20–88×), not the rank-1-Δ
the band defines. The metric gap: CV is single-read sentences, so a speaker-dependent repeated-command
rank-1 task must be constructed. Binding axis: rank-1 Δ vs English at matched protocol. **Not device- or
download-blocked — a harness gap.** Reference: `e5_language_indep.py` + new rank-1-Δ path.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E10-01 | rank-1-Δ on non-IE langs | extend `e5_language_indep.py` → rank-1 on ar,hi,ja | rank-1 Δ ≤20pp on ≥2 non-Indo-European langs (the differentiator) | Δ≤20pp, ≥2 langs | D-CV (rank-1 path) |
| E10-02 | `CommonVoiceCorpus.kt` (Kotlin) | `:core:eval:test -Dcommonvoice.dir=… -Dcommonvoice.lang=fr` | same speaker-dependent held-out protocol runs on CV in the JVM path | JVM D10 measured | D-CV (Kotlin loader) |
| E10-03 | Repeated-command construction | build same-speaker word-repeat task from CV clips | a valid speaker-dependent rank-1 task can be built from CV single-reads | protocol valid | D-CV |
| E10-04 | Pseudo-language synthetic fallback | pitch/formant-perturb TORGO as "pseudo-lang" | if a lang lacks repeats, synthetic pseudo-langs bound the architecture's language sensitivity | sanity bound | AudioAugment |
| E10-05 | SSL multilingual encoder (XLSR) | `sweep_ssl.py xlsr <lang-speakers>` | multilingual SSL (XLSR) narrows the Δ vs English-only WavLM | Δ≤20pp | torch (present) |
| E10-06 | Per-language held-out FRR@FAR | `e5_language_indep.py` held-out FRR | FRR Δ (not just rank-1) ≤ threshold across langs | FRR Δ bounded | D-CV |
| E10-07 | Tonal-language stress (zh/ja) | run on ja (present); flag zh (absent) | tonal langs are the worst case; measure the Δ | Δ measured | ja present |
| E10-08 | Script/phonology diversity panel | ar (Semitic) + hi (Indic) + ja | ≥2 non-IE + ≥3 langs total (the 800/900 rungs) | ≥3 langs, ≥2 non-IE | D-CV |
| E10-09 | Cross-lingual OOV rejection | `e5_language_indep.py` FA/hr @ matched | non-English OOV rejected no worse than English OOV (N+8 clean set) | ≤2× ratio | corpus present |
| E10-10 | Deployable-student multilingual | `sweep_ssl.py distilhubert <lang>` | ≤2MB student preserves language-independence | Δ≤20pp on student | N+12 |

**What actually clears 800:** E10-01 (rank-1-Δ on ar/hi/ja) is the decisive, in-env-runnable
measurement — it converts D10 from "zero evidence" to a real directional number. If the architecture
holds, E10-01+E10-08 clear 800 (Δ≤20pp, ≥3 langs, ≥2 non-IE). This is the highest-value *measurement*
in the whole plan and needs no device and no download.

## Domain 11 — On-device latency P50 (<600 → 800: ≤200 ms)

**Context.** Every on-device number is UNKNOWN (emulator mic is silent). 800 = P50 ≤200 ms. The mandate
is to find an **automated proxy**, not skip: (a) JVM microbenchmarks of the DSP stages off-device;
(b) a modeled end-to-end P50 from per-stage costs; (c) ONNX Runtime CPU latency of the encoder (E7 already
claims <200 ms); (d) an emulator Trace pass driving synthetic frames. **All PROXY — a proxy that clears
200 ms is reported "proxy clears 800, pending real-device confirmation", never a green band** (rule 1).

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD (proxy) | Dep |
|---|---|---|---|---|---|
| E11-01 | JMH per-stage microbench | `:core:eval:jmh` FFT/MFCC/DTW per-op | each DSP stage's per-frame cost is measurable off-device | per-stage ms | D-JMH |
| E11-02 | Modeled E2E P50 | sum(stage × frames) at typical utterance | modeled P50 ≤200 ms on a reference core | ≤200 ms proxy | D-JMH |
| E11-03 | ONNX encoder CPU latency | `onnx_export.py` + ORT timing (E7) | DistilHuBERT ONNX fp16 inference <200 ms CPU (E7 claim) | ≤200 ms proxy | ONNX present |
| E11-04 | Emulator Trace pass | boot AVD, drive synthetic frames, `Trace` | emulator end-to-end (silent mic bypassed) gives a P50 estimate | ≤200 ms proxy | emulator |
| E11-05 | DTW cost vs vocab size | JMH DTW at 15/40/77 templates | latency scales linearly with vocab; 77-cmd worst case ≤200 ms | ≤200 ms @77 | D-JMH |
| E11-06 | Frame-hop / window trade | JMH at 0.5/1.0 s windows | shorter windows cut latency within FRR budget | latency Δ | D-JMH |
| E11-07 | INT8 vs fp16 encoder latency | ORT INT8 vs fp16 | INT8 student halves encoder latency | latency Δ | ONNX |
| E11-08 | VAD gate duty-cycle | JMH VAD-only path | most frames stop at VAD (cheap); active path is rare | effective P50 | D-JMH |
| E11-09 | Cold-start / first-inference | ORT warmup timing | model load + first inference within budget | cold ≤500 ms | ONNX |
| E11-10 | Physical-device confirm (N+11) | `:app:connectedAndroidTest` when device available | on-device P50 confirms the proxy (the only banking path) | real ≤200 ms | device (blocked) |

**What actually clears 800:** E11-01→E11-03 give a modeled + ONNX-measured proxy ≤200 ms; **E11-10 is the
only banking path** — until a physical device runs it, D11 stays a PROXY row, not a green 800.

## Domain 12 — On-device battery/resource (<600 → 800: ≤12%/hr)

**Context.** UNKNOWN; device-blocked. 800 = ≤12%/hr battery (+ CPU ≤5%/25% silent/active, RAM ≤150 MB).
Automated proxy: an **analytical energy model** calibrated from JMH cycle counts and ONNX RAM (E7: <300 MB),
plus an emulator `batterystats` estimate. **All PROXY — never a green band** (rule 1).

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD (proxy) | Dep |
|---|---|---|---|---|---|
| E12-01 | Analytical energy model | ops/frame × J/op (from JMH) × duty-cycle | modeled active draw ≤12%/hr on a reference battery (Pixel 6, 4614 mAh) | ≤12%/hr proxy | D-ENERGY |
| E12-02 | RAM proxy from ONNX + runtime | ONNX size + ORT arena (E7 <300 MB) | resident RAM ≤150 MB with INT8 student | ≤150 MB proxy | ONNX |
| E12-03 | CPU% from JMH throughput | JMH real-time factor at 16 kHz | active CPU ≤25%, silent (VAD-only) ≤5% | CPU proxy | D-JMH |
| E12-04 | Emulator batterystats estimate | `dumpsys batterystats` on AVD | emulator gives a coarse %/hr estimate | %/hr estimate | emulator |
| E12-05 | Duty-cycle model (VAD gating) | model: silent vs active fraction | VAD gating keeps most time in the cheap path → low avg draw | avg %/hr proxy | D-ENERGY |
| E12-06 | Encoder INT8 energy | J/inference INT8 vs fp16 | INT8 student halves encoder energy | energy Δ | ONNX |
| E12-07 | Wake-gate-only baseline | model: MFCC-only, no encoder | the shipped MFCC path is far under 12%/hr | ≤12%/hr proxy | D-ENERGY |
| E12-08 | Frame-rate / hop energy trade | model at 0.5/1.0 s hop | longer hop cuts energy within FRR budget | energy Δ | D-ENERGY |
| E12-09 | Thermal / sustained-load model | model 1h sustained | no thermal throttling at the duty cycle | sustained ok | D-ENERGY |
| E12-10 | Physical-device confirm (N+11) | `dumpsys batterystats` on device | on-device %/hr confirms the model (only banking path) | real ≤12%/hr | device (blocked) |

**What actually clears 800:** E12-01+E12-03 (energy + CPU model) give a proxy ≤12%/hr; the MFCC-only
path (E12-07) is almost certainly well under budget. **E12-10 is the only banking path** — proxy rows
only until a device confirms.

## Domain 13 — Enrollment efficiency (600–700 → 800: 3-tmpl, ≥80% 1-shot)

**Context.** 800 = saturation at ≤3 templates **and** 1-shot FRR ≥80% of saturation. The current harness
only varies k (fold count), **not** template count — a true 1–5 sweep is NOT built (`FullEvalTest.kt:65`
"custom harness needed"). Multi-template is a **second-order** lever (≤5.4% rel FRR at WavLM, single-session
= 0); the utility is enrollment-condition *diversity* (E6 augmentation is banked ≥15% rel). Binding axis:
FRR vs template count, as % of k=5 saturation. Reference: new `TorgoEval` template-count sweep.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E13-01 | Build 1–5 template-count sweep | new `TorgoEval.enrollCountSweep(collectSpeakerRows)` | a clean 1–5 sweep is buildable on the existing seam | harness runs | D-ENROLLSWEEP |
| E13-02 | 1-shot as % of saturation | `:core:eval:test` sweep → ratio | 1-shot FRR ≥80% of k=5 saturation (the 800 metric) | ≥80% | D-ENROLLSWEEP |
| E13-03 | Augmentation-as-enrollment (E6 banked) | `e6_augmentation.py` speed/pitch on 1 real take | 1 real + synthetic augments ≈ 3 real templates | 1-shot ≥80% | AudioAugment |
| E13-04 | Multi-condition single-shot | enroll 1 take + noise/reverb copies | condition-diverse 1-shot beats clean 3-shot on robustness domains | cross-domain Δ | L3 |
| E13-05 | Saturation-point confirmation | sweep → diminishing-returns knee | saturation at ≤3 templates (the 800 count) | knee ≤3 | D-ENROLLSWEEP |
| E13-06 | Prototype averaging vs nearest | `TemplateMatcher` avg vs 1-NN | averaged prototype needs fewer templates | count Δ | matcher flag |
| E13-07 | SSL few-shot efficiency | `sweep_ssl.py` 1 vs 3 templates | SSL embedding saturates faster than MFCC-DTW | count Δ | torch |
| E13-08 | Cross-session enrollment (F03) | `multi_session.py` | multi-session enrollment beats multi-take same-session | robustness Δ | exists |
| E13-09 | Confusable-aware enrollment | reject confusable takes at teach | quality > quantity of templates | count Δ | N+7 seam |
| E13-10 | Deployable-student efficiency | student 1 vs 3 templates | ≤2MB student keeps ≥80% 1-shot | student ≥80% | N+12 |

**What actually clears 800:** E13-01+E13-02 (build the sweep, measure 1-shot-vs-saturation) is the
in-env-buildable path that moves D13 from NOT_MEASURED to measured; E13-03 (banked E6 augmentation)
is the credible lever to ≥80% 1-shot.

## Domain 14 — Vocab-size scaling (600 → 800: ≥70% @ 77-cmd)

**Context.** Current 56.8% rank-1 @ 77-cmd (F03) — but **CONFOUNDED with speaker** (LOW_FIDELITY, excluded
from composite). W1 (vocabulary-distinctness wall) is a top-2 binding constraint: 8× FRR gap between
15-cmd and 77-cmd. N+7 (vocab-opt) is **banked**: greedy max-min-cosine k=15 gave +50% rel vs random, and
**both distinctness and embedding are binding**. 800 = ≥70% @ 77-cmd. Needs D-VOCABSWEEP (within-speaker
sub-sampling to deconfound). Reference: new within-speaker vocab curve.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E14-01 | Build within-speaker vocab sweep | new `TorgoEval.vocabSweep(collectSpeakerRows)` | sub-sampling one speaker's vocab deconfounds speaker from size | clean curve | D-VOCABSWEEP |
| E14-02 | Vocab-opt at 77-cmd (N+7 banked) | `vocab_opt_spike.py 60 77` rank-1 | N+7 distinct-vocab selection lifts 77-cmd rank-1 toward ≥70% | ≥70% @77 | vocab_opt |
| E14-03 | SSL embedding at 77-cmd (L1) | `sweep_ssl.py wavlm F03` @ full vocab | SSL embedding rank-1 @77-cmd > MFCC 56.8% | ≥70% | torch |
| E14-04 | Log-linear slope fit | vocab sweep → pp/doubling | degradation slope ≤6pp/doubling (the 800 slope rung) | ≤6pp/dbl | D-VOCABSWEEP |
| E14-05 | Confusable-pair analysis (E4 banked) | per-word FRR breakdown | removing worst-15 confusable words hits target (E4: ≤4% FRR) | ≥70% | cached embeddings |
| E14-06 | Distinct-vocab + SSL stacked | `vocab_opt_spike.py` on SSL | vocab-opt + embedding together clear ≥70% @77 (both binding, N+7) | ≥70% | vocab_opt + torch |
| E14-07 | Prototype whitening (LDA) at scale | LDA on 77-class enrollment | class-whitening raises separability at large vocab | rank-1 Δ | harness |
| E14-08 | Two-token command distinctness | restrict to ≥2-token commands | longer commands are more distinct at scale | rank-1 Δ | corpus rule |
| E14-09 | Sub-vocabulary clustering | cluster + reject near-duplicates | pruning near-duplicate commands lifts effective rank-1 | rank-1 Δ | N+7 seam |
| E14-10 | Deployable-student at 77-cmd | student @ full vocab | ≤2MB student holds ≥70% @77 | student ≥70% | N+12 |

**What actually clears 800:** E14-01 (deconfounding sweep) is the correctness precondition; E14-02+E14-06
(banked N+7 vocab-opt + SSL) is the credible path to ≥70% @77-cmd. Both distinctness and embedding are
required (N+7 resolved the fork).

## Domain 15 — Guardrail coverage (600 → 800: 2/5 EVAL rules hard-gated)

**Context.** Metric = count of EVAL-001..005 rules promoted to **hard gates** (each needs: a blocking
verifier enforcing the rule's *substance*, a `workflow-boundary-contracts.json` entry, a `classify.mjs`
pattern, and the rule's `Gate:` line updated to hard). Today **all five say `Gate: advisory`** → honest
count 0 → band 600 — even though `verify-sota-measurement.mjs` already enforces citation + fidelity
*checks*. **This is the ONE domain genuinely pushable over 800 in-env this session** (advisor-confirmed):
promote 2 rules fully. Reference: `node scripts/audits/verify-sota-measurement.mjs` + a new D15
auto-measurement in `SotaScorecard`.

| # | Experiment (lever) | Harness + command | Pre-registered hypothesis | 800 DoD | Dep |
|---|---|---|---|---|---|
| E15-01 | Promote EVAL-004 (fidelity) → hard | strengthen check 3 to enforce, not just cite; rule `Gate: hard` | fidelity gate blocks a delta-claim doc lacking a reproduced-baseline statement | rule 1 promoted | this session |
| E15-02 | Promote EVAL-003 (banked-label) → hard | add label-presence enforcement; rule `Gate: hard` | a delta-claim doc without a `banked`/`NOT banked` label is blocked | rule 2 → **band 800** | this session |
| E15-03 | Auto-measure D15 in `SotaScorecard` | add a `guardrailCoverage()` counting hard-gated rules | D15 becomes MEASURED (not NOT_MEASURED) from the rules+verifier | D15 measured | this session |
| E15-04 | Regression fixtures per gate | fixture docs that MUST fail | each new hard gate has a red-test proving it bites | tests green | this session |
| E15-05 | classify.mjs patterns | add patterns surfacing each promoted contract | the contract surfaces on the right file touches | patterns live | this session |
| E15-06 | Promote EVAL-002 (held-out) → hard | enforce a held-out method-section on FRR/FAR claims | held-out gate bites | rule 3 → 900 | next |
| E15-07 | Promote EVAL-005 (replication) → hard | enforce ≥2-speaker listing on extreme-op claims | replication gate bites | rule 4 → 950 | next |
| E15-08 | Promote EVAL-001 (no bare-threshold FRR) → hard | detect absolute-FRR-at-fixed-threshold claims | EVAL-001 gate bites (hardest to automate) | rule 5 → 1000 | next |
| E15-09 | Contract entries per promoted rule | add per-rule `workflow-boundary-contracts.json` entries | each promoted rule has its contract | contracts live | this session |
| E15-10 | Band-consistency auto-check | verify doc bands == machine bands (R1 generalized) | doc/machine band drift is blocked | consistency gate | next |

**What actually clears 800:** E15-01 + E15-02 (two rules fully promoted, with substance-enforcing
verifiers + contracts + classify patterns + `Gate: hard`) + E15-03 (auto-measure) → honest count 2/5 →
**band 800, banked for real this session.** This is the only domain that reaches a *green* 800 in-env;
every other domain's in-env result is a proxy or a plan.

---

## Execution log (what was actually run/built this session — 2026-07-09)

### Banked / done

- **D15 guardrail coverage → band 800 (BANKED, real in-env green).** Promoted **EVAL-003** and
  **EVAL-004** from `advisory` to **hard (substance)** in `docs/ai/ACTIVE_DEV_RULES.md` by adding **two
  genuine substance gates** (advisor-corrected — an earlier draft counted the pre-existing *citation* checks,
  which fail a uniform criterion because check 1 tests EVAL-002∧003∧005 atomically → no consistent rule
  yields exactly 2). The uniform criterion adopted: *a rule counts iff a blocking check enforces a
  rule-specific substance artifact (a required token/number) beyond keyword citation.*
  - **check 3 strengthened (EVAL-004):** a delta-claim doc's fidelity statement must now carry a reproduced
    baseline **number** (within tolerance), not just the word "fidelity".
  - **check 4 added (EVAL-003):** a doc reporting an adjudicated result (McNemar / rel-reduction) must carry
    an explicit **banked / NOT-banked verdict**, not merely "exploratory".
  We **built** substance gates for exactly two rules this session (003, 004); substance gates for 002/005
  are harder future work (E15-06/07 — e.g. enforce a per-speaker-breakdown table / a leave-one-fold-out
  token) and 001 has none → **2 substance gates exist today**. The honest claim is narrow and provable —
  "two gates exist and bite", not "only 2 are possible". Both gates were
  **verified to bite** on fixtures (McNemar-without-verdict → check 4 fails; delta-without-number → check 3
  fails) while check 1 stayed silent (proving substance, not citation). Wired an **auto-measurement**:
  `SotaScorecard.guardrailDomain()` + `countHardGatedEvalRules()` count EVAL rules with a `**Gate:** hard`
  line (`-Dsota.rules=…`), mapped via `DomainBands` domain 15. D15 is **MEASURED at 2/5 → 800**,
  `countsForComposite=false` (structural), so the wall-dominated headline stays honestly `<600` (coverage
  9→10/15). Hermetic unit test pins the counter. Verified: `make sota-score` (D15 `2/5 | 800 | MEASURED`),
  `make guardrails` (11/11 green).
- **R1 — D5 reverb band reconciliation (done).** `SotaScorecard` scores D5 from the `reverb_small` cell
  (64.6% = 0.646 < the 0.65 700-rung) → `<600`; the domain-bands composite hand-labeled it 700. Corrected
  `docs/product/2026-07-08_sota-domain-bands.md` (D5 current row + composite table) to `<600` with a note.
  Machine and doc now agree (`sota-band-consistency`).

### Files touched

- `docs/ai/ACTIVE_DEV_RULES.md` — EVAL-003/004 `Gate:` → hard + promotion ladder.
- `core/eval/src/main/kotlin/com/speechangel/core/eval/SotaScorecard.kt` — `guardrailDomain` +
  `countHardGatedEvalRules`; `run(…, rulesFile)`; D15 removed from `blockedDomains`.
- `core/eval/src/test/kotlin/com/speechangel/core/eval/SotaScorecardTest.kt` — hermetic counter test + D15
  band-map + TORGO-run D15 assertions.
- `core/eval/build.gradle.kts` — forward `-Dsota.rules`. · `Makefile` — `sota-score` passes `-Dsota.rules`.
- `docs/product/2026-07-08_sota-domain-bands.md` — R1. · `core/eval/build/sota-scorecard.md` — regenerated.

### Not attempted this session (remain as plan)

CP-1 encoder build (D-QBE-EVAL / N+12 ≤2MB student), MFCC dual-cascade (D-MFCC-CASCADE), D7 `--emit`
wiring (D-D7-EMIT — cheap next step), CommonVoice rank-1-Δ (D-CV), enrollment/vocab sweeps
(D-ENROLLSWEEP/D-VOCABSWEEP), JMH latency + energy proxies (D-JMH/D-ENERGY), real-noise/RIR
(D-NOISE/D-RIR). All are pre-registered above with runnable commands; env deps confirmed present.

### Honesty note

D15 is the **only** domain that reaches a *green* 800 in-env; it is structural (guardrail mechanization),
excluded from the shipped-system composite. No accuracy/proxy number was banked as a band this session —
the composite remains `<600`, bound by D2/D3/D5.
