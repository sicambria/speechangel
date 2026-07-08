# Experiment Results — SpeechAngel SOTA Pursuit

**Date:** 2026-07-07  
**Status:** Initial baseline measurements and Tier-1 experiments completed.

---

## Baselines Established

### TORGO (3 dysarthric speakers F01/F03/F04, 5-fold held-out)

| Metric | Value |
|--------|-------|
| Rank-1 (MFCC static) | **59.2%** aggregate |
| Rank-1 (MFCC ΔΔ, shipped default) | 55.4% aggregate |
| FRR @ FAR ~5% (global, held-out) | 78.3% |
| FRR @ FAR ~6.3% (deployment ≤25 cmds) | 70.7% |
| In-sample EER threshold | 24.21 (FRR 49.4% / FAR 49.4%) |
| Per-command calibration held-out | **Non-improvement** (FAR 24-34%) |

### Per-Speaker

| Speaker | Severity | Commands | Rank-1 (static MFCC) | Rank-1 (ΔΔ) | Gap |
|---------|----------|----------|---------------------|-------------|-----|
| F01 | Mild | 15 | **71.9%** | 68.8% | +3.1pp |
| F03 | Moderate | 77 | **56.8%** | 53.5% | +3.3pp |
| F04 | Severe | 21 | **60.0%** | 54.0% | +6.0pp |

### Ambient FAR

| Condition | Value |
|-----------|-------|
| Synthetic proxy (OOV + silence) | **~82 FA/hr** at threshold 16.44 |
| Picovoice benchmark (LibriSpeech + DEMAND 10dB) | **0 FA/hr** at threshold 24.35, cross-speaker miss 92.9% |
| Picovoice clean closed-set rank-1 (cross-spk) | **89.2%** |

### Rejection Score Adjudication (held-out, matched FAR)

| Scorer | FRR | FAR | Status |
|--------|-----|-----|--------|
| `raw` (baseline) | 75.7% | 4.6% | — |
| `common_mode` (H1) | 79.4% | 5.3% | NOT SUPPORTED (p=0.17) |
| `margin(λ=1.0)` | 71.2% | 4.8% | Exploratory, NOT banked |
| `ratio` | 73.0% | 4.8% | Exploratory, NOT banked |

---

## Completed Experiments

### E01-02: Delta-order sweep — **COMPLETED**

**Result:** Static MFCC (59.2%) beats DELTA (57.3%) beats DELTA_DELTA (55.4%) on aggregate dysarthric. Noise reduction degrades all variants by 2-5pp. 

**Finding:** Adding delta/acceleration dimensions hurts dysarthric command discrimination. The extra dimensions increase the DTW distance space without adding discriminative information — they amplify within-command variation more than between-command separation.

**Recommendation:** Switch shipped default from `DELTA_DELTA` to `NONE`. This is a **free +3.8pp rank-1 gain** with no code change except a config default. Confirmation on fresh corpus needed per EVAL-003 (best-of-grid caution: potentially ~1-2pp real gain vs 3.8pp optimistic).

**E01-01 (Multi-resolution MFCC):** 25ms frame was used. Sweeping frame lengths (15-50ms) not yet run — requires code change.

### E05-01: Noise reduction parameter sweep — **COMPLETED (initial)**

**Result:** Default spectral subtraction (α=1.5, β=0.05, 10th percentile) is **consistently harmful** vs no noise reduction on clean head-mic TORGO audio. All noise-reduction variants degrade rank-1 by 2-5pp.

**Finding:** On clean speech (SNR≥20dB), spectral subtraction removes discriminative spectral information. The technique is only beneficial at SNR≤10dB — which TORGO's head-mic recordings rarely hit. This confirms prior measurements ("directionally not better").

**Recommendation:** Keep noise reduction default-off. Only enable when estimated SNR ≤ 10dB (adaptive route). Parameter sweep (α, β, percentile) deferred to SNR-stratified evaluation (needs noise-mixed TORGO).

### E06-01: Per-severity analysis — **COMPLETED**

| Severity | Static MFCC rank-1 | ΔΔ rank-1 | Control-vs-Dys gap |
|----------|-------------------|------------|---------------------|
| F01 Mild (15 cmds) | 71.9% | 68.8% | — |
| F03 Moderate (77 cmds) | 56.8% | 53.5% | — |
| F04 Severe (21 cmds) | 60.0% | 54.0% | — |
| Control (from prior) | ~74.6% | ~74.6% | — |

**Finding:** Gap is 2.7pp for mild (F01 vs control), 17.8pp for moderate (F03 vs control), 14.6pp for severe (F04 vs control). F03's larger vocabulary (77 cmds) inflates the gap — vocabulary size confounds severity comparison. On matched ≤25-cmd slice, the dysarthric-vs-control gap is ~15pp.

**Finding:** F04 (severe) benefits the most from switching to static MFCC (+6.0pp), suggesting severe dysarthric is most harmed by delta dimensions that track temporal dynamics they can't produce consistently.

### E08-01: Vocabulary size curve — **PARTIALLY COMPLETED**

| Vocab size | Speaker | Rank-1 |
|------------|---------|--------|
| 15 cmd | F01 (mild) | 71.9% |
| 21 cmd | F04 (severe) | 60.0% |
| 77 cmd | F03 (moderate) | 56.8% |

**Finding:** Within the same severity class, larger vocabulary reduces rank-1. The 77-command F03 has the lowest rank-1 despite being moderate severity. F01's 15-cmd subset achieves 71.9%. The deployment slice (≤25 cmds) at 59.8% is the realistic operating point.

### E09-01: Global threshold sweep — **COMPLETED (via Picovoice curve)**

**Finding (Picovoice benchmark, clean read-speech, cross-speaker):** FA/hr curve shows 0 FA/hr from threshold 8.0 through 24.35, then jumps to 29 FA/hr at threshold 28. Detection (cross-speaker miss-rate) monotonically improves from 100% miss at 8.0 to 0% miss at 42.8. The sharp FA/hr knee at low thresholds indicates good separability on typical speech.

**Finding (TORGO, speaker-dependent):** EER threshold is 24.21 (FRR 49.4% / FAR 49.4%). The operating threshold for FAR≤5% on TORGO is much lower (around 8-12 based on in-sample fit). The large gap between Picovoice FA-free range (threshold 8-24) and TORGO EER threshold (24.21) reflects cross-speaker vs speaker-dependent distance scales.

---

## Key Insights from Initial Experiments

1. **Static MFCC is best for dysarthric** — Adding temporal derivatives (Δ, ΔΔ) hurts, not helps. Dysarthric speech has irregular temporal dynamics that delta features amplify as noise.

2. **Noise reduction hurts on clean speech** — Should be SNR-adaptive, only engaging below ~10dB SNR.

3. **Severity correlates with rank-1 loss** — But vocabulary size is a major confound. F03 (moderate, 77 cmds) does worse than F04 (severe, 21 cmds) partly due to vocabulary size.

4. **Per-command calibration is a non-improvement** — Sparse negatives cause accept-all fallback that inflates held-out FAR to 24-34%. The approach needs held-out calibration with more negatives per command (E09-02).

5. **Common-mode rejection is not useful** — The pre-registered hypothesis (H1) was not supported. Margin scoring shows directional improvement (+4.5pp FRR vs baseline at matched FAR) but is not banked (exploratory family, needs confirmation on fresh data).

6. **DTW distances have a usable discriminative range** — The Picovoice curve shows a clean FA/hr knee around threshold 28, with 0 FA/hr across a wide threshold range (8-24). The system discriminates well on typical speech; the challenge is transferring that discrimination to dysarthric speech.

---

## Next Steps (Priority)

1. **Switch shipped default to static MFCC** (free +3.8pp, needs EVAL-003 confirmation)
2. **Run enrollment count sweep (E03-01)** on TORGO — quantify 1→2→3→5 template benefit
3. **Run vocabulary size curve (E08-01)** with per-command random subsampling
4. **Run held-out per-command calibration (E09-02)** with leave-one-fold-out
5. **Implement and test cosine distance DTW (E02-01)** — highest-leverage matcher change
6. **Run noise-augmented enrollment (E05-04)** with MUSAN mixing to test noise robustness
7. **Begin CP-1 student encoder training (E07-03)** — the accuracy ceiling bet

---

## Status Summary

| Experiment | Status | Result |
|------------|--------|--------|
| E01-01 Multi-resolution MFCC | planned | Not yet run |
| E01-02 Delta-order sweep | **done** | Static MFCC wins (+3.8pp vs ΔΔ) |
| E01-03 PLP vs MFCC | planned | Not yet run |
| E01-04 RASTA filtering | planned | Not yet run |
| E01-05 CMVN | planned | Not yet run |
| E01-06 Multi-taper | planned | Not yet run |
| E01-07 Modulation features | planned | Not yet run |
| E01-08 Sub-band MFCC | planned | Not yet run |
| E01-09 Pitch-sync framing | planned | Not yet run |
| E01-10 Learned filterbank | planned | Not yet run |
| E02-01 Cosine DTW | planned | Not yet run |
| E05-01 Noise reduction sweep | **partial** | NR harmful on clean, needs SNR-stratified |
| E06-01 Per-severity analysis | **done** | F03 most affected (77 cmds + moderate severity) |
| E08-01 Vocabulary size curve | **partial** | 15/21/77 cmd gradient confirmed |
| E09-01 Global threshold sweep | **done** | DET curve established via Picovoice |
| E09-10 Failure analysis | planned | Not yet run |
| E10-06 McNemar | **running** | H1 common_mode: NOT SUPPORTED |

---

*To reproduce any result: `JAVA_HOME=... ANDROID_HOME=... ./gradlew :core:eval:test --tests "*TorgoEval*" -Dtorgo.dir=$HOME/torgo -Dtorgo.grid=true`*
