<!-- SOTA domain band structure: 15 code-relevant domains, SOTA=1000, bands at 600/700/800/900/950. Standing reference. -->

# SpeechAngel — SOTA Domain Bands (Code-Relevant, Real-World Metrics)

**Date:** 2026-07-08 · **SOTA = 1000 (theoretical maximum for SpeechAngel's constraint set)**
Companion to `docs/product/2026-07-08_score-band-pathway.md` (product-level scorecard pathway)
and `docs/product/2026-07-08_sota-wake-word-reference.md` (the authoritative external SOTA reference).

---

## Scope and constraint set

Every domain is bounded by SpeechAngel's hard constraints, which define the SOTA=1000 ceiling:

- **Speaker-dependent** (not speaker-independent — the user trains their own commands)
- **Language-independent** (no ASR, no phonemes, no language model — template/embedding matching)
- **On-device** (no cloud, model ≤ ~2 MB, no GPU)
- **Arbitrary-word enrollment** (1-shot, any word in any language, not a fixed vocabulary)
- **Deterministic command→action** (not an LLM agent)

SOTA=1000 means: a hypothetical system that achieves the best known result on each axis
*while preserving all five constraints*. No system has ever achieved this; PD-DWS breaks
language-independence, Porcupine breaks arbitrary-word, Euphonia breaks on-device. SOTA=1000
is the aspirational, constraint-preserving ceiling.

**Validation rule:** Every band threshold must be verifiable by a specific measurement script
(runnable on this host or on a physical Android device). No theoretical derivations, no
hand-waves.

---

## Domain 1: Closed-set rank-1 accuracy

**What:** Rank-1 (nearest-template) correctness on dysarthric speech, threshold-free.
The pure discrimination signal — can the system tell commands apart?

| Band | Dysarthric aggregate | Per-severity (mild/mod/severe) | Verification |
|------|---------------------|-------------------------------|-------------|
| **SOTA=1000** | ≥95% | ≥98% / ≥95% / ≥90% | — (no system achieves this constraint-preserving) |
| **950** | ≥90% | ≥95% / ≥90% / ≥85% | — |
| **900** | ≥85% | ≥90% / ≥85% / ≥80% | `:core:eval:test -Dtorgo.dir=... -Dtorgo.grid=true` |
| **800** | ≥75% | ≥80% / ≥75% / ≥70% | `:core:eval:test` |
| **700** | ≥65% | ≥70% / ≥65% / ≥60% | `:core:eval:test` |
| **600** | ≥55% | — | `:core:eval:test` |
| **Current** | **59.2%** (static MFCC) | F01=71.9% mild, F03=56.8% mod, F04=60.0% sev | `TorgoEval.analyze()` |

**Measurement:** `core:eval:test` → `TorgoEval.analyze()` → rank-1 per speaker, k=5 round-robin,
EnergyVAD trim, threshold-free. Validation script: `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo`.

**Ceiling evidence:** WavLM-L12 pooled-cosine **71.9%** (700 band, McNemar p=2×10⁻⁶ vs MFCC).
But this is a 95M-param English-only research probe — not a deployable artifact and not
language-independent verified. The deployable ~1-2M student must reach the 700 band or better.

**External SOTA reference:** ZP-KWS ~29-33% FRR@1%FAR (zero-shot, language-agnostic, 1.55M params).
That's the constraint-matched rank-1 ceiling proxy — ~70-67% upper bound if FAR=0 (roughly).

---

## Domain 2: FRR at matched deployment-scale FAR (≤5 FAR/hr)

**What:** Open-set false reject rate when the acceptance threshold is set to hold ≤5 false accepts
per hour of ambient audio. The deployability-critical combined discrimination+rejection metric.

| Band | FRR @ ≤5 FA/hr (dysarthric) | Deploy-slice FRR (≤25 cmds) | Verification |
|------|---------------------------|------------------------------|-------------|
| **SOTA=1000** | ≤0.5% | ≤0.5% | — (PD-DWS level, constraint-broken) |
| **950** | ≤2% | ≤3% | `:core:eval:test` + `AmbientFar` |
| **900** | ≤5% | ≤5% | `:core:eval:test` + `AmbientFar` |
| **800** | ≤15% | ≤15% | `:core:eval:test` + `AmbientFar` |
| **700** | ≤35% | ≤35% | `:core:eval:test` + `AmbientFar` |
| **600** | ≤55% | — | `:core:eval:test` + `AmbientFar` |
| **Current** | **75.7%** (static = shipped; `delta_delta` variant 78.3%) | **70.7%** | `TorgoEval.heldOut()` |

**Measurement:** Held-out leave-one-fold-out threshold selection, matched FAR calibration via
`AmbientFar.measuredResult()`, reported as FRR at the matched operating point. Validation:
`./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.sim.report=true`.

**Binding constraint:** W2 (always-on FA/hr wall). The CP-2 dual-cascade banked win proves
F03 FRR can drop from 50.3%→25.4% at ≤0.5 FA/hr with WavLM embeddings, but the MFCC-DTW
baseline has NOT been evaluated with the dual-cascade at deployment-scale. The deployment-scale
(77-cmd) FRR is ~4-5× worse than the 15-cmd slice — vocabulary distinctness (W1) dominates
until proven otherwise (N+7 fork).

---

## Domain 3: Always-on ambient FA/hr

**What:** False accepts per hour on continuous ambient household audio — the true deployability
blocker. An always-on assistant with >0.5 FA/hr is unusable regardless of FRR.

| Band | FA/hr | Wake-stage detection @ ≤0.5 FA/hr | Verification |
|------|-------|-----------------------------------|-------------|
| **SOTA=1000** | ≤0.01 | ≥99% | Porcupine reference (breaks arbitrary-word) |
| **950** | ≤0.05 | ≥95% | `AmbientFar` on ≥6h real recording |
| **900** | ≤0.1 | ≥90% | `AmbientFar` on ≥6h real recording |
| **800** | ≤0.5 | ≥80% | `AmbientFar` on ≥6h real recording |
| **700** | ≤2 | ≥65% | `AmbientFar` on ≥1h real recording |
| **600** | ≤5 | ≥50% | `PicovoiceBenchmark.measuredResult()` |
| **Current** | **~82 FA/hr** (optimistic proxy) | MFCC in-regime F01=68.8% @ ~0 FA/hr (not ≤0.5) | `AmbientFar.measuredResult()` (proxy) |

**Measurement:** Continuous audio stream, sliding window, debounced. Two protocols:
- **In-regime** (product regime): speaker's own words as wake gate, LibriSpeech background, per-window VAD.
  Validation: `python3 scripts/eval/ssl_frontend_spike/in_regime.py <speakers> <bg_min>`.
- **Real ambient** (G-REALAMB): ≥6h continuous household audio, matched FA/hr calibration.
  Validation: `./gradlew :core:eval:test -Dambient.wav=<path> -Dtorgo.dir=$HOME/torgo`.

**Binding constraint:** The 600 band (≤5 FA/hr, the deployability gate) requires a real ambient
recording — the current ~82 FA/hr proxy is optimistically biased. CP-2's dual-cascade has been
banked at WavLM level (F03 25.4% FRR @ ≤0.5 FA/hr) but needs MFCC-level evaluation and a real
ambient stream. The Picovoice benchmark already proves there is no cross-speaker operating point
that is both sensitive and quiet (119 FA/hr at first useful detection) — in-regime measurement is
the binding protocol.

---

## Domain 4: Noise robustness (additive noise at fixed SNR)

**What:** Closed-set rank-1 accuracy degradation under additive white noise at 20/10/5 dB SNR.
Noise is the dominant degrader (proven by the condition grid).

| Band | Rank-1 @ 20 dB | Rank-1 @ 10 dB | Rank-1 @ 5 dB | Verification |
|------|---------------|---------------|--------------|-------------|
| **SOTA=1000** | ≥95% | ≥90% | ≥80% | Porcupine 97.1% @ 10dB reference (atypical untested) |
| **950** | ≥85% | ≥75% | ≥65% | `ConditionEval` |
| **900** | ≥80% | ≥65% | ≥55% | `ConditionEval` |
| **800** | ≥70% | ≥55% | ≥40% | `ConditionEval` |
| **700** | ≥60% | ≥45% | ≥25% | `ConditionEval` |
| **600** | ≥55% | ≥35% | ≥10% | `ConditionEval` |
| **Current** | **56.1%** | **34.1%** | **8.5%** | `ConditionEval.conditionGrid()` |

**Measurement:** `AudioAugment.addNoise()` at calibrated SNR, enrollment clean, query degraded.
Validation: `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.conditions=true`.

**Missing:** MUSAN noise types (babble, music, street) — blocked on ~30 GB corpus download.
RIR far-field convolution — blocked on OpenSLR RIR download. The current grid only covers
additive white noise, not real-world noise types.

---

## Domain 5: Reverb robustness

**What:** Closed-set rank-1 accuracy under simulated room reverberation (RT60 small/medium).

| Band | Rank-1 @ small reverb | Rank-1 @ medium reverb | Verification |
|------|----------------------|------------------------|-------------|
| **SOTA=1000** | ≥95% | ≥95% | — |
| **950** | ≥90% | ≥85% | `ConditionEval` |
| **900** | ≥85% | ≥80% | `ConditionEval` |
| **800** | ≥75% | ≥70% | `ConditionEval` |
| **700** | ≥65% | ≥65% | `ConditionEval` |
| **600** | — | — | (reverb is mild; no band distinction needed) |
| **Current** | **64.6%** (tied with clean) → **`<600`** (below the 700 ≥65% rung) | **69.5%** (better than clean — acoustic variation aids discrimination at small vocab) → **700** | `ConditionEval` |

**Band (wall-dominated, min of the two cells):** small-reverb 64.6% is `<600` (just below the 700
≥65% rung); medium-reverb 69.5% is 700. The domain band is the **min = `<600`**, which is what
`SotaScorecard` reports (it scores the `reverb_small` cell). The composite table below is corrected to
`<600` (was hand-labeled 700 — an optimistic mislabel; **R1**, 2026-07-09).

**Measurement:** `AudioAugment.convolveRir()`. Validation:
`./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.conditions=true` (conditions grid
includes reverb_small and reverb_medium).
**Note:** Reverb is NOT the binding constraint — the condition grid proves it's mild.
The small vocabulary / speaker-dependent nature means room acoustics can actually help
discrimination (timbre variation across commands is preserved, noise floor is not raised).

---

## Domain 6: Bandwidth robustness

**What:** Rank-1 under telephone band-limiting (300-3400 Hz) and typical phone-mic bandpass.

| Band | Rank-1 @ 300-3400 Hz | Verification |
|------|----------------------|-------------|
| **SOTA=1000** | ≥95% | — |
| **950** | ≥90% | `ConditionEval` |
| **900** | ≥85% | `ConditionEval` |
| **800** | ≥75% | `ConditionEval` |
| **700** | ≥65% | `ConditionEval` |
| **Current** | **65.9%** | Already in 700 band |

**Measurement:** `AudioAugment.bandLimit(300, 3400)`. Validation: same as Domain 4.
**Note:** Speech energy is concentrated in-band — band-limiting has minimal effect.
Phone-mic bandpass (500-6000 Hz) is untested but likely similarly mild.
Not a binding constraint on its own.

---

## Domain 7: In-regime wake word detection

**What:** Detection rate of the speaker's own wake template when embedded in continuous
background audio, at a measured FA/hr operating point. The product-regime metric
(speaker's own words, not cross-speaker benchmark).

| Band | Detection @ ≤0.5 FA/hr | Verification |
|------|------------------------|-------------|
| **SOTA=1000** | ≥95% | openWakeWord targets (unverified, breaks language-independence) |
| **950** | ≥90% | `in_regime.py` / `dual_cascade_verify.py` |
| **900** | ≥85% | `in_regime.py` / `dual_cascade_verify.py` |
| **800** | ≥75% | `in_regime.py` |
| **700** | ≥65% | `in_regime.py` |
| **600** | ≥50% | `in_regime.py` |
| **Current** | F01 **68.8%** @ ~0 FA/hr (MFCC), F01 **75.0%** @ ~0 FA/hr (WavLM) | `in_regime.py` |

**Measurement:** Product-regime, speaker-dependent. Speaker's own words as gate. LOO detection
against 1.01h LibriSpeech background, per-window VAD, 1.5s/0.5s window, 1.0s refractory.
Validation: `python3 scripts/eval/ssl_frontend_spike/in_regime.py F01 FC01 60`.
Paired McNemar at matched FA/hr via `inregime_paired.py`.

**Note:** Current numbers are @ ~0 FA/hr (not ≤0.5 FA/hr — the strict matched operating point
has not been calibrated yet for MFCC). The CP-2 dual-cascade banked win uses WavLM and needs
MFCC-level replication.

---

## Domain 8: Dual-cascade rejection gain

**What:** FRR reduction at matched FA/hr from the dual-filter cascade (distance + duration-ratio
+ optionally margin-ratio cross-verify) vs. the single-threshold baseline. The primary CP-2 lever.

| Band | Rel FRR reduction (dysarthric) | F03 absolute FRR @ ≤0.5 FA/hr | Verification |
|------|-------------------------------|------------------------------|-------------|
| **SOTA=1000** | ≥60% rel | ≤10% | PD-DWS level (constraint-broken) |
| **950** | ≥50% rel | ≤15% | `dual_cascade_verify.py` |
| **900** | ≥40% rel | ≤20% | `dual_cascade_verify.py` |
| **800** | ≥30% rel | ≤30% | `dual_cascade_verify.py` |
| **700** | ≥20% rel | ≤40% | `dual_cascade_verify.py` |
| **600** | ≥10% rel | ≤50% | `dual_cascade_verify.py` |
| **Current** | **BANKED**: F03 50.3%→25.4% (49.5% rel, p<0.001) — **WavLM only** | F03 **25.4%** @ ≤0.5 FA/hr (WavLM), MFCC NOT EVALUATED | `dual_cascade_verify.py` |

**Measurement:** 3D grid search (distance × |log(dur_ratio)| × margin_ratio), per-(query,template)-pair
features, 1.01h LibriSpeech background, matched ≤0.5 FA/hr, paired McNemar + exact binomial.
Validation: `python3 scripts/eval/ssl_frontend_spike/dual_cascade_verify.py <speakers> <bg_min>`.

**Critical gap:** The banked win is WavLM-only. The MFCC-DTW dual-cascade has NOT been evaluated
at deployment scale. The F03 F04 (deployment-slice) numbers are needed to confirm the lever
transfers to the shippable front-end.

**Control safety:** Verified — no regression on FC01/FC02/FC03 (b=0, n=740). Safe for typical speech.

---

## Domain 9: SSL embedding quality (deployable encoder)

**What:** Rank-1 accuracy of the deployable (≤2 MB, on-device, language-independent trained)
few-shot encoder, at matched held-out FAR on real dysarthric audio.

| Band | Rank-1 (dysarthric) | Param count | Language-independence verified | Verification |
|------|--------------------|-------------|-------------------------------|-------------|
| **SOTA=1000** | ≥85% | ≤1.5M | Yes (multilingual eval) | ZP-KWS class (1.55M, FRR@1%FAR ~29-33%) |
| **950** | ≥80% | ≤2M | Yes | `:core:eval:test` + `QbeEncoder` seam |
| **900** | ≥75% | ≤2M | Yes | `:core:eval:test` + `QbeEncoder` seam |
| **800** | ≥70% | ≤5M | Partial (English proven, multilingual pending) | `:core:eval:test` |
| **700** | ≥65% | ≤10M | Partial | `:core:eval:test` or `sweep_ssl.py` |
| **600** | ≥60% | any | Not required | `sweep_ssl.py` (ceiling probe) |
| **Current** | **CEILING ONLY**: WavLM-L12 71.9% (95M, English-only). Deployable student: **NOT BUILT** | — | — | `sweep_ssl.py` |

**Measurement:** Two stages:
- **Ceiling** (600-700 band): frozen HuggingFace encoder, CPU-only Python.
  Validation: `python3 scripts/eval/ssl_frontend_spike/sweep_ssl.py <speakers>`.
- **Deployable** (800+ band): Android QbeEncoder interface, ONNX/TFLite, INT8.
  Validation: `./gradlew :core:eval:test -Dtorgo.dir=... -Dqbe.model=<path>`.

**Binding constraint:** CP-1 build. The 2×2 decomposition proved the lever is a fixed-dim QbE
embedding + cosine prototypes, not a front-end swap (WavLM+DTW ties MFCC-DTW; MFCC+pooling drops
to 39.3%). DistilHuBERT (~23M, 65.9%) is the current size floor. ZP-KWS (1.55M, ~29-33% FRR)
is the constraint-matched SOTA reference. The N+9 DistilHuBERT size-floor experiment is pre-registered
but unrun.

---

## Domain 10: Language independence

**What:** Rank-1 accuracy on non-English audio, measured against the English TORGO baseline.
The #1 product differentiator (95/100 axis).

| Band | Non-English delta vs English | Multilingual eval coverage | Verification |
|------|------------------------------|---------------------------|-------------|
| **SOTA=1000** | Δ ≤ 5pp | ≥5 languages, ≥2 non-Indo-European | Common Voice + EasyCall |
| **950** | Δ ≤ 10pp | ≥3 languages | Common Voice |
| **900** | Δ ≤ 15pp | ≥3 languages | Common Voice |
| **800** | Δ ≤ 20pp | ≥2 languages | Common Voice |
| **700** | Δ ≤ 30pp | 1 language | Common Voice (single language) |
| **600** | Any measurable signal | 1 language | `:core:eval:test` with non-English WAV |
| **Current** | **NO BASELINE** | **Zero non-English data tested** | — |

**Measurement:** Common Voice (CC0, multilingual) loaded via a new `CommonVoiceCorpus` in `core:eval`.
Same speaker-dependent, held-out protocol as Domain 1. Compare rank-1 and FRR@FAR across languages.
Validation: `./gradlew :core:eval:test -Dcommonvoice.dir=<path> -Dcommonvoice.lang=fr`.

**Binding constraint:** W4. The entire language-independence claim rests on the architecture
(template matching, no ASR) — it has never been empirically verified. The N+8 Common Voice
experiment is pre-registered but unrun. gated on Common Voice download (~hours).

---

## Domain 11: On-device latency

**What:** End-to-end latency from end-of-utterance to action dispatch, measured on a physical
Android device. Must be <200 ms for real-time feel.

| Band | P50 latency | P99 latency | Frame-processing overhead | Verification |
|------|------------|------------|--------------------------|-------------|
| **SOTA=1000** | ≤50 ms | ≤100 ms | ≤1 ms/frame | Android Macrobenchmark |
| **950** | ≤100 ms | ≤200 ms | ≤2 ms/frame | Android Macrobenchmark |
| **900** | ≤150 ms | ≤300 ms | ≤5 ms/frame | `androidTest` + `Trace` |
| **800** | ≤200 ms | ≤500 ms | ≤10 ms/frame | `androidTest` |
| **700** | ≤500 ms | ≤1 s | ≤20 ms/frame | Emulator `dumpsys` |
| **600** | ≤1 s | ≤2 s | — | Emulator timestamp log |
| **Current** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | Emulator has silent mic |

**Measurement:** Android `Trace.beginSection`/`endSection` around VAD+MFCC+DTW+dispatch, reported
via `systrace`/Perfetto. Off-device JMH benchmarks for per-component latency (FFT, MFCC per-frame,
DTW at typical sizes). Validation: `./gradlew :core:eval:jmh` (JMH, off-device); `./gradlew
:app:connectedAndroidTest` (on-device).

**Binding constraint:** G-DEVICE. Every on-device number is UNKNOWN. JMH benchmarks are planned
but not built (Phase-3 perf items). The emulator's silent mic prevents end-to-end measurement.

---

## Domain 12: On-device resource (battery, CPU, RAM)

**What:** Battery drain (%/hr active listening), CPU % (when silent vs when recognizing),
resident RAM. Production SOTA: <5%/hr battery, <1% CPU when silent.

| Band | Battery %/hr (active) | CPU % (silent / active) | RAM (MB) | Verification |
|------|----------------------|------------------------|----------|-------------|
| **SOTA=1000** | ≤2% | ≤0.5% / ≤5% | ≤50 | openWakeWord reference (RPi3, 15-20 models/core) |
| **950** | ≤5% | ≤1% / ≤10% | ≤80 | `BatteryHistorian` + `dumpsys` |
| **900** | ≤8% | ≤2% / ≤15% | ≤100 | `BatteryHistorian` + `dumpsys` |
| **800** | ≤12% | ≤5% / ≤25% | ≤150 | `dumpsys batterystats` |
| **700** | ≤20% | ≤10% / ≤40% | ≤200 | `dumpsys batterystats` |
| **600** | ≤30% | ≤20% / ≤60% | ≤300 | Emulator estimate |
| **Current** | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** | Emulator cannot measure |

**Measurement:** `dumpsys batterystats --reset --charged`, 1h active listening + 1h idle, `dumpsys
batterystats --checkin`. CPU via `top`/`pidstat`. RAM via `dumpsys meminfo`. Validation: physical
device only — no emulation possible.

---

## Domain 13: Enrollment efficiency

**What:** Number of enrollment recordings needed to reach saturation (diminishing returns on
per-template FRR). Lower = better for the target population (effort per command).

| Band | Templates to saturation | 1-shot FRR (% of saturation) | Verification |
|------|------------------------|------------------------------|-------------|
| **SOTA=1000** | 1 | 100% | — |
| **950** | 2 | ≥90% | `TorgoEval` enrollment-count sweep |
| **900** | 3 | ≥85% | `TorgoEval` enrollment-count sweep |
| **800** | 3 | ≥80% | `TorgoEval` enrollment-count sweep |
| **700** | 5 | ≥70% | `TorgoEval` enrollment-count sweep |
| **600** | 5 | ≥60% | `TorgoEval` enrollment-count sweep |
| **Current** | **≥3** (saturates) | 1-shot FRR ~75.7% (not relative to saturation — absolute) | `TorgoEval` enrollment-count sweep |

**Measurement:** Monte Carlo enrollment sweep (k=5 folds, fixed test set, 5 iterations per count),
rank-1 and FRR at each count, reported as fraction of k=5 saturation. Validation:
`./gradlew :core:eval:test -Dtorgo.dir=...` → enrollment-count experiment.

**Note:** Multi-template enrollment is a second-order lever (≤5.4% rel FRR reduction at WavLM level,
single-session=0). The saturation point at k≥3 is confirmed. The utility is not from FRR gains
but from enrollment-condition diversity (multi-condition augmentation).

---

## Domain 14: Vocabulary size scaling

**What:** Rank-1 accuracy as a function of vocabulary size (number of enrolled commands).
The dominant degrader for large-vocab speakers (F03=77 cmds, FRR=68% vs F01=15 cmds, FRR=35%).
This is W1 — the vocabulary distinctness wall.

| Band | Rank-1 @ 77-cmd vocabulary | FRR degradation slope per doubling | Verification |
|------|---------------------------|-----------------------------------|-------------|
| **SOTA=1000** | ≥90% | ≤2pp/doubling | `TorgoEval` vocab-size curve |
| **950** | ≥85% | ≤3pp/doubling | `TorgoEval` vocab-size curve |
| **900** | ≥80% | ≤4pp/doubling | `TorgoEval` vocab-size curve |
| **800** | ≥70% | ≤6pp/doubling | `TorgoEval` vocab-size curve |
| **700** | ≥60% | ≤8pp/doubling | `TorgoEval` vocab-size curve |
| **600** | ≥50% | ≤10pp/doubling | `TorgoEval` vocab-size curve |
| **Current** | F03=56.8% (77-cmd) vs F01=71.9% (15-cmd) | ~5-8pp/doubling confirmed (E08-01) | `TorgoEval` vocab-size curve |

**Measurement:** Sub-sample vocabulary sizes, measure rank-1 and FRR at each, fit log-linear slope.
Validation: `./gradlew :core:eval:test -Dtorgo.dir=...` → vocab-size experiment.

**Binding constraint:** W1. The N+7 vocabulary-optimized enrollment experiment is the decisive fork:
if ≤10% FRR at 77-cmd with optimized vocabulary → distinctness is the binding constraint (fix
vocabulary, not encoder); if ~25% → embedding quality is binding (build CP-1 encoder). This is
the single most important unrun experiment.

---

## Domain 15: Robustness gate coverage (guardrail completeness)

**What:** The fraction of EVAL-critical guardrails that are hard gates (not advisory). Tracks the
mechanization of measurement discipline — the "guardrail promotion ladder" from AGENTS.md §4.9.

| Band | Hard gates / total EVAL gates | Contracts promoted | Verification |
|------|------------------------------|-------------------|-------------|
| **SOTA=1000** | 5/5 | EVAL-001..005 → hard gates + contracts | `run-all.mjs` PASS |
| **950** | 4/5 | 4 rules promoted to contracts | `run-all.mjs` PASS |
| **900** | 3/5 | 3 rules promoted | `run-all.mjs` PASS |
| **800** | 2/5 | 2 rules promoted | `run-all.mjs` PASS |
| **700** | 1/5 | 1 rule promoted | `run-all.mjs` PASS |
| **600** | 0/5 | 0 promoted (all advisory) | `run-all.mjs` + manual EVAL check |
| **Current** | **Partial: 3 hard-checks covering EVAL-002/003/004/005 citations + fidelity** (EVAL-001 advisory-only) | **eval-measurement-discipline + sota-band-consistency contracts active** | `verify-sota-measurement.mjs` |

**Measurement:** Count of hard-gated EVAL rules in `scripts/audits/run-all.mjs` vs the 5 rules
in `ACTIVE_DEV_RULES.md`. Each promoted rule must have: a contract entry in
`workflow-boundary-contracts.json`, a hard-gate verifier in `scripts/audits/`, and a `classify.mjs`
match pattern that surfaces the contract.

**Current state:** `verify-sota-measurement.mjs` (created 2026-07-08) enforces three hard checks:
(1) EVAL-002/003/005 citation in testing docs, (2) EVAL-004 fidelity-reproduction statements on
delta claims, (3) honesty-banner presence on generated eval reports. Advisory warnings cover
S-tier experiment staleness (plan-file check) and negated-citation detection. EVAL-001
(pre-registration as a distinct sequential gate) remains advisory-only. Two boundary contracts
are active (`eval-measurement-discipline`, `sota-band-consistency`). This is the first rung on
the guardrail promotion ladder — 3 hard checks + 2 contracts from zero.

---

## Composite SOTA band map

| Domain | 600 | 700 | 800 | 900 | 950 | SOTA=1000 | Current band |
|--------|-----|-----|-----|-----|-----|-----------|-------------|
| 1. Rank-1 accuracy | ≥55% | ≥65% | ≥75% | ≥85% | ≥90% | ≥95% | **600** (59.2%) |
| 2. FRR @ ≤5 FA/hr | ≤55% | ≤35% | ≤15% | ≤5% | ≤2% | ≤0.5% | **<600** (75.7%) |
| 3. Ambient FA/hr | ≤5 | ≤2 | ≤0.5 | ≤0.1 | ≤0.05 | ≤0.01 | **<600** (~82) |
| 4. Noise @ 20dB | ≥55% | ≥60% | ≥70% | ≥80% | ≥85% | ≥95% | **600** (56.1%) |
| 5. Reverb robustness | — | ≥65% | ≥75% | ≥85% | ≥90% | ≥95% | **<600** (64.6% small; R1 2026-07-09) |
| 6. Bandwidth robustness | — | ≥65% | ≥75% | ≥85% | ≥90% | ≥95% | **700** (65.9%) |
| 7. Wake detection @ ≤0.5 FA/hr | ≥50% | ≥65% | ≥75% | ≥85% | ≥90% | ≥95% | **600** (~69% @ ~0 FA/hr) |
| 8. Dual-cascade rejection | ≥10% rel | ≥20% rel | ≥30% rel | ≥40% rel | ≥50% rel | ≥60% rel | **900** (49.5% WavLM) |
| 9. SSL embedding quality | ≥60% | ≥65% | ≥70% | ≥75% | ≥80% | ≥85% | **<600** (NOT BUILT) |
| 10. Language independence | signal | Δ≤30pp | Δ≤20pp | Δ≤15pp | Δ≤10pp | Δ≤5pp | **<600** (ZERO baseline) |
| 11. Latency (P50) | ≤1s | ≤500ms | ≤200ms | ≤150ms | ≤100ms | ≤50ms | **<600** (UNKNOWN) |
| 12. Battery/resource | ≤30%/hr | ≤20%/hr | ≤12%/hr | ≤8%/hr | ≤5%/hr | ≤2%/hr | **<600** (UNKNOWN) |
| 13. Enrollment efficiency | ≥60% | ≥70% | ≥80% | ≥85% | ≥90% | 100% | **600-700** (saturates ≥3) |
| 14. Vocab size scaling | ≥50% | ≥60% | ≥70% | ≥80% | ≥90% | ≥90% | **600** (56.8% @ 77cmd) |
| 15. Guardrail coverage | 0/5 | 1/5 | 2/5 | 3/5 | 4/5 | 5/5 | **600** (3 hard checks + 2 contracts, this commit) |

---

## The binding constraints (walls)

1. **Domain 3 (Ambient FA/hr):** The deployability blocker. Until ≤0.5 FA/hr is reached on real
   ambient audio, no other domain matters. Current: ~82 FA/hr proxy, ~160× from target.
2. **Domain 14 (Vocabulary size scaling):** The largest accuracy wall. 8× FRR gap between 15-cmd
   and 77-cmd vocabulary. The N+7 fork decides whether vocabulary distinctness (W1) or embedding
   quality (W3) is binding.
3. **Domain 9 (SSL embedding):** The deployable encoder does not exist. The ceiling is proven
   (71.9% WavLM), but the ~1-2M student is unbuilt.
4. **Domain 10 (Language independence):** The #1 differentiator has zero empirical evidence.
   Architecture-only claim; needs Common Voice measurement.
5. **Domain 11-12 (Device metrics):** ALL UNKNOWN. Blocked on physical device access.

## The two best-measured domains

- **Domain 5 (Reverb):** Already at 700 band — reverb is mild, not a constraint.
- **Domain 8 (Dual-cascade):** WavLM-level banked win at 900 band. Needs MFCC replication.

---

## Validation scripts index

| Domain | Script | Command |
|--------|--------|---------|
| 1, 2, 4, 5, 6, 13, 14 | `core:eval:test` (Kotlin) | `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.grid=true` |
| 3, 7, 8 | `dual_cascade_verify.py` (Python) | `python3 scripts/eval/ssl_frontend_spike/dual_cascade_verify.py <speakers> <bg_min>` |
| 7 | `in_regime.py` (Python) | `python3 scripts/eval/ssl_frontend_spike/in_regime.py <speakers> <bg_min>` |
| 9 | `sweep_ssl.py` (Python) | `python3 scripts/eval/ssl_frontend_spike/sweep_ssl.py <speakers>` |
| 10 | `CommonVoiceCorpus.kt` (NOT BUILT) | `./gradlew :core:eval:test -Dcommonvoice.dir=<path>` |
| 11, 12 | Android `androidTest` (NOT BUILT) | `./gradlew :app:connectedAndroidTest` |
| 15 | `verify-sota-measurement.mjs` (Node) | `node scripts/audits/verify-sota-measurement.mjs` |

---

## Method note

Every band threshold is verifiable by running the specified script on this host (except Domains
11-12, which require a physical device). No theoretical derivations, no hand-waves. Bands are
set such that:
- **600** = the deployability floor — the minimum to be a viable product
- **700** = SOTA-track — competitive with modest neural baselines
- **800** = production-class — competitive with shipped OSS systems (Howl/openWakeWord)
- **900** = SOTA-class — competitive with the best published results, constraint-preserving
- **950** = near-perfect — close to the constraint-matched SOTA ceiling
- **1000** = theoretical maximum — best known result on any axis, all five constraints preserved
  (no system achieves this; the reference is the best per-axis from the SOTA competitive bar)
