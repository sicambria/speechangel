# Experiment Scoring — SpeechAngel SOTA Pursuit

**Scoring criteria (0–1000):**
- **Impact (0–400):** Expected FRR/FAR improvement magnitude. 400 = game-changing (≥20pp rank-1), 300 = large (10-20pp), 200 = medium (5-10pp), 100 = small (1-5pp), 50 = marginal
- **Feasibility (0–300):** Ease of execution with existing infra. 300 = run today, 200 = minor code, 100 = major code, 50 = needs external asset
- **Constraint Fit (0–200):** Preserves language-independence + on-device + determinism. 200 = perfect fit, 150 = minor tension, 100 = significant tension, 50 = breaks constraint
- **Evidence Strength (0–100):** Literature/existing-results backing. 100 = published SOTA result, 70 = strong related work, 40 = plausible hypothesis, 10 = speculative

**Score interpretation:**
- 850-1000: Must do — highest expected ROI, ship-blocking
- 700-849: High priority — strong evidence + feasible
- 550-699: Medium priority — worth doing after above
- 400-549: Low priority — speculative or expensive
- <400: Do not pursue unless evidence strengthens

---

## Domain 01: Feature Extraction

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E01-01 | Multi-resolution MFCC sweep | 150 | 250 | 200 | 60 | **660** | planned |
| E01-02 | Delta-order sweep | 200 | 300 | 200 | 100 | **800** | **DONE** — static wins +3.8pp |
| E01-03 | PLP vs MFCC | 100 | 180 | 200 | 70 | **550** | planned |
| E01-04 | RASTA filtering | 120 | 150 | 200 | 60 | **530** | planned |
| E01-05 | CMVN normalization | 80 | 280 | 150 | 50 | **560** | planned |
| E01-06 | Multi-taper spectral est. | 100 | 150 | 200 | 40 | **490** | planned |
| E01-07 | Modulation-filtered features | 150 | 100 | 180 | 60 | **490** | planned |
| E01-08 | Sub-band MFCC | 180 | 150 | 200 | 60 | **590** | planned |
| E01-09 | Pitch-synchronous framing | 130 | 120 | 180 | 40 | **470** | planned |
| E01-10 | Learned filterbank (offline) | 250 | 100 | 180 | 80 | **610** | planned |

## Domain 02: Matching Algorithms

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E02-01 | Cosine distance DTW | 250 | 280 | 200 | 80 | **810** | high priority |
| E02-02 | Derivative DTW (D-DTW) | 180 | 260 | 200 | 70 | **710** | high priority |
| E02-03 | Subsequence DTW | 200 | 200 | 180 | 70 | **650** | medium |
| E02-04 | Weighted DTW (VAD weights) | 150 | 250 | 200 | 50 | **650** | medium |
| E02-05 | k-NN matching (k>1) | 180 | 280 | 200 | 70 | **730** | high |
| E02-06 | PCA+Mahalanobis DTW | 160 | 180 | 180 | 60 | **580** | medium |
| E02-07 | Soft-DTW | 140 | 180 | 200 | 70 | **590** | medium |
| E02-08 | Dual-filter cascade | 350 | 250 | 200 | 90 | **890** | **MUST DO** |
| E02-09 | Segmental DTW | 130 | 150 | 200 | 40 | **520** | low |
| E02-10 | Matcher fusion (DTW+cosine) | 280 | 220 | 180 | 80 | **760** | high |

## Domain 03: Template Enrollment

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E03-01 | Enrollment count sweep | 300 | 250 | 200 | 90 | **840** | **MUST DO** |
| E03-02 | Quality-filtered enrollment | 180 | 260 | 200 | 70 | **710** | high |
| E03-03 | Diverse enrollment (sessions) | 250 | 240 | 200 | 80 | **770** | high |
| E03-04 | DBA prototype enrollment | 220 | 180 | 200 | 80 | **680** | medium |
| E03-05 | Condition-aware selection | 200 | 200 | 200 | 60 | **660** | medium |
| E03-06 | Active enrollment | 150 | 120 | 200 | 50 | **520** | medium |
| E03-07 | Channel-robust enrollment | 250 | 200 | 200 | 70 | **720** | high |
| E03-08 | Template pruning | 100 | 280 | 200 | 60 | **640** | medium |
| E03-09 | Enrollment augmentation | 280 | 230 | 200 | 80 | **790** | high |
| E03-10 | Cross-user cohort transfer | 120 | 150 | 100 | 40 | **410** | low |

## Domain 04: Wake Word & FAR

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E04-01 | Wake template count sweep | 280 | 250 | 200 | 80 | **810** | high |
| E04-02 | Per-speaker wake calibration | 300 | 230 | 200 | 80 | **810** | high |
| E04-03 | Two-stage cascade tuning | 180 | 280 | 200 | 70 | **730** | medium |
| E04-04 | Dedicated rejection model | 320 | 160 | 180 | 80 | **740** | high |
| E04-05 | Onset-only wake matching | 180 | 260 | 200 | 50 | **690** | medium |
| E04-06 | Multi-frame persistence | 300 | 290 | 200 | 80 | **870** | **MUST DO** |
| E04-07 | Wake distinctness optimize | 160 | 220 | 200 | 50 | **630** | medium |
| E04-08 | Negative template enrollment | 250 | 250 | 200 | 60 | **760** | high |
| E04-09 | SNR-adaptive wake threshold | 280 | 260 | 200 | 70 | **810** | high |
| E04-10 | OpenWakeWord benchmark | 200 | 180 | 150 | 80 | **610** | medium |

## Domain 05: Noise Robustness

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E05-01 | Noise reduction param sweep | 180 | 230 | 200 | 60 | **670** | medium |
| E05-02 | Wiener filter vs specsub | 200 | 180 | 200 | 80 | **660** | medium |
| E05-03 | Log-MMSE noise reduction | 180 | 150 | 200 | 80 | **610** | medium |
| E05-04 | MUSAN noise augmentation | 320 | 220 | 200 | 90 | **830** | **MUST DO** |
| E05-05 | RIR far-field convolution | 250 | 200 | 200 | 80 | **730** | high |
| E05-06 | Combined RIR+MUSAN aug | 300 | 180 | 200 | 80 | **760** | high |
| E05-07 | SNR-adaptive threshold | 280 | 250 | 200 | 70 | **800** | high |
| E05-08 | Band-limited robustness | 180 | 250 | 200 | 70 | **700** | medium |
| E05-09 | Packet-loss robustness | 80 | 260 | 200 | 40 | **580** | low |
| E05-10 | Multi-mic beamforming | 150 | 100 | 180 | 60 | **490** | low |

## Domain 06: Dysarthric Specialization

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E06-01 | Per-severity analysis | 180 | 280 | 200 | 90 | **750** | **DONE** |
| E06-02 | Formant-aware features | 220 | 150 | 200 | 70 | **640** | medium |
| E06-03 | Jitter/shimmer/HNR | 180 | 170 | 200 | 70 | **620** | medium |
| E06-04 | Spectral moments | 160 | 200 | 200 | 60 | **620** | medium |
| E06-05 | Rate-adaptive DTW band | 200 | 250 | 200 | 60 | **710** | high |
| E06-06 | Dys-specific clustering | 220 | 160 | 200 | 50 | **630** | medium |
| E06-07 | Duration normalization | 250 | 140 | 180 | 70 | **640** | medium |
| E06-08 | Syllable-locked features | 240 | 130 | 200 | 60 | **630** | medium |
| E06-09 | Personalized z-scoring | 200 | 250 | 200 | 70 | **720** | high |
| E06-10 | Severity-adaptive pipeline | 280 | 100 | 180 | 60 | **620** | medium |

## Domain 07: Learned Encoders (QbE)

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E07-01 | Embedding dimension sweep | 180 | 250 | 200 | 80 | **710** | medium |
| E07-02 | WavLM layer selection | 200 | 250 | 200 | 80 | **730** | high |
| E07-03 | Student architecture bake-off | 350 | 120 | 150 | 90 | **710** | high |
| E07-04 | Multi-task training | 250 | 100 | 150 | 70 | **570** | medium |
| E07-05 | Knowledge distillation | 320 | 100 | 160 | 90 | **670** | high |
| E07-06 | Phoneme-supervised pretrain | 350 | 80 | 150 | 95 | **675** | high |
| E07-07 | Prototype selection strategies | 180 | 260 | 200 | 70 | **710** | medium |
| E07-08 | Embedding+DTW fusion | 300 | 200 | 180 | 80 | **760** | high |
| E07-09 | On-device latency benchmark | 100 | 220 | 200 | 70 | **590** | medium |
| E07-10 | Language-independence valid. | 100 | 150 | 200 | 60 | **510** | low |

## Domain 08: Vocabulary Optimization

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E08-01 | Vocab size vs accuracy | 250 | 280 | 200 | 90 | **820** | **PARTIAL** |
| E08-02 | Pre-enrollment FRR estimate | 280 | 150 | 200 | 60 | **690** | medium |
| E08-03 | Greedy command selection | 300 | 200 | 200 | 70 | **770** | high |
| E08-04 | Command duration optimize | 200 | 260 | 200 | 70 | **730** | medium |
| E08-05 | Syllable count vs acc. | 180 | 250 | 200 | 70 | **700** | medium |
| E08-06 | Vowel diversity metric | 200 | 180 | 200 | 50 | **630** | medium |
| E08-07 | Consonant place diversity | 180 | 160 | 200 | 40 | **580** | low |
| E08-08 | Wake-word bleed prevention | 250 | 260 | 200 | 60 | **770** | high |
| E08-09 | Minimal-pair precision | 150 | 280 | 200 | 50 | **680** | medium |
| E08-10 | Vocab recommendation engine | 250 | 120 | 200 | 50 | **620** | medium |

## Domain 09: Operating Point Optimization

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E09-01 | Global threshold sweep | 250 | 300 | 200 | 90 | **840** | **DONE** |
| E09-02 | Held-out per-cmd calib. | 300 | 250 | 200 | 90 | **840** | **MUST DO** |
| E09-03 | Budget allocation strategies | 250 | 240 | 200 | 70 | **760** | high |
| E09-04 | Confidence calibration | 200 | 250 | 200 | 80 | **730** | high |
| E09-05 | Cost-ratio operating point | 180 | 280 | 200 | 60 | **720** | medium |
| E09-06 | Multi-template threshold scaling | 220 | 250 | 200 | 60 | **730** | medium |
| E09-07 | Temporal threshold adapt. | 200 | 200 | 150 | 40 | **590** | medium |
| E09-08 | Hysteresis threshold | 200 | 260 | 200 | 70 | **730** | medium |
| E09-09 | Population prior init. | 180 | 220 | 200 | 60 | **660** | medium |
| E09-10 | Per-command failure diag. | 180 | 260 | 200 | 60 | **700** | **PARTIAL** |

## Domain 10: Evaluation Methodology

| # | Experiment | Impact | Feasibility | Constraints | Evidence | **Total** | Status |
|---|-----------|--------|-------------|-------------|----------|-----------|--------|
| E10-01 | DET curve standard | 180 | 280 | 200 | 90 | **750** | planned |
| E10-02 | Cross-corpus validation | 300 | 80 | 200 | 80 | **660** | blocked |
| E10-03 | Bootstrap CI reporting | 200 | 270 | 200 | 90 | **760** | planned |
| E10-04 | Stratified eval reporting | 250 | 260 | 200 | 90 | **800** | planned |
| E10-05 | Statistical power analysis | 200 | 240 | 200 | 80 | **720** | planned |
| E10-06 | McNemar standard | 250 | 290 | 200 | 90 | **830** | **DONE** |
| E10-07 | Open-set eval (OOV) | 280 | 200 | 200 | 80 | **760** | planned |
| E10-08 | Sim-vs-real fidelity | 250 | 150 | 200 | 70 | **670** | planned |
| E10-09 | Longitudinal eval | 220 | 160 | 200 | 70 | **650** | planned |
| E10-10 | SOTA leaderboard | 180 | 180 | 200 | 80 | **640** | planned |

---

## Score Distribution Summary

| Tier | Score Range | Count | Description |
|------|-------------|-------|-------------|
| **S** (Must do) | 810-1000 | **12** | Ship-blocking, highest ROI |
| **A** (High) | 700-809 | **28** | Strong evidence + feasible |
| **B** (Medium) | 550-699 | **40** | Worth doing after A-tier |
| **C** (Low) | 400-549 | **16** | Speculative or expensive |
| **D** (Skip) | <400 | **4** | Do not pursue now |

## S-Tier (Must Do — 12 experiments)

| Exp | Score | Description |
|-----|-------|-------------|
| **E02-08** | 890 | Dual-filter cascade (LRDWWS technique) |
| **E04-06** | 870 | Multi-frame persistence for wake |
| **E03-01** | 840 | Enrollment count sweep |
| **E09-01** | 840 | Global threshold sweep (DONE) |
| **E09-02** | 840 | Held-out per-command calibration |
| **E04-01** | 810 | Wake template count sweep |
| **E04-02** | 810 | Per-speaker wake calibration |
| **E04-09** | 810 | SNR-adaptive wake threshold |
| **E02-01** | 810 | Cosine distance DTW |
| **E05-04** | 830 | MUSAN noise augmentation |
| **E08-01** | 820 | Vocab size vs accuracy (PARTIAL) |
| **E10-06** | 830 | McNemar standard (DONE) |

## A-Tier (High Priority — 28 experiments)

07-QbE encoder, 05-noise robust, 04-wake/FA, 02-matcher, 03-enrollment domains dominate.
Highest-leverage clusters: **(a)** learned encoders, **(b)** noise robustness through augmentation, **(c)** multi-template enrollment, **(d)** matcher innovations.
