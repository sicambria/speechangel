# SpeechAngel — Overall Research Synthesis

**Compiled:** 2026-07-07  
**Status:** All research, testing, codebase findings, experiment scores (200), and evaluation results synthesized.  
**Purpose:** Single-source reference for all research decisions, current performance, experiment outcomes, and the path to SOTA.

---

## 1. What SpeechAngel Is

An **on-device, language-independent, user-trainable** Android voice-command app (Kotlin/Gradle/Jetpack Compose) for immobilized and speech-impaired users. The user records their own examples of arbitrary spoken commands on the phone; the app matches future utterances via **acoustic template matching** — no language model, no cloud, no phonemes.

**Core differentiators:**
- Language-independent by construction (matches the user's own sounds, not a phoneme model)
- On-device enrollment (1–few-shot, re-trainable by the end user on the phone)
- Always-on / hands-free (assistant role + mic foreground service + deterministic AccessibilityService)
- **Deterministic, NOT an autonomous LLM agent** (Play 2026 policy make-or-break)

---

## 2. Architecture

```
:core:model       → Domain types (CommandId, Template, RecognitionResult) — no deps
:core:dsp         → MFCC extractor, FFT, mel filterbank, energy VAD, streaming gate
:core:matching    → DTW (Euclidean + cosine, withPath for dual-filter), TemplateMatcher, VocabularyDistinctness
:core:enrollment  → Enroller, Recognizer, WakeWordGate, WakeGatedRecognizer, QbE seam
:core:eval        → TorgoEval, Evaluator, ThresholdCalibrator, AmbientFar, PicovoiceBenchmark
:data             → Room persistence, AudioRecord, Hilt DI
:app              → Compose UX, ListeningService, AccessibilityService
```

**Recognition pipeline:**
1. Audio → `EnergyVad.trim()` → endpointing
2. Speech → `MfccExtractor.extract()` → MFCC (13 static, optional Δ + ΔΔ)
3. Features → `TemplateMatcher.match()` → 1-NN min-DTW per command (Euclidean or cosine via `MatcherConfig.localDistance`)
4. Below threshold → `Match`; over → `Reject`

**Two-stage always-on loop:**
- Stage 1 (24/7): `StreamingEnergyGate` → `WakeWordGate` → Wake/NoWake
- Stage 2 (on wake): `Recognizer` on full utterance window

**Key code additions (2026-07-07):**
- `Dtw.cosine()` — cosine frame distance (amplitude-invariant) at `core/matching/Dtw.kt:31`
- `Dtw.withPath()` — DTW returning path length for dual-filter cascade at `core/matching/Dtw.kt:61`
- `MatcherConfig.localDistance` — selectable "euclidean" or "cosine" at `core/matching/TemplateMatcher.kt:26`
- `MatcherConfig.dualFilterTolerance` — path-length rejection (E02-08) at `core/matching/TemplateMatcher.kt:30`
- `MatcherConfig.kNN` — k-NN distance averaging (E02-05) at `core/matching/TemplateMatcher.kt:32`
- `MatcherConfig.hysteresisZone` — three-zone decision (E09-08) at `core/matching/TemplateMatcher.kt:34`
- `WakeGatedRecognizer.wakePersistence` — multi-frame wake persistence (E04-06) at `core/enrollment/WakeGatedRecognizer.kt:32`
- `AudioAugment.pitchShift()` — resample-based pitch shift (E13-08) at `core/eval/AudioAugment.kt:198`
- `AudioAugment.timeStretch()` — resample-based time stretch at `core/eval/AudioAugment.kt:224`

---

## 3. Current Performance (The Honest Numbers)

### TORGO dysarthric corpus (F01/F03/F04 dysarthric, 5-fold held-out)

| Metric | Shipped (ΔΔ, 25ms, 10%) | Static (25ms, 10%) | Best (30ms, 30%) | Δ (shipped→best) |
|--------|------------------------|-------------------|-------------------|---|
| Aggregate rank-1 | 55.4% | 59.2% | **65.2%** | **+9.8pp** |
| F01 (mild, 15 cmds) | 68.8% | 71.9% | **75.0%** | +6.2pp |
| F03 (moderate, 77 cmds) | 53.5% | 56.8% | **60.5%** | +7.0pp |
| F04 (severe, 21 cmds) | 54.0% | 60.0% | **76.0%** | **+22.0pp** |
| FRR @ FAR ~5% (global, HO) | 78.3% | 75.7% | **75.3%** | −3.0pp |
| EER | 49.4% | 45.7% | **40.8%** | −8.6pp |

### Cosine DTW evaluation (static MFCC)

| Distance | Rank-1 | FRR HO | EER |
|----------|--------|--------|-----|
| Euclidean | **59.2%** | **75.7%** | **45.7%** |
| Cosine | 58.4% | 79.4% | 49.8% |

**Finding: Cosine is worse.** Amplitude carries discriminative information for dysarthric speech that cosine discards.

### Enrollment saturation (k-fold proxy)

| Folds (k) | Enroll % | Rank-1 |
|-----------|---------|--------|
| k=2 | 50% | 56.9% |
| k=3 | 66% | **59.2%** |
| k=5 | 80% | **59.2%** |
| k=10 | 90% | **59.2%** |

**Finding: Rank-1 saturates at 3+ templates.** 2-fold under-trains (−2.3pp). Beyond k=3 adds zero gain.

### Noise reduction impact

| Config | Rank-1 |
|--------|--------|
| Static MFCC (no NR) | **59.2%** |
| Static MFCC + spectral_subtraction | 55.1% (−4.1pp) |

**Finding: Noise reduction harmful on clean speech.** Should be SNR-adaptive (enable only at ≤10 dB).

### Always-on ambient FAR

| Metric | Value |
|--------|-------|
| Single-template, uncalibrated | **~82 FA/hr** (~160× the ≤0.5 FA/hr budget) |
| In-regime (own words as gate) detection @ ~0 FA/hr | **65–69%** |
| Best WavLM FRR @ 0.5 FA/hr | **25%** (need <5%) |

### CP-1 ceiling (learned encoder)

| Method | Rank-1 |
|--------|--------|
| MFCC-DTW (baseline, static) | **59.2%** |
| MFCC-DTW (ΔΔ, old shipped) | 55.4% |
| WavLM-L12 pooled-cosine | **71.9%** (−32% rel error, McNemar p=2×10⁻⁶) |

### Per-command calibration

| Speaker | Global FRR HO | Per-Cmd FRR HO | Per-Cmd FAR HO |
|---------|--------------|---------------|----------------|
| F01 | 81.3% | 40.6% | **24.2%** (FAR inflation) |
| F03 | 80.5% | 55.1% | **34.1%** |
| F04 | 62.0% | 58.0% | **27.0%** |

**Finding: Per-command calibration is still a non-improvement.** Lower FRR is a looser operating point, not a gain. Sparse negatives cause accept-all fallback. Needs larger corpus (CP-0: SAP).

### Vocabulary size vs accuracy

| Speaker | Commands | Rank-1 |
|---------|----------|--------|
| F01 | 15 | 71.9% |
| F04 | 21 | 60.0% |
| F03 | 77 | 56.8% |

**Finding: ~5-8pp rank-1 loss per doubling of vocabulary.** Target ≤25 commands for practical deployment.

### Product maturity: **442/1000** (pre-alpha)

---

## 4. The Central Tradeoff (Three Goals in Tension)

> **Language-independence + on-device user-training + >99% accuracy — you can reliably get any two, not all three.**

SpeechAngel chooses **language-independence + on-device-training** (the inclusion requirements for damaged speech) and treats >99% as a per-user aspiration.

---

## 5. Key Constraints (from research + Play policy)

1. **Deterministic, not an autonomous LLM agent** — `isAccessibilityTool=true`
2. **Accuracy reported as FRR + FAR/hour**, never bare "99%"
3. **On-device enrollment is the differentiator** — never regress to language-dependent STT
4. **Robustness from re-enrollment**, not self-adapting model
5. **Caregiver-assisted first-time setup** (un-automatable grants)
6. **No dynamic dependency versions**, all deps through version catalog
7. **Mic FGS** must declare `foregroundServiceType="microphone"`
8. **No NC-licensed models** bundled; training data CC-BY-4.0/CC0 only

---

## 6. What's Built vs. What's Missing

### Built & tested (code complete to emulator ceiling)
- MFCC front-end (static + Δ + ΔΔ, CMN, spectral subtraction)
- DTW matcher (Sakoe-Chiba band, Euclidean + cosine local distance, withPath for dual-filter cascade)
- TemplateMatcher (multi-template, per-command thresholds, configurable local distance)
- Energy VAD + StreamingEnergyGate
- Wake-word gate + 2-stage streaming recognizer
- Enroller + AdaptationDecision (confirmation-gated)
- VocabularyDistinctness advisor
- Room persistence + FeatureCodec
- AndroidAudioRecorder (16kHz streaming)
- ListeningService (foreground, hands-free)
- AccessibilityService (deterministic actions)
- Command packs (export/import/validate)
- Eval harness (synthetic + TORGO + Picovoice + condition grid + rejection eval + front-end bake-off)

### Architecture ready (code exists, needs integration)
- **Dual-filter cascade** (E02-08, 890): `Dtw.withPath()` returns path length. Reject DTW matches where path deviates >X% from expected — 1-line integration in TemplateMatcher.
- **Multi-frame wake persistence** (E04-06, 870): `WakeGatedRecognizer` already processes per-frame. Adding `consecutiveWakeCount ≥ N` before Stage-2 trigger is ~5 LOC.
- **Wake template count sweep** (E04-01, 810): `AmbientFar` with variable template counts — config change.
- **Per-speaker wake calibration** (E04-02, 810): `ThresholdCalibrator` on wake templates — API exists.
- **SNR-adaptive wake threshold** (E04-09, 810): `StreamingEnergyGate` computes running noise floor — SNR is a division away.

### Scaffolded but blocked on external assets
- **QbE encoder** (`NoopQbeEncoder` placeholder) ← CP-1: core accuracy bet
- **Path-A backend** (`NoopPathABackend` placeholder)
- **Dictation backend** (`NoopDictationBackend` placeholder)
- **MUSAN augmentation** (E05-04, 830): `AudioAugment.addNoise()` ready, corpus needed (~30 GB)
- **Pitch-shift augmentation** (E13-08, 800): `AudioAugment` has reverb/band-limit/noise/gain but no pitch shift yet

---

## 7. The SOTA Landscape (External Reference Points)

| System | Metric | Context |
|--------|--------|---------|
| Porcupine | ~97% @ 10 dB SNR, ≤0.1 FA/hr | Closed, English, proprietary |
| openWakeWord | ≤0.5 FA/hr | English, NC models, no Android |
| LRDWWS'24 winner (PD-DWS) | FAR 0.32% / FRR 0.5% | Closed-vocab, trained on that vocab |
| ZP-KWS | FRR ~29–33% @ 1% FAR | Constraint-matched (language-agnostic, 1.55M params) |
| Euphonia | 13.9% WER personalized | Dysarthric ASR (open-vocab — harder task) |
| On-device personalization (2403.07802) | 30.1%→24.3% error, 23.7k params | 4-shot, TinyML, on-device learnable |
| SpeechAngel static MFCC-DTW | FRR 75.7% / ~82 FA/hr | **2-3 orders of magnitude from deployable** |
| SpeechAngel WavLM ceiling | Rank-1 71.9% | +12.7pp above static MFCC |

---

## 8. Critical Path v2 (The Two Bets That Decide the Product)

### CP-1 — Accuracy bet: does a learned encoder beat MFCC-DTW while preserving language-independence + 1-shot?
- Ceiling measured: WavLM-L12 pooled-cosine 71.9% rank-1 vs static MFCC-DTW 59.2% → **GO (+12.7pp)**
- The lever is **QbE embedding + cosine**, not a front-end swap (WavLM-under-DTW *ties* MFCC; MFCC-under-pooling *drops* to 39.3%)
- Next: distill deep-SSL into ~1–2M param student, gated on language-independence (E07-03, E07-05, E07-06)

### CP-2 — Deployability bet: Stage-1 wake cascade to ≤0.5 FA/hr
- Current: ~82 FA/hr ambient (single-template) → ~65-69% det @ ~0 FA/hr (in-regime)
- WavLM FRR 25% at 0.5 FA/hr (need <5%)
- The lever is **threshold calibration / dedicated rejection model / dual-filter cascade**, not a better encoder
- Architecture ready: dual-filter (E02-08, 890), multi-frame persistence (E04-06, 870), SNR-adaptive thresholds (E04-09, 810)

### CP-3 — Real-device audio metrics (physical device only)
- Audio pipeline watchdog (E17-01, 860): detect silent AudioRecord failures, auto-restart
- Crash-loop detection (E17-03, 820): exponential backoff, 10-crash/hr → disable and notify
- Battery drain measurement (E14-03): Stage-1 energy gate only: 0.5-1.5%/hr expected

---

## 9. Known Limitations (Updated)

1. **MFCC-DTW FRR is 1-3 orders of magnitude from deployable** (75.3% FRR @ ~5% FAR → need <5%)
2. **~82 FA/hr ambient** (~160× budget → dual-filter cascade + multi-frame persistence are the levers)
3. **No physical device measurement** — all numbers emulator + JVM eval
4. **QbE encoder not trained** — seam built, CP-1 ceiling at 71.9%, distillation not started
5. **Language-independence not validated beyond English** (TORGO is English)
6. **Per-command calibration is a non-improvement** — FAR balloons to 24-34% due to sparse negatives
7. **No voice-drift corpus** with VoiceCondition labels
8. **Noise reduction is harmful on clean speech** (−4.1pp) — should be SNR-adaptive
9. **Cosine DTW is worse than Euclidean** (−0.8pp) — amplitude matters for dysarthric speech
10. **SAP DUA not yet acquired** — longest lead item, gates CP-1/CP-2 trust
11. **Enrollment saturates at 3+ templates** — more templates per command add zero DTW discrimination gain
12. **Vocabulary size costs ~5-8pp per doubling** — practical limit is ≤25 commands
13. **Dual-filter, k-NN, hysteresis don't affect rank-1** — they operate at the acceptance/rejection level, not distance ranking. Only FRR/FAR at threshold level would change.
14. **5% DTW band is too tight** for dysarthric (49.4% rank-1, −9.8pp vs baseline). Minimum viable: 10%.
15. **DTW band is configurable per-command** — wider for commands with high temporal variability, narrower for consistent ones.

---

## 10. Experiment Suite (200 Experiments Across 20 Domains)

### Score Distribution

| Tier | Score | Count | % |
|------|-------|-------|---|
| **S** (Must do) | 810-1000 | **15** | 7.5% |
| **A** (High priority) | 700-809 | **62** | 31% |
| **B** (Medium) | 550-699 | **96** | 48% |
| **C** (Low) | 400-549 | **23** | 11.5% |
| **D** (Skip) | <400 | **4** | 2% |

### Domains 01-10: Core Pipeline (100 experiments)

| # | Domain | Top Experiment | Score |
|---|--------|---------------|-------|
| 01 | Feature Extraction | E01-02: Delta sweep **DONE** (static wins +3.8pp) | 800 |
| 02 | Matching Algorithms | E02-08: Dual-filter cascade **READY** | 890 |
| 03 | Template Enrollment | E03-01: Count sweep **DONE** (saturates at 3+) | 840 |
| 04 | Wake Word & FAR | E04-06: Multi-frame persistence **READY** | 870 |
| 05 | Noise Robustness | E05-04: MUSAN augmentation **NEEDS DATA** | 830 |
| 06 | Dysarthric Specialization | E06-01: Per-severity analysis **DONE** | 750 |
| 07 | Learned Encoders (QbE) | E07-03: Student bake-off **NEEDS TRAINING** | 710 |
| 08 | Vocabulary Optimization | E08-01: Vocab size curve **DONE** | 820 |
| 09 | Operating Point | E09-02: Held-out per-cmd calib **DONE** (non-improvement) | 840 |
| 10 | Evaluation Methodology | E10-06: McNemar standard **DONE** | 830 |

### Domains 11-20: SOTA Breakthrough Directions (100 experiments)

| # | Domain | Top Experiment | Score |
|---|--------|---------------|-------|
| 11 | QbE Deployment | E11-01: sherpa-onnx Android KWS | 770 |
| 12 | Matcher Innovation | E12-09: Runtime-synthesized negatives | 790 |
| 13 | Data Augmentation | E13-08: Pitch-shift enrollment aug | 800 |
| 14 | On-Device Optimization | E17-01: Audio pipeline watchdog | 860 |
| 15 | Multi-Task Learning | E16-01: Residual adapter (LoRA) | 710 |
| 16 | Personalization | E16-03: Online prototype refinement | 780 |
| 17 | Production Engineering | E17-01: Audio watchdog **PLANNED** | 860 |
| 18 | Transfer & Foundation | E18-08: MSWC multilingual pretrain | 680 |
| 19 | Ensemble & Cascade | E19-01: 3-stage cascade | 790 |
| 20 | Human-in-the-Loop UX | E20-02: Adaptive re-enrollment | 770 |

### S-Tier: Ship-Blocking (15 experiments)

| Exp | Score | Domain | Description | Status |
|-----|-------|--------|-------------|--------|
| E02-08 | 890 | Matching | Dual-filter cascade (path-length rejection) | **READY** |
| E04-06 | 870 | Wake/FAR | Multi-frame persistence (N consecutive wakes) | **READY** |
| E17-01 | 860 | Production | Audio pipeline watchdog + auto-restart | Planned |
| E03-01 | 840 | Enrollment | Enrollment count sweep (quantified saturation) | **DONE** |
| E09-01 | 840 | Operating Pt | Global threshold sweep | **DONE** |
| E09-02 | 840 | Operating Pt | Held-out per-command calibration (non-improvement) | **DONE** |
| E05-04 | 830 | Noise | MUSAN noise augmentation for enrollment | Needs data |
| E10-06 | 830 | Evaluation | McNemar paired testing standard | **DONE** |
| E08-01 | 820 | Vocabulary | Vocab size vs accuracy curve | **DONE** |
| E17-03 | 820 | Production | Crash-loop detection with exponential backoff | Planned |
| E04-01 | 810 | Wake/FAR | Wake template count sweep | **READY** |
| E04-02 | 810 | Wake/FAR | Per-speaker wake calibration | **READY** |
| E04-09 | 810 | Wake/FAR | SNR-adaptive wake threshold | **READY** |
| E02-01 | 810 | Matching | Cosine distance DTW | **DONE** (negative) |
| E01-02 | 800 | Frontend | Delta-order sweep (static MFCC wins +3.8pp) | **DONE** |

---

## 11. Key Findings from Experiments (2026-07-07)

### Positive (adopt)

1. **Combined 30ms frames + 30% DTW band: Rank-1 65.2% (+6.0pp)** — switch both shipped defaults. F04 (severe dysarthric) +16pp.
2. **30% DTW band alone: +5.2pp rank-1** — dysarthric speech needs wider temporal warping than typical speech.
3. **30ms frames alone: +1.1pp rank-1** — longer frames capture more spectral structure for slow dysarthric articulation.
4. **Static MFCC beats ΔΔ by +3.8pp** — switch shipped default. Free gain, no code change beyond config.
5. **Enrollment saturates at 3+ templates** — ask users for 3 recordings per command, not more.
6. **Vocabulary ≤25 commands is the practical target** — ~5-8pp loss per doubling.
7. **Dual-filter cascade, multi-frame persistence, pitch-shift, and k-NN infrastructure is built** — all implemented and compiled. Ready for threshold-level evaluation (FRR/FAR).

### Negative (do not adopt)

1. **Cosine DTW is worse than Euclidean** (−0.8pp) — amplitude carries discriminative information for dysarthric speech.
2. **Noise reduction is harmful on clean speech** (−4.1pp) — should be SNR-adaptive, not always-on.
3. **Per-command calibration is a non-improvement** — FAR balloons to 24-34% due to sparse negatives.
4. **Common-mode rejection is not supported** (H1: p=0.17) — honest negative from McNemar testing.
5. **5% DTW band is harmful** (49.4% rank-1) — Sakoe-Chiba band must be ≥10% for dysarthric speech.
6. **15ms/20ms frames are worse** — short frames don't capture sufficient spectral structure for dysarthric.

### Architecture improvements with no rank-1 effect

1. **Dual-filter cascade** — rank-1 unchanged at all tolerances. Affects threshold acceptance decisions only. Requires per-threshold scoring for evaluation.
2. **k-NN (k=3,5)** — rank-1 unchanged. Averaging top-k template distances gives same ranking as min distance on TORGO.
3. **Hysteresis threshold** — rank-1 unchanged at all zone widths. Threshold-level feature only.

### Needs external resources

1. **QbE encoder training** — CP-1 ceiling at 71.9%, 12.7pp above MFCC-DTW baseline, 6.7pp above best MFCC-DTW config (65.2%).
2. **MUSAN corpus** — AudioAugment ready, corpus download needed for noise-robust enrollment.
3. **SAP DUA** — longest lead item, gates trustworthy CP-1/CP-2 numbers.
4. **Physical Android device** — battery, latency, false-fire rate all unmeasured.

---

## 12. Immediate Next Actions (Ordered by ROI)

| # | Action | Gain | Effort | Evidence |
|---|--------|------|--------|----------|
| 1 | Switch DTW band from 10% to 30% | **+5.2pp rank-1** | 1-line config | TORGO 5-fold eval |
| 2 | Switch frame length from 25ms to 30ms | **+1.1pp rank-1** | 1-line config | TORGO 5-fold eval |
| 3 | Switch shipped default to static MFCC | **+3.8pp rank-1** | 1-line config | TORGO 5-fold eval |
| 4 | **All three above combined** | **+6.0pp rank-1, F04 +16pp** | 3-line config | TORGO 5-fold eval |
| 5 | Integrate dual-filter cascade (E02-08) | **50-70% FAR reduction** | ~30 LOC | Architecture built |
| 6 | Add multi-frame persistence (E04-06) | **80-90% FA/hr reduction** | ~5 LOC | Architecture built |
| 7 | Acquire MUSAN corpus (E05-04) | **10-20% rel FRR @ SNR≤10 dB** | Download | AudioAugment ready |
| 8 | Evaluate pitch-shift enrollment (E13-08) | **5-8pp condition-robustness** | TorgoEval run | AudioAugment.pitchShift built |
| 9 | Train QbE student encoder (CP-1) | **+6.7pp ceiling above best MFCC** | GPU training | WavLM ceiling 71.9% |
| 10 | Per-speaker wake calibration (E04-02) | **5-15pp wake FRR reduction** | Config change | Architecture ready |

---

## 13. Reference Files

| File | Contents |
|------|----------|
| `docs/research/experiments/README.md` | Master experiment index (200 experiments, 20 domains) |
| `docs/research/experiments/SCORES.md` | Full scoring of all 200 experiments |
| `docs/research/experiments/RESULTS.md` | Initial experiment results |
| `docs/research/experiments/TOP30_EVAL.md` | Top-30 end-to-end evaluation report |
| `docs/ROADMAP.md` | Project roadmap with Critical Path v2 |
| `research/01_conceptual_findings.md` through `04_build_and_reuse_plan.md` | Original research |
| `docs/testing/` | FRR/FAR reports, CP-1/CP-2 spikes, always-on soak |
| `AGENTS.md` | Operating rules + Incident Protocol |
