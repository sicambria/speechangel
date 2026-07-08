# SpeechAngel SOTA Experiment Suite

> **200 experiments across 20 domains to close the gap from pre-alpha (442/1000) to SOTA.**

**Goal:** FRR <5% @ FAR ≤0.5 FA/hr on real dysarthric audio, language-independent, 1-shot enrolled, always-on.

**Current baseline:** Static MFCC rank-1 59.2% dysarthric. FRR 78.3% @ FAR ~5%. ~82 FA/hr ambient.

**Constraint-matched SOTA reference:** ZP-KWS ~29-33% FRR@1%FAR. Target: beat 33% FRR, approach 5%.

**Latest finding:** Static MFCC beats ΔΔ by +3.8pp (59.2% vs 55.4%), noise reduction hurts on clean speech.

---

## Domain Index — Domains 01-10: Core Pipeline (100 experiments)

| # | Domain | File | Current State | Top Experiment |
|---|--------|------|--------------|----------------|
| 01 | Feature Extraction | `docs/research/experiments/01_frontend.md` | Static MFCC 59.2% r1 | E01-02: Delta sweep **DONE** (+3.8pp) |
| 02 | Matching Algorithms | `docs/research/experiments/02_matcher.md` | DTW Euclidean 10% band | E02-08: Dual-filter **890 (S)** |
| 03 | Template Enrollment | `docs/research/experiments/03_enrollment.md` | 1 template/command | E03-01: Count sweep **840 (S)** |
| 04 | Wake Word & FAR | `docs/research/experiments/04_wake_far.md` | ~82 FA/hr ambient | E04-06: Multi-frame persist **870 (S)** |
| 05 | Noise Robustness | `docs/research/experiments/05_noise.md` | SpecSub harm on clean | E05-04: MUSAN aug **830 (S)** |
| 06 | Dysarthric Specialization | `docs/research/experiments/06_dysarthric.md` | 59.2% r1 (static MFCC) | E06-01: Severity analysis **DONE** |
| 07 | Learned Encoders (QbE) | `docs/research/experiments/07_qbe.md` | NoopQbeEncoder | E07-03: Student bake-off **710 (A)** |
| 08 | Vocabulary Optimization | `docs/research/experiments/08_vocabulary.md` | Distinctness advisory | E08-01: Vocab size curve **820 (S)** |
| 09 | Operating Point | `docs/research/experiments/09_oppoint.md` | Global thresh 8.0 | E09-02: Held-out calib **840 (S)** |
| 10 | Evaluation Methodology | `docs/research/experiments/10_eval.md` | TORGO eval built | E10-06: McNemar **DONE** |

## Domain Index — Domains 11-20: SOTA Breakthrough Directions (100 experiments)

| # | Domain | File | Focus | Top Experiment |
|---|--------|------|-------|----------------|
| 11 | QbE Deployment | `docs/research/experiments/11_qbe_deployment.md` | ONNX, TFLite, INT8, MSWC pretrain | E11-01: sherpa-onnx **770 (A)** |
| 12 | Matcher Innovation | `docs/research/experiments/12_matcher_innovation.md` | Learned cost, HNSW, proto nets | E12-05: OOV proto nets **700 (A)** |
| 13 | Data Augmentation | `docs/research/experiments/13_augmentation.md` | TTS-dysarthric, SpecAug, babble | E13-08: Pitch aug **800 (A)** |
| 14 | On-Device Optimization | `docs/research/experiments/14_ondeploy.md` | Latency, battery, crash recovery | E17-01: Watchdog **860 (S)** |
| 15 | Multi-Task Learning | `docs/research/experiments/15_multitask.md` | Joint speaker/VAD/SNR/severity | E16-01: Adapter **710 (A)** |
| 16 | Personalization | `docs/research/experiments/16_personalization.md` | MAML, LoRA, online proto | E16-03: Online refine **780 (A)** |
| 17 | Production Engineering | `docs/research/experiments/17_production.md` | Watchdog, crash-loop, BT | E17-01: Audio watchdog **860 (S)** |
| 18 | Transfer & Foundation | `docs/research/experiments/18_transfer_learning.md` | Whisper, XLS-R, MSWC, d2v2 | E18-08: MSWC pretrain **680 (B)** |
| 19 | Ensemble & Cascade | `docs/research/experiments/19_ensemble.md` | 3-stage, voting, conformal | E19-01: 3-stage cascade **790 (A)** |
| 20 | Human-in-the-Loop UX | `docs/research/experiments/20_ux_hitl.md` | Disambiguation, calibration | E20-02: Adaptive re-enroll **770 (A)** |

---

## Score Distribution (all 200 experiments)

| Tier | Score | Count | % |
|------|-------|-------|---|
| **S** (Must do) | 810-1000 | **15** | 7.5% |
| **A** (High priority) | 700-809 | **62** | 31% |
| **B** (Medium) | 550-699 | **96** | 48% |
| **C** (Low) | 400-549 | **23** | 11.5% |
| **D** (Skip) | <400 | **4** | 2% |

## S-Tier: Ship-Blocking Experiments (15)

| Exp | Score | Domain | Description |
|-----|-------|--------|-------------|
| E02-08 | 890 | Matching | Dual-filter cascade (LRDWWS technique) |
| E04-06 | 870 | Wake/FAR | Multi-frame persistence for wake |
| E17-01 | 860 | Production | Audio pipeline watchdog + auto-restart |
| E03-01 | 840 | Enrollment | Enrollment count sweep (1→2→3→5→10) |
| E09-01 | 840 | Operating Point | Global threshold sweep **(DONE)** |
| E09-02 | 840 | Operating Point | Held-out per-command calibration |
| E05-04 | 830 | Noise | MUSAN noise augmentation for enrollment |
| E10-06 | 830 | Evaluation | McNemar paired testing standard **(DONE)** |
| E08-01 | 820 | Vocabulary | Vocab size vs accuracy curve |
| E17-03 | 820 | Production | Crash-loop detection with exponential backoff |
| E04-01 | 810 | Wake/FAR | Wake template count sweep |
| E04-02 | 810 | Wake/FAR | Per-speaker wake calibration |
| E04-09 | 810 | Wake/FAR | SNR-adaptive wake threshold |
| E02-01 | 810 | Matching | Cosine distance DTW |
| E01-02 | 800 | Frontend | Delta-order sweep **(DONE: static MFCC wins)** |

---

## Key Supporting Files

- `docs/research/experiments/SCORES.md` — Full scoring of all 200 experiments with criteria breakdown
- `docs/research/experiments/RESULTS.md` — Compilation of executed experiment results
- `docs/research/OVERALL.md` — Complete research synthesis

## Quick Links

- Reproduce TORGO baseline: `make bench-picovoice` or `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo`
- Run front-end grid: `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.grid=true`
- Guardrails check: `make guardrails` or `node scripts/audits/run-all.mjs`
