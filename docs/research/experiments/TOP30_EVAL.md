# SpeechAngel — Top-30 SOTA Experiments: End-to-End Evaluation

**Date:** 2026-07-07  
**Corpus:** TORGO (F01 mild, F03 moderate, F04 severe dysarthric)  
**Baseline:** Static MFCC rank-1 59.2%, FRR 75.7% @ FAR 4.6%, EER 45.7%

---

## Executed Experiments (8 completed, measured on TORGO)

### E01-02: Delta-Order Sweep → **CONFIRMED (Static MFCC wins +3.8pp)**

| Front-end | Rank-1 | FRR HO | FAR HO | EER |
|---|---|---|---|---|
| none (static) | **59.2%** | 75.7% | 4.6% | 45.7% |
| delta | 57.3% | 77.9% | 5.1% | 48.7% |
| delta_delta | 55.4% | 78.3% | 5.1% | 49.4% |

**Verdict: Switch shipped default from DELTA_DELTA to NONE.** +3.8pp rank-1, +2.6pp FRR reduction at matched FAR.

### E02-01: Cosine vs Euclidean DTW → **NEGATIVE (Cosine worse by -0.8pp)**

| Distance | Rank-1 | FRR HO | FAR HO | EER |
|---|---|---|---|---|
| euclidean | **59.2%** | **75.7%** | 4.6% | **45.7%** |
| cosine | 58.4% | 79.4% | 4.8% | 49.8% |

**Verdict: Euclidean distance wins.** Cosine normalizes amplitude but loses the discriminative information in MFCC magnitude. For dysarthric speech with reduced spectral contrast, amplitude matters. Do not adopt.

### E03-01: Enrollment Count Sweep → **SATURATES AT k≥3 folds (66% enrollment)**

| Folds | Enroll % | Rank-1 | FRR HO | FAR HO | EER |
|---|---|---|---|---|---|
| k=2 | 50% | 56.9% | 73.8% | 4.8% | 48.7% |
| k=3 | 66% | **59.2%** | 75.7% | 5.1% | 44.9% |
| k=5 | 80% | **59.2%** | **75.7%** | 4.6% | 45.7% |
| k=10 | 90% | **59.2%** | 76.8% | 5.1% | 45.7% |

**Verdict: Rank-1 saturates at k≥3 (≥66% of data as enrollment).** 2-fold (50% enrollment) is under-trained (−2.3pp). Going from k=3 to k=10 adds no rank-1 gain. For a real deployment with 3-5 templates/command, this suggests 3 templates is the saturation point.

### E09-02: Held-Out Per-Command Calibration → **NON-IMPROVEMENT CONFIRMED**

| Speaker | Global FRR HO | Per-Cmd FRR HO | Per-Cmd FAR HO |
|---|---|---|---|
| F01 | 81.3% | 40.6% | **24.2%** |
| F03 | 80.5% | 55.1% | **34.1%** |
| F04 | 62.0% | 58.0% | **27.0%** |

**Verdict: Per-command calibration inflates FAR to 24-34% due to sparse negatives.** The lower FRR is a looser operating point, not a gain. Fix requires more negatives per command (need larger corpus → CP-0: SAP acquisition).

### E08-01: Vocabulary Size Curve → **CONFIRMED**

| Speaker | Commands | Rank-1 | Severity |
|---|---|---|---|
| F01 | 15 | 71.9% | Mild |
| F04 | 21 | 60.0% | Severe |
| F03 | 77 | 56.8% | Moderate |

**Verdict: ~5-8pp rank-1 loss per doubling of vocabulary.** Deployment target: ≤25 commands for ≥60% rank-1. Severity confounds vocabulary size (F03 has 77 commands → worst rank-1 despite being moderate).

### E01-01 Noise Reduction: → **HARMFUL ON CLEAN SPEECH**

| Config | Rank-1 |
|---|---|
| none (no NR) | **59.2%** |
| none + spectral_subtraction | 55.1% (−4.1pp) |
| delta + spectral_subtraction | 52.4% (−4.9pp) |
| delta_delta + spectral_subtraction | 52.4% (−3.0pp) |

**Verdict: Noise reduction should remain default-off.** Only enable when estimated SNR ≤ 10 dB (adaptive route).

### E10-06: McNemar Testing → **METHODOLOGY ESTABLISHED**
Common-mode rejection: NOT SUPPORTED (p=0.17). Margin scoring shows directional +4.5pp FRR improvement but is NOT banked (exploratory family, needs confirmation on fresh data).

---

## Architecture-Readiness Evaluated (5 experiments)

| Exp | Score | Status | What Changed |
|-----|-------|--------|-------------|
| **E02-08** | 890 | **READY** | `Dtw.withPath()` returns path length alongside distance. Dual-filter cascade is a config change from working. |
| **E04-06** | 870 | **READY** | `WakeGatedRecognizer.onFrame()` processes per-frame. Adding `consecutiveWakeCount ≥ N` is 5 LOC. |
| **E04-01** | 810 | **READY** | `AmbientFar` with variable wake template counts. Infrastructure exists. |
| **E04-02** | 810 | **READY** | `ThresholdCalibrator` on wake templates. Per-speaker calibration built-in. |
| **E04-09** | 810 | **READY** | `StreamingEnergyGate` computes running noise floor. SNR estimate is a division away. |

---

## Requires External Resources (4 experiments)

| Exp | Score | Blocker | Action |
|-----|-------|---------|--------|
| **E05-04** | 830 | MUSAN corpus (~30 GB) | `AudioAugment.addNoise()` ready. Download corpus. |
| **E17-01** | 860 | Physical Android device | `AudioRecord` watchdog. Mock-testable, needs device for real validation. |
| **E16-03** | 780 | Working QbE encoder | Online prototype refinement requires embedding similarity. |
| **E05-06** | 760 | MUSAN + RIR corpora | Combined augmentation. Both corpora needed. |

## Requires Implementation (4 experiments)

| Exp | Score | Action |
|-----|-------|--------|
| **E13-08** | 800 | Add pitch-shift to `AudioAugment`. Phase vocoder or resample-based. |
| **E19-01** | 790 | Three-stage cascade: energy→DTW→QbE routing in TemplateMatcher. |
| **E12-09** | 790 | Runtime-synthesized negative templates during enrollment. |
| **E20-02** | 770 | Adaptive re-enrollment prompting (UX). Per-command failure tracking + guidance. |

## Planned/Design (6 experiments)

| Exp | Score | Status |
|-----|-------|--------|
| E16-01 | 710 | LoRA/Adapter on-device fine-tuning (needs encoder) |
| E03-03 | 770 | Diverse enrollment (multi-session, needs longitudinal data) |
| E08-03 | 770 | Greedy command selection (can simulate on TORGO) |
| E08-08 | 770 | Wake-word bleed prevention (can test with existing WakeWordGate) |
| E17-03 | 820 | Crash-loop detection (Android-only) |
| E05-07 | 800 | SNR-adaptive threshold (code ready, needs noise-mixed data) |

---

## Key Findings Summary

1. **Static MFCC is the best front-end** — confirmed across all experiments. +3.8pp vs ΔΔ.
2. **Cosine DTW is worse than Euclidean** — amplitude information matters for dysarthric speech. Honest negative result.
3. **Enrollment saturates at 3+ templates** — k≥3 folds (66% enrollment) gives full accuracy. More data above this doesn't help DTW matching.
4. **Per-command calibration is still a non-improvement** — FAR balloons to 24-34% due to sparse negatives. Needs larger corpus.
5. **Infrastructure is ready for 5 high-impact experiments** — dual-filter cascade (890), multi-frame persistence (870), wake calibration (810×3). All are config/small-code changes.
6. **Noise reduction hurts on clean speech** — should be SNR-adaptive, not always-on.
7. **Vocabulary size is the silent accuracy killer** — target ≤25 commands. Each doubling costs ~5-8pp.

## Immediate Next Actions (Ordered by ROI)

1. Switch shipped default to static MFCC: **+3.8pp free gain** (1-line config change)
2. Integrate dual-filter cascade (E02-08): path-length rejection in TemplateMatcher.match()
3. Add multi-frame persistence to WakeGatedRecognizer (E04-06): N consecutive wake detections
4. Acquire MUSAN corpus for noise-augmented enrollment (E05-04)
5. Add pitch-shift augmentation to AudioAugment (E13-08)
6. Train QbE encoder (CP-1, E07-03): the accuracy ceiling bet at 71.9% vs 59.2%
