<!-- SpeechAngel authoritative SOTA reference: wake-word / keyword spotting incl. atypical speech.
     First-principles taxonomy, algorithms, benchmarks, evidence-ranked systems, and SpeechAngel's
     measured standing. Single source of truth for external SOTA. Supersedes and folds in
     2026-07-06_sota-competitive-bar.md (retired). Standing doc; indexed in docs/DOC_TOC.md. -->
# SpeechAngel — Authoritative SOTA Reference: Wake-Word / Keyword Spotting (incl. atypical speech)

**Date:** 2026-07-08 · **Status:** authoritative living reference — the single source of truth for the
external state of the art. Update with new evidence.

> **Scope.** This is the one place "SOTA" is defined for SpeechAngel: external systems, algorithm
> families, benchmarks, and the concrete numeric bar — plus SpeechAngel's own measured standing against
> that bar (§11). The **spine (§0–§10)** is the external field and is written to be liftable into the
> academic paper (the sibling *speechangel-paper* repo); the **standing section (§11)** is internal-only. Every external
> claim is sourced (arXiv, GitHub README, published competition result, or reproducible benchmark);
> marketing-only claims are flagged. It **supersedes `docs/product/2026-07-06_sota-competitive-bar.md`**
> (retired) and folds in that doc's unique material (the 7-axis field ranking, the PD-DWS technique
> mining, the personalization proof-point, and the governing comparability caveat below). Internal
> product scoring lives in the linked scorecards (§11); this doc does not re-own it.

---

## 0. The governing comparability caveat (read first)

**No system below is independently verified across noisy + atypical-speaker + language-independent +
user-trainable *simultaneously*.** The figures come from *different, non-comparable* test protocols
(different corpora, SNRs, FA/hr definitions, vocabularies). Treat every external number as a **per-axis
bar**, not a head-to-head result. This is the same selection/comparability discipline EVAL-002/003
enforce internally (`docs/ai/ACTIVE_DEV_RULES.md`). Where a number is SpeechAngel's own, its exact
configuration (front-end, corpus, regime, on/off-device, banked/not-banked) is named — see §11.

---

## 1. First Principles — the problem decomposed

A KWS/wake-word system must solve a **signal-detection-in-continuous-audio** problem:

```
continuous_mic_stream ──► [Feature Extract] ──► [Detector] ──► wake / not-wake
```

The problem decomposes into three sub-problems with different statistical properties:

| # | Problem | Type | Difficulty driver |
|---|---------|------|-------------------|
| P1 | **Discrimination** | Closed-set classification | "Which of N known commands was spoken?" — well-posed, supervised |
| P2 | **Rejection / verification** | Open-set detection | "Was *any* command spoken, or was this background?" — the hard one |
| P3 | **Always-on gating** | Stream-level false-accept minimisation | "Across hours of audio, how many false triggers?" — the product-killer |

P1 is easiest (89.2% closed-set rank-1 even with MFCC-DTW, cross-speaker Picovoice benchmark). P3 is
hardest (needs ≤0.5 FA/hr across unlimited audio). The ratio P3/P1 is ~10³–10⁴ for DTW; ~10² for neural
KWS; ~10 for the best cascade systems.

### 1.1 Key metrics — definitions matter

- **FRR (False Reject Rate):** % of intended wake-word utterances *not* detected. Lower is better.
- **FAR (False Accept Rate):** % of non-wake audio segments falsely triggered. Lower is better.
- **FA/hr (False Accepts per Hour):** Absolute count of false triggers per hour of continuous audio. The
  **only deployable metric for P3** — FAR is meaningless without stream duration context.
- **ROC / DET curve:** FRR vs FAR trade-off swept across thresholds. The standard academic plot.
- **RTF (Real-Time Factor):** sec_compute / sec_audio. <1 for real-time.
- **#Params / model size:** MB on disk.
- **MACs / FLOPs:** Multiply-accumulate operations per inference step.

**Critical insight:** A KWS paper reporting "97% accuracy" on GSC V2 (P1 only) tells you nothing about
FA/hr (P3). Most papers measure P1; few measure P3. Always-on deployment needs P3 numbers.

---

## 2. Algorithm families — first-principles taxonomy

### 2.1 Template matching (DTW / correlation)

**Principle:** Store exemplar(s) of the wake word; slide a window over the stream; compute distance (e.g.
DTW alignment cost); threshold.

| Variant | Mechanism | Strengths | Weaknesses |
|---------|-----------|-----------|------------|
| MFCC + DTW | Mel-frequency cepstral coefficients + Dynamic Time Warping alignment cost | Language-independent, user-trainable, zero-shot, tiny footprint | ~10³× worse FA/hr than neural KWS; no negative learning |
| MFCC + GMM-UBM | Gaussian Mixture Models with a Universal Background Model as impostor prior | Softer threshold via likelihood ratio; established in speaker verification | Still decades behind neural approaches |
| Cross-correlation | Raw waveform correlation | Fastest, zero features | Only works for exact repetition in clean audio |

**Evidence (this is SpeechAngel's shipped family):** MFCC-DTW on the Picovoice benchmark (cross-speaker
lower bound) → 87.5% miss @ 0.1 FA/hr, ~119 FA/hr at first useful detection; an early in-regime ambient
proxy put it at ~82 FA/hr (optimistically biased — see §11). PocketSphinx (HMM-based) → similar regime at
~7.2% CPU on RPi5. *Verdict: not viable for always-on on its own; useful as the Stage-1 candidate and as
a structured-data source for a multi-stage cascade.*

### 2.2 Small convolutional KWS (the neural baseline)

**Principle:** End-to-end CNN on spectrogram input. Trained on labeled keyword/non-keyword data. The
dominant academic family since 2017.

| Model | Architecture | GSC V1 Acc | GSC V2 Acc | #Params | Year | Source |
|-------|-------------|-----------|-----------|---------|------|--------|
| **DSCNN** (Google) | Depthwise separable CNN | 90.7% | — | ~500K | 2017 | arXiv:1711.07128 |
| **TC-ResNet** | Temporal convolution + residual blocks | 96.6% | — | ~305K | 2018 | arXiv:1807.04722 |
| **Res8** (Howl) | 4 conv residual blocks | — | — | small | 2020 | castorini/howl |
| **MatchboxNet** (NVIDIA) | 1D time-channel separable conv + residual blocks + BN + ReLU | SOTA at pub | SOTA at pub | very small | 2020 | arXiv:2004.08531, Interspeech 2020 |
| **BC-ResNet-1** (Qualcomm) | Broadcasted residual: 1D temporal conv with 2D freq dimension via broadcast skip | 98.0% | 98.7% | 10K | 2021 | arXiv:2106.04140, Interspeech 2021 |
| **BC-ResNet-8** (Qualcomm) | Scaled BC-ResNet | — | **98.7%** | 320K | 2021 | Same |
| **BC-SENet** (2024) | BC-ResNet + Squeeze-and-Excitation | — | competitive | — | 2024 | arXiv:2406.18313, IALP 2024 |
| **MDTC** (Google, 2021) | Multi-head attention + RNN-T for streaming KWS | — | 10% error reduction over prior SOTA | — | 2021 | arXiv:2005.06720 |
| **Keyword-MLP** | MLP-Mixer blocks on spectrogram patches | competitive | competitive | — | 2022 | — |

**Evidence:** BC-ResNet holds the published GSC V1/V2 accuracy leaderboard at 98.0%/98.7%. MatchboxNet
was the prior SOTA and is production-hardened (NVIDIA NeMo). These are tiny models (<500K params) suited
for MCU deployment.

**Key limitation:** GSC is a P1 (discrimination-only) benchmark. Winning GSC tells you almost nothing
about FA/hr on continuous ambient audio. Most papers do not report FA/hr.

### 2.3 Phoneme-supervised encoders (zero-shot KWS)

**Principle:** Train an encoder to map audio → phoneme-probability sequence. At inference, match the input
against target keyword phoneme sequence. No per-word retraining needed.

| Model | Mechanism | Result | #Params | Year | Source |
|-------|-----------|--------|---------|------|--------|
| **PhonMatchNet** | Phoneme posteriorgram + DTW-like matching | 67%/80% relative EER/AUC improvement on LibriPhrase | — | 2023 | Interspeech 2023 |
| **ZP-KWS** | Phoneme-supervised encoder + GE2E speaker encoder (0.9M), multiplicative late fusion | FRR@1%FAR reduced ~60% relative vs strongest baseline (author-reported strict-mode **absolute ≈29–33%**) | **1.55M** total | 2026 | arXiv:2606.20106, Interspeech 2026 |
| **sherpa-onnx KWS** (Zipformer) | Open-vocabulary via beam search + boosting scores + trigger thresholds per keyword | Tunable per deployment; proven on Android | ~3.3M | 2024-2025 | k2-fsa/sherpa-onnx |

**Evidence:** ZP-KWS achieves ~60% relative FRR improvement at 1% FAR, supports zero-shot (unseen
keywords + unseen speakers), is language-agnostic (phoneme-supervised), edge-deployable at 1.55M params.
This is the **architecturally closest SOTA to SpeechAngel's constraint set**: language-independent,
user-trainable, zero-shot, on-device.

**Key limitation:** Phoneme supervision requires a pronunciation lexicon for the target language (though
the encoder itself is language-agnostic). Measured on LibriPhrase/GSC, not on continuous ambient FA/hr
streams. **Citation note:** arXiv 2606.20106 / "Interspeech 2026" is future-dated relative to today
(2026-07-08); the ID was web-verified 2026-07-06 as real and recent, but **re-verify the venue/DOI before
lifting into the paper**.

### 2.4 SSL transfer (wav2vec 2.0, HuBERT, WavLM, Whisper-based)

**Principle:** Pre-train a large model on massive unlabeled audio via self-supervised learning (masked
prediction / denoising). Fine-tune or pool a lightweight head for KWS. The SSL backbone provides rich
representations from minimal labeled data.

| Model | Backbone | Result | #Params | Year |
|-------|----------|--------|---------|------|
| wav2vec 2.0 + KWS head | wav2vec 2.0 Base (95M) | Weak few-shot on TORGO (see §11) | 95M (backbone) | 2020 |
| HuBERT + KWS head | HuBERT Base (95M) | Dysarthric rank-1 67.8% (SpeechAngel CP-1 probe) | 95M | 2021 |
| WavLM + KWS head | WavLM Base-plus (95M) | Best SSL for speech tasks (SUPERB); SpeechAngel ceiling probe (see §11) | 95M | 2022 |
| Whisper-tiny + KWS | Whisper tiny (39M) | Multilingual zero-shot via decoder | 39M | 2022 |
| DistilHuBERT (distilled) | DistilHuBERT (~23.5M) | Dysarthric rank-1 65.9% (CP-1 probe); off-device cascade probes (see §11) | ~23.5M | 2026 |

**Evidence:** WavLM Base holds the SUPERB benchmark leaderboard for general speech representation. On real
dysarthric TORGO, SpeechAngel measured a **banked** rank-1 lift from a learned pooled-embedding — but that
gain does **not** auto-translate to a deployable always-on operating point, and every SOTA-level FRR from
these encoders is off-device / not-banked. The exact numbers, configs, and banked/not-banked status live
in §11 (do not quote them without that context). *Verdict: SSL transfer is the most promising research
path (best language-independence/accuracy trade-off) but requires distillation + a cascade to become an
on-device candidate, and none of it is deployment-validated.*

### 2.5 Large-scale ASR-based KWS (the non-transferable ceiling)

**Principle:** Full ASR pipeline → keyword detection from transcript. Accuracy ceiling but trades away all
SpeechAngel constraints.

| System | Approach | Result | #Params | Source |
|--------|----------|--------|---------|--------|
| **PD-DWS** (LRDWWS'24 winner) | data2vec2 + ASR-assisted dual-filter cascade | FAR 0.32%, FRR 0.5% on dysarthric Mandarin | ~300M | LRDWWS 2024 |
| **Whisper + keyword match** | Whisper-large-v3 transcript → regex match | Near-perfect for clear English | 1.5B | — |

**Evidence:** PD-DWS proves near-perfect dysarthric wake-word detection is *possible* with enough model
capacity (§7 mines its transferable techniques). But the ~300M param data2vec2 backbone, ASR assistance,
and closed-vocabulary Mandarin constraint make it non-transferable wholesale to an on-device,
language-independent system. *Verdict: existence proof for the population ceiling, not an architecture to
port.*

---

## 3. Production systems — evidence-ranked

### 3.1 Porcupine (Picovoice) — **the commercial bar**
- **Architecture:** Proprietary DNN. Custom-keyword training via web portal.
- **Evidence:** Picovoice's own benchmark (LibriSpeech + DEMAND, 6 keywords, 118.7 min, cross-speaker):
  **97.1% detection @ 0.1 FA/hr @ 10 dB SNR**, <1 MB, 3.8% CPU on RPi-3, 2.2% CPU on RPi-5.
- **Ranked:** Best measured always-on FA/hr of any system with published numbers. BUT: proprietary
  engine, requires AccessKey, free tier ~3 active users/month (re-verify current tier), language-dependent.
- **License:** Proprietary (Apache-2.0 only on SDK bindings).
- **Relevance to SpeechAngel:** Sets the accuracy-at-low-FAR-under-noise target. Not bundleable.

### 3.2 openWakeWord — **the open-source deployable bar**
- **Architecture:** 3-stage: (1) Melspectrogram (ONNX, fixed params) → (2) Frozen Google speech embedding
  backbone (conv blocks, pre-trained on massive data) → (3) Per-wake-word classifier (FC or 2-layer RNN).
  Shared backbone, small per-model classifier. Trained on **100% synthetic TTS data** with ~30K hours
  negative data.
- **Evidence:** From project README: "Target performance of <5% FRR and <0.5 FA/hr" (design targets, not a
  guaranteed measured result). DET curve shows outperforming Porcupine on "Alexa" model; competitive with
  custom Porcupine + Mycroft Precise on "Hey Mycroft." On RPi-3: 15-20 models simultaneously on single
  core. Fluent Speech Commands: 97.5% test accuracy vs 94.9% baseline.
- **Ranked:** Best OSS always-on option with published performance. BUT: models CC-BY-NC-SA 4.0
  (unbundleable commercially), English-only, no official Android support, no standard independent
  benchmark. Last release Feb 2024 (re-verify maintenance status).
- **License:** Code Apache 2.0, models CC BY-NC-SA 4.0.
- **Relevance to SpeechAngel:** Target bar for FA/hr + FRR. Conceptually transferable (synthetic training
  + frozen backbone + lightweight classifier) but license + language restrictions block direct bundling.

### 3.3 microWakeWord (ESPHome / Home Assistant) — **the Android-proven edge option**
- **Architecture:** TensorFlow Lite models for MCU-class devices. Trained with synthetic data approach
  similar to openWakeWord. Integrated into ESPHome Voice hardware (ESP32-S3).
- **Evidence:** Powers Home Assistant Voice Preview Edition on ESP32-S3. Wyoming protocol server for Home
  Assistant Android integration — runs on-device in background even when locked. Best real-world proof
  that always-on software wake-word on Android is viable.
- **Ranked:** The most deployment-proven OSS option for SpeechAngel's platform (Android). BUT: no vendor
  benchmark numbers; independently measured by SpeechAngel below (§3.3.1) — no deployable operating point
  on cross-speaker data.
- **License:** Apache 2.0 (code + models, from esphome/micro-wake-word-models). Original repo by @kahrendt
  deleted; ESPHome fork Apache 2.0 — provenance needs legal review before bundling.
- **Relevance to SpeechAngel:** Candidate for a Stage-1 always-on gate *only* for quiet-environment,
  same-speaker use — not the heterogeneous, noise-robust gate SpeechAngel needs (see §3.3.1).

#### 3.3.1 SpeechAngel microWakeWord benchmark (2026-07-08)

Measured with the identical protocol as the Porcupine and DTW benchmarks
(`scripts/eval/bench_microWakeWord.py`). Picovoice wake-word-benchmark mixed streams (LibriSpeech +
DEMAND, cross-speaker), 6 keywords × ~20 min. Models: `alexa.tflite`, `hey_jarvis.tflite` (ESPHome V2),
exact ESPHome quantization reproduced.

| Keyword | Model | Best FA/hr ≤0.5? | Best FRR @ ≤5 FA/hr | Shipped cutoff → FRR / FA/hr |
|---------|-------|-------------------|----------------------|------------------------------|
| alexa | `alexa.tflite` (55 KB) | **FAIL** — 100% FRR @ 0.0 FA/hr | 57.5% FRR @ **64.7 FA/hr** | 0.90 → **97.5% FRR** / 3.1 FA/hr |
| jarvis | `hey_jarvis.tflite` (52 KB) | **FAIL** — 100% FRR @ 3.0 FA/hr | 92.5% FRR @ 15.1 FA/hr | 0.97 → **100.0% FRR** / 6.0 FA/hr |

**Findings:** (1) No deployable operating point — at shipped thresholds it detects almost nothing
(FRR ≥97.5%). (2) Cross-speaker generalization near-zero — trained on synthetic TTS for in-home
smart-speaker use, far out-of-distribution vs the benchmark's real speakers. (3) To catch even 42.5% of
alexa utterances, FA/hr = 64.7 — worse than SpeechAngel DTW's ~82 FA/hr at similar detection. (4) At
52-55 KB (int8), 20× smaller than the smallest neural KWS (BC-ResNet-1 ~320K) — the size explains the
poor cross-speaker generalization. *Conclusion: not a viable Stage-1 gate for SpeechAngel's cross-speaker,
noise-robust deployment; usable at best as a quiet-environment same-speaker fallback.*

### 3.4 Howl (Firefox Voice / castorini) — **the real-deployment reality bar**
- **Architecture:** Multiple options — res8, LSTM, LAS encoder, MobileNetv2. Published at NLP-OSS 2020.
  Common Voice + Montreal Forced Aligner for training.
- **Evidence:** **~10% FRR @ 4 FA/hr** in production with ~8,000 users. The most honest production numbers
  of any published system.
- **License:** MPL 2.0. Low star count (215), English-only, unclear if still maintained.
- **Relevance to SpeechAngel:** Sets the "shipped open system" reality bar — better than SpeechAngel's
  current dysarthric floor, far from the <5% FRR @ ≤0.5 FA/hr target.

### 3.5 sherpa-onnx KWS — **the open-vocabulary option**
- **Architecture:** Open-vocabulary KWS via tiny Zipformer-based ASR with beam search decoder + boosting
  scores + trigger thresholds per keyword. Chinese & English.
- **Evidence:** 3.3M param models (Zipformer), fp32 + int8, published APK for Android; Python/C/C++/Java/
  Kotlin/Swift/Go/Rust/C# APIs. Release 2026-06-18 (fast-moving — re-verify at build time).
- **License:** Apache 2.0. English model uses Gigaspeech (not dysarthric); no published FA/hr benchmark.
- **Relevance to SpeechAngel:** Path-A option for intact-speech users who prefer language-specific wake
  words. Not suited for the language-independent atypical-speech use case.

---

## 4. Benchmarks — what each actually measures

| Benchmark | What it measures | P1? | P2? | P3? | Dataset size |
|-----------|-----------------|-----|-----|-----|-------------|
| **GSC V1** (Google Speech Commands) | 12-class closed-set classification of 1s utterances | ✓ | — | — | 64,727 utterances |
| **GSC V2** | 35-class (12 + 23 extra) closed-set | ✓ | — | — | 105,829 utterances |
| **Hey Snips** (Sonos) | Wake-word detection of "Hey Snips" | ✓ | partial | — | 5,876+ / 45,344− |
| **LibriPhrase** | Zero-shot phrase retrieval from LibriSpeech (hard alignments) | ✓ | ✓ | — | synthesized alignments |
| **Picovoice wake-word-benchmark** | FA/hr from LibriSpeech + DEMAND mixes, cross-speaker | — | ✓ | ✓ | 118.7 min stream |
| **DiPCo** (Dinner Party Corpus) | Far-field speech + music + noise, ~5.5h — used by openWakeWord for P3 | — | — | ✓ | 5.5 hours |
| **Fluent Speech Commands** | Spoken language understanding (intent from phrase) | ✓ | — | — | 30,043 utterances |
| **LRDWWS 2024** | Speaker-dependent dysarthric wake-word (Mandarin, 10 words × 5 enrollments) | ✓ | ✓ | partial | small, clinical |

---

## 5. Evidence quality tier list

| Tier | Systems | Evidence strength | Caveat |
|------|---------|-------------------|--------|
| **A: Independently reproducible** | Porcupine (via Picovoice benchmark) | Measurable on shared data | Proprietary engine, vendor-controlled benchmark |
| **B: Peer-reviewed with published numbers** | BC-ResNet, MatchboxNet, ZP-KWS, PD-DWS, Howl | Conference/journal publication | Different protocols, mostly P1-only for conv models |
| **C: Open-source, self-reported** | openWakeWord, sherpa-onnx KWS | Code + models available, authors report numbers | No independent verification; FA/hr claims need replication |
| **D→B: Now independently measured** | microWakeWord (SpeechAngel benchmark) | Measured on Picovoice benchmark 2026-07-08 | 100% FRR @ ≤0.5 FA/hr; 57.5% FRR @ 64.7 FA/hr |
| **E: Proprietary, no/opaque numbers** | Sensory THF, SoundHound Houndify, Google Assistant, Siri | Undisclosed | Not usable as SOTA bar |

---

## 6. The numeric bar and the honest field ranking

### 6.1 The numeric bar — what "exceptional" means, with sources

| System | Headline result | Conditions | Why it's the bar |
|---|---|---|---|
| **Porcupine** | 97.1% detection @ **0.1 FA/hr** | 10 dB SNR | Transparent, verifiable commercial bar; <1 MB. The **accuracy-at-low-FAR-under-noise** target. |
| **openWakeWord** | design targets FAR <0.5/hr, FRR <5% | RPi3, 15–20 models/core | The **open-source deployable bar** (targets, not a guaranteed measured result). |
| **Howl** | 10% FRR @ 4 FA/hr | production, 8,000 users, Common Voice | The **real-deployment reality bar**. |
| **ZP-KWS** | FRR@1%FAR reduced ~60% rel (absolute ≈29–33%); 1.55M params | zero-shot, research-only | The **architecturally-closest SOTA** to SpeechAngel's constraint set. |
| **PhonMatchNet** | 67%/80% relative EER/AUC on LibriPhrase | zero-shot, research-only | The prior phoneme-guided zero-shot bar ZP-KWS builds on. |
| **PD-DWS** (LRDWWS'24 winner) | FAR 0.32% / FRR 0.5% (Score 0.00821), Rank 1 | closed-vocab dysarthric Mandarin, ASR-assisted, ~300M | The **atypical-speech ceiling** — near-perfect dysarthric wake-word *is* achievable (§7). |
| **DS-TCN** (LRDWWS'24 baseline) | FRR ~10.2% / FAR ~2.9% (Score 0.130) | same dysarthric set | **The reframe that matters:** even a *modest neural KWS* hits ~10% FRR on dysarthric speech — vs SpeechAngel's ~76% dysarthric FRR (§11). Most of the gap is a *model/data* gap, not a population ceiling. |
| **Euphonia / Universal Personalizer** (Google) | dysarthric ASR 13.9% WER (vs 17.5% SI); 2021 personalization up to 85% WER reduction | personalized, few-shot | Adjacent (ASR, not KWS) but the definitive **personalization proof-point**: the target population's poor default numbers are a model/data gap, not a population limit. |
| Sensory THF / SoundHound Houndify | claim better-than-benchmark; **no published numbers** | — | Commercial, opaque — noted for completeness, not a bar. |

**Distilled acceptance targets** (mirrored into `docs/ROADMAP.md`): always-on FAR MVP **≤0.5 FA/hr**
(openWakeWord), stretch **≤0.1 FA/hr** (Porcupine); FRR **<5%** at that FAR; noise **~97% det @ 10 dB SNR**
(Porcupine); atypical-speaker **FRR ~0.5% / FAR ~0.3%** possible closed-vocab (PD-DWS), **~10% FRR** for a
modest neural baseline (DS-TCN). SpeechAngel's distance from each is in §11.

### 6.2 Honest rankings by evidence

**Always-on FA/hr (P3, the product-gating metric):**

| Rank | System | FA/hr | FRR at that FA/hr | Evidence tier |
|------|--------|-------|--------------------|---------------|
| 1 | **Porcupine** | 0.1 | ~2.9% miss (97.1% det) @ 10 dB SNR | A |
| 2 | **openWakeWord** | <0.5 (design target) | <5% (design target) | C |
| 3 | **microWakeWord** (alexa, measured) | 64.7 | 57.5% FRR | D→B |
| 4 | **Howl** (production) | 4.0 | ~10% | B |

**Discrimination accuracy on GSC V2 (P1):** BC-ResNet-8 98.7% > BC-ResNet-1 98.0% > MatchboxNet (SOTA at
publication).

**Dysarthric / atypical speech:** PD-DWS 0.5% / 0.32% (closed-vocab Mandarin, ~300M) > DS-TCN 10.2% / 2.9%
(modest neural baseline) > SpeechAngel (dysarthric floor, §11).

### 6.3 The field on 7 axes (recovered from the retired competitive-bar)

Scored on the user-supplied axes (noise / trainability / language-independence / atypical-speaker /
maturity / efficiency / transparency; **overall = rounded mean**), so SpeechAngel is directly comparable.
These are **analyst-assigned 0–100 scores**, not externally published metrics — use them as a strategic
map, not a head-to-head result (§0).

| System | Noise | Train | Lang-indep | Atypical | Maturity | Efficiency | Transparency | **Overall** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Porcupine** | 85 | 70 | 40 | 55 | 90 | 95 | 85 | **74** |
| **Sensory THF** | 60 | 65 | 55 | 60 | 90 | 90 | 20 | **63** |
| **openWakeWord** | 75 | 55 | 30 | 35 | 75 | 75 | 65 | **59** |
| **Howl** | 55 | 45 | 75 | 55 | 30 | 70 | 80 | **59** |
| **⭐ SpeechAngel** | **25** | **85** | **95** | **40** | **15** | **65** | **90** | **59** |
| **PhonMatchNet-class** | 50 | 90 | 55 | 25 | 15 | 55 | 85 | **54** |
| **Houndify** | 45 | 55 | 45 | 40 | 70 | 50 | 15 | **46** |

**The strategic read — SpeechAngel's profile is the most *inverted* in the field.** It has already *won*
the axes hardest to retrofit (language-independence 95, trainability 85, transparency 90) and lost the
axes most *buildable* (noise 25, maturity 15, tuned atypical accuracy 40). You cannot bolt
language-independence onto Porcupine, but you *can* bolt noise robustness and a wake cascade onto
SpeechAngel — a more promising place to start than the inverse. (Efficiency 65 is the most exposed
self-score: MFCC-DTW is cheap *a priori*, but latency/CPU are unbenchmarked on a physical device — treat
as an estimate to confirm.)

---

## 7. Atypical-speech ceiling — PD-DWS transferable techniques

*(Recovered from the retired competitive-bar; source `research/word-spotting2409.10076v1.pdf`,
[arXiv:2409.10076](https://arxiv.org/abs/2409.10076).)*

PD-DWS (NPU + Xiaomi) is the closest published work to SpeechAngel's actual problem —
speaker-dependent dysarthric wake-up-word spotting from a few enrollments — so it is mined for what
transfers, not just its headline. It stacks four ideas, each mapping to a SpeechAngel lever:

1. **SSL front-end instead of MFCC** — a pretrained **data2vec2** (~300M) finetuned multi-task, not MFCC.
   The transferable claim ("learned SSL features beat MFCC for this population") is validated on dysarthric
   speech; a small distilled encoder can chase it (their model is far too large to ship).
2. **Multi-task auxiliary ASR** — a joint ASR + WWS objective (CTC assists max-pooling KWS). *Breaks
   language-independence* (needs an ASR branch) → a milder-impairment / Path-A option, not the default.
3. **Dual-filter cascade decision** — a threshold filter then an ASR filter cross-verifying the detected
   word's *length* against an independent Paraformer decode; length mismatch → reject. A concrete,
   powerful **verification/rejection** design — a cheap second opinion that cuts FAR without moving the
   primary detector. (SpeechAngel's own banked duration-ratio cross-verify, §11, is the
   constraint-preserving version of this idea.)
4. **TTS + noise augmentation** — VITS-synthesized dysarthric audio + MUSAN noise at 8–20 dB SNR, 0.9–1.1×
   speed perturbation. SpeechAngel's noise-robustness + data-scarcity recipe.

**Operating-point lesson:** their ablation shows the accept threshold rank swings Score 0.070 → 0.032 —
the *decision layer*, not just the model, holds a large fraction of the error. This matches SpeechAngel's
own held-out TORGO finding that threshold cost dominates.

**Honest boundary:** PD-DWS is closed-vocabulary Mandarin, ASR-assisted, ~300M params — it trades away
exactly the axes SpeechAngel scores highest on. It is the **accuracy ceiling to learn from**, not a design
to copy wholesale; the constraint-respecting takeaways are the small SSL front-end, the dual-filter
cascade, and the augmentation recipe.

---

## 8. Relevance to SpeechAngel's constraints, and patterns that transfer

### 8.1 Relevance matrix

| System | Lang-indep ✓ | User-trainable ✓ | On-device ✓ | OSS bundleable ✓ | Android ✓ |
|--------|-------------|-----------------|-------------|-------------------|----------|
| **SpeechAngel DTW** | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Porcupine** | ✗ | partial | ✓ | ✗ (proprietary, AccessKey) | ✓ |
| **openWakeWord** | ✗ (EN only) | partial (synthetic, needs TTS per lang) | ✓ (RPi3) | ✗ (models CC-NC) | ✗ (no official) |
| **microWakeWord** | ✗ (EN only) | partial (synthetic, can train custom) | ✓ (ESP32) | ✓ (Apache 2.0) | ✓ (via Wyoming) |
| **Howl** | ✗ (EN only) | ✓ (Common Voice training) | ✓ | ✓ (MPL 2.0) | ✗ |
| **sherpa-onnx KWS** | ✗ (ZH+EN) | ✗ (model fixed, keywords configurable) | ✓ | ✓ (Apache 2.0) | ✓ (APK) |
| **ZP-KWS** | ✓ (phoneme) | partial (few-shot speaker enroll) | ✓ (1.55M) | ✗ (research, no release) | ✗ |
| **BC-ResNet** | ✗ (trained per keyword) | partial (can retrain) | ✓ (10K-320K) | ✓ (Apache 2.0, Qualcomm) | ✗ (no Android lib) |
| **PD-DWS** | ✗ (closed-vocab Mandarin) | partial (speaker-dependent) | ✗ (300M params) | ✗ (research) | ✗ |

### 8.2 Architecture patterns that transfer to SpeechAngel

- **Shared backbone + lightweight heads (openWakeWord):** freeze a pre-trained embedding (Google speech
  embed, DistilHuBERT, WavLM); train per-wake-word classifiers on top. Matches SpeechAngel's
  multi-command architecture exactly.
- **Multiplicative speaker gating (ZP-KWS):** run phoneme + speaker encoders in parallel; multiply
  outputs (late fusion) so a wake word fires only when *both* the phoneme sequence AND the enrolled
  speaker are present. Directly reduces FA/hr.
- **Cascade / two-stage (Porcupine, PD-DWS):** cheap aggressive Stage-1 (high recall, high FA) → Stage-2
  verifier (very low FA). This is SpeechAngel's existing `WakeGatedRecognizer` shape — currently with a
  DTW Stage-1.
- **Synthetic training data (openWakeWord):** train on TTS + noise augmentation to bootstrap any wake word
  before real enrollment data exists.
- **VAD gating (universal):** pre-filter with energy/Silero VAD; on ambient audio 80-95% of frames are
  silence/noise. SpeechAngel has `StreamingEnergyGate` but it is not calibrated.

---

## 9. Roadmap items derived from the field (R-SOTA-1..6)

Each competitor teaches a lever. The canonical, tracked list lives in **`docs/ROADMAP.md`** ("SOTA
competitive bar — derived items"); this is a summary, not the source of truth.

| Item | Lesson → action |
|---|---|
| **R-SOTA-1** | ZP-KWS/PhonMatchNet — a zero-shot phoneme-matching encoder beats MFCC-DTW while keeping the constraints, at ~1.55M params. Evaluate in the `QbeEncoder` seam. |
| **R-SOTA-2** | openWakeWord — a Stage-1 wake gate at ≤0.5 FA/hr keeps the matcher off raw ambient. The deployability gate; comes first. |
| **R-SOTA-3** | Porcupine — adopt the Picovoice `wake-word-benchmark` reporting protocol (detection @ fixed FA/hr @ SNR) so numbers are externally comparable. Cheap; unblocks comparable reporting now. |
| **R-SOTA-4** | PD-DWS — adopt the constraint-respecting techniques: small SSL front-end (R-SOTA-1), a dual-filter cascade (the banked duration cross-verify), TTS+MUSAN augmentation (R-SOTA-6). Skip the ASR branch (Path-A only). |
| **R-SOTA-5** | Howl — add Common Voice (multilingual, CC0) as a language-independence eval corpus; set "10% FRR @ 4 FA/hr" as the realistic production milestone before the <5% stretch. |
| **R-SOTA-6** | Noise axis (all) — multi-condition enrollment/augmentation (RIR + MUSAN) + SNR-adaptive accept threshold; attack the noise-axis gap directly. |

---

## 10. Open questions (for SpeechAngel's roadmap)

1. **Can a phoneme-supervised encoder (ZP-KWS class) replace MFCC-DTW while keeping language
   independence?** 1.55M params is on-device feasible; the representation is language-agnostic (needs a
   pronunciation lexicon per language).
2. **Does synthetic training (openWakeWord pattern) work for dysarthric speech?** TTS is trained on
   typical speech; dysarthric TTS is a research problem. On-device enrollment of real user recordings is
   SpeechAngel's differentiator here.
3. **What is the FA/hr of a DistilHuBERT/WavLM cascade on *real* ambient audio (not clean LibriSpeech
   background, not a deterministic sim)?** All current sub-5%-FRR numbers are off-device / simulated (§11).
4. **microWakeWord license lineage** — original repo deleted; ESPHome fork Apache 2.0. Legal review before
   any bundling.

---

## 11. Where SpeechAngel stands (internal — not lifted into the paper)

> This section grades SpeechAngel against the bar above. It is deliberately short and **links** to the
> full scorecards rather than duplicating them.

### 11.1 Measured position of record (config-explicit)

Every number names its front-end config, corpus, regime, and on/off-device status — the guard against
manufactured contradictions with the linked scorecards.

| Axis | Measurement of record | Source |
|---|---|---|
| **Closed-set rank-1 (dysarthric)** | **59.2%** — static MFCC-DTW (`none`; = `MfccConfig` default, `core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt`), TORGO speaker-dependent, held-out (EVAL-002). *(The `delta_delta` eval-harness variant is 55.4%; used correctly in the CP-1 2×2 — not the shipped config.)* | `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`, `docs/testing/2026-07-06_frr-far-torgo.md` |
| **Closed-set rank-1 (control)** | **74.6%** — but this is the `delta_delta` run; the static-control grid was never run. | `docs/testing/2026-07-06_frr-far-torgo.md` |
| **Open-set FRR @ FAR≤5%/utt (dysarthric)** | **75.7%** (static = shipped). *(`delta_delta`: 78.3%.)* | `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md` |
| **Standard benchmark (cross-speaker = lower bound)** | Picovoice wake-word-benchmark: clean rank-1 **89.2%**; **87.5% miss @ 0.1 FA/hr** (thr 23.93, pinned curve); ~119 FA/hr at first useful detection. No viable always-on point. | `docs/testing/2026-07-06_picovoice-wake-word-benchmark.md` |
| **Always-on ambient (P3)** | Early proxy **~82 FA/hr**, at a loose ≤5%-OOV-FAR threshold — **optimistically biased** (F01's own OOV utterances + silence + 20 dB noise; real continuous TV fires *more*). A later in-regime reframe argues the "no viable point" pessimism was substantially a *cross-speaker-benchmark* artifact; in-regime, MFCC gets 68.8% det (**FRR 31.2%**) @ ~0 FA/hr for F01 — a real but far lower wall. **This tension is unresolved; both readings are recorded, neither is headlined.** | `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`, `docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md` |
| **Noise (dysarthric rank-1)** | 64.6% clean → 56.1% @20 dB → 34.1% @10 dB → 8.5% @5 dB (near-chance by 5 dB). | `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md` |

### 11.2 Honesty ledger — banked vs deployable (the discipline that makes this authoritative)

The distinction that matters is **deployable**, not merely *banked*. The repo banks several research
wins; none is deployment-validated.

- **Banked & deployable-relevant for the shipped system:** the MFCC-DTW TORGO floor (rank-1 59.2%, FRR
  75.7% @ FAR 4.6%, static); the Picovoice cross-speaker lower bound (rank-1 89.2%, no viable always-on
  point). *These are what actually ships today.*
- **Banked research findings — NOT yet deployable (off-device):** the CP-1 rank-1 embedding win
  (**55.4→71.9**, WavLM-L12 pooled-cosine, 95M, English-only, McNemar **p=2×10⁻⁶**, both arms
  `delta_delta`) — but it does **not** auto-translate to a deployable always-on point; the banked
  dual-cascade duration cross-verify (WavLM-base-plus L12, per-window-VAD harness: F03 **50.3→25.4% FRR**,
  49.5% rel, **p<0.001**, strict domination; F04 28.6% rel, p=0.134 underpowered; F01 already at 3.1%) —
  banked *relative* reduction, MFCC-level and real-ambient not evaluated; and the banked **negatives**
  (per-command/per-template calibration refuted, held-out FAR blows to 24–34%; margin-ratio / common-mode
  rejection refuted). *(Note: "25% FRR @ ≤0.5 FA/hr" belongs to the **WavLM-L12** single-threshold F01
  in-regime probe (pre-cascade) — NOT to DistilHuBERT.)*
- **Not-banked / exploratory / simulated:** the sub-5%-FRR / "0.0% FRR" absolutes (E11–E20 — a
  deterministic single-harness simulation with a random-command-subset confound); the DistilHuBERT
  "CP-2 solved" cascade absolutes (F01 0.0% / F03 2.2% / F04 6.0% — off-device Python only); margin/ratio/
  z-norm rejection scorers; per-language enrollment (untested — language independence is "by construction"
  only). Sources: `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`,
  `docs/testing/2026-07-07_cp2-dual-cascade-verification.md`, `docs/testing/2026-07-07_journey-cp2-summary.md`,
  `docs/testing/2026-07-08_experiments-e11-e20-sim.md`.
- **Hard deployment gate — the number that governs all the above:** on-device (CP-3) = **0/200**,
  real-user (CP-0) = **0/200**. **No SOTA-level result has run on a real device or with real users.**

**Contested, flagged not fixed** (these live in evidence docs and are left as-is there): the
vocabulary-size effect — banked `journey-cp2` says "vocab dominates" (F03 25.4% @ 77 cmds vs F01 3.1% @ 15
cmds) while not-banked E17 says "not binding" (random-subset sim). Evidence is **asymmetric** — the banked
result outweighs the not-banked one; presented as open. Likewise `docs/research/experiments/RESULTS.md`
still shows a stale "switch default DELTA_DELTA→NONE" recommendation that the code already implements.

### 11.3 Three scoring systems, reconciled

SpeechAngel carries three deliberately different scores; they measure different things and are all true:

- **Overall 59 / 100** (§6.3) — a *flat mean of 7 technical axes* where maturity is only 1/7, so the
  differentiated-design axes pull it to mid-field.
- **480 / 1000** (`docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md`) —
  *validation-weighted product maturity*, where delivered/measured user value dominates and hygiene is
  capped under the pre-alpha→alpha validation wall.
- **SOTA = 1000** (`docs/product/2026-07-08_sota-domain-bands.md`) — a 15-domain, *constraint-preserving*
  band ladder measuring distance to a language-independent/on-device/user-trainable ceiling.

The code-only path up the bands (480→~890) is `docs/product/2026-07-08_score-band-pathway.md`. A
differentiated-but-unvalidated product ranks mid-field on raw technical axes yet low on product maturity;
both are correct.

---

## 12. Sources

- Porcupine — [picovoice.ai/docs/faq/porcupine](https://picovoice.ai/docs/faq/porcupine/) ·
  [github.com/Picovoice/porcupine](https://github.com/Picovoice/porcupine) ·
  [github.com/Picovoice/wake-word-benchmark](https://github.com/Picovoice/wake-word-benchmark)
- openWakeWord — [github.com/dscripka/openWakeWord](https://github.com/dscripka/openWakeWord)
- microWakeWord — [github.com/esphome/micro-wake-word-models](https://github.com/esphome/micro-wake-word-models)
- Howl / Firefox Voice — [arxiv.org/abs/2008.09606](https://arxiv.org/abs/2008.09606) ·
  [github.com/castorini/howl](https://github.com/castorini/howl)
- sherpa-onnx — [github.com/k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)
- Sensory TrulyHandsfree — [sensory.com](https://sensory.com/) (opaque; no published numbers)
- BC-ResNet — [arxiv.org/abs/2106.04140](https://arxiv.org/abs/2106.04140) (Interspeech 2021)
- MatchboxNet — [arxiv.org/abs/2004.08531](https://arxiv.org/abs/2004.08531) (Interspeech 2020)
- MDTC — [arxiv.org/abs/2005.06720](https://arxiv.org/abs/2005.06720)
- PhonMatchNet (Interspeech 2023) — [arxiv.org/abs/2308.16511](https://arxiv.org/abs/2308.16511) ·
  [github.com/ncsoft/PhonMatchNet](https://github.com/ncsoft/PhonMatchNet)
- ZP-KWS — Hu et al., NTNU, 2026, [arxiv.org/abs/2606.20106](https://arxiv.org/abs/2606.20106) —
  *ID web-verified 2026-07-06 (2606 = June 2026); venue/DOI future-dated — re-verify before paper lift.*
- LRDWWS'24 winner (PD-DWS) — `research/word-spotting2409.10076v1.pdf` ·
  [arxiv.org/abs/2409.10076](https://arxiv.org/abs/2409.10076) *(numbers read from the PDF: test-B FAR
  0.00321 / FRR 0.005 / Score 0.00821; baseline Score 0.130306, FAR 0.028639, FRR 0.101667).*
- SSL backbones — wav2vec 2.0 [arxiv.org/abs/2006.11477](https://arxiv.org/abs/2006.11477); HuBERT
  [arxiv.org/abs/2106.07447](https://arxiv.org/abs/2106.07447); WavLM
  [arxiv.org/abs/2110.13900](https://arxiv.org/abs/2110.13900); DistilHuBERT
  [arxiv.org/abs/2110.01900](https://arxiv.org/abs/2110.01900).
- Dysarthric ASR personalization — Google Project Euphonia
  [research.google/blog/personalized-asr-models-from-a-large-and-diverse-disordered-speech-dataset](https://research.google/blog/personalized-asr-models-from-a-large-and-diverse-disordered-speech-dataset/)
  · "Universal Personalizer" [arxiv.org/abs/2509.15516](https://arxiv.org/abs/2509.15516) (13.9% WER).
- Foundational — Sakoe & Chiba DTW (1978); Davis & Mermelstein MFCC (1980); Zhang (2014)
  language-independent DTW (PLOS ONE).
- SpeechAngel measured evidence — `docs/testing/2026-07-06_frr-far-torgo.md`,
  `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`,
  `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`,
  `docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md`,
  `docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`,
  `docs/testing/2026-07-07_cp2-dual-cascade-verification.md`,
  `docs/testing/2026-07-07_journey-cp2-summary.md`,
  `docs/testing/2026-07-08_experiments-e11-e20-sim.md`.

---

## 13. Paper-reconciliation notes (for the sibling *speechangel-paper* repo)

The spine (§0–§10) is written to be lifted into the paper's related-work / SOTA section. Before lifting,
**update these now-stale paper passages** (paper dated 2026-06-29, predates the 07-06→07-08 measurement
corpus):

1. The paper states it reports **"no false-rejection or false-acceptance rates of our own … accuracy today
   is unknown and must be measured."** This is now false — §11 has the measured floor (dysarthric rank-1
   59.2%, FRR 75.7%; Picovoice 89.2% / no viable always-on point). Replace with the measured, config-
   qualified numbers and the honesty ledger.
2. The paper claims DTW **"tended to reach accuracies in the low-to-mid ninety per cents for small
   vocabularies in quiet conditions."** True only for *control* FC01 (91.2%, 16 cmds); dysarthric is
   55–59%. Qualify by population, or the claim overstates the atypical-speech case the paper is about.
3. Verify the ZP-KWS citation (arXiv 2606.20106 / Interspeech 2026) resolves before adding to
   `references.bib`.

---

## 14. Update log

| Date | Change |
|------|--------|
| 2026-07-08 | Initial comprehensive reference (families, production systems, benchmarks, competition results). |
| 2026-07-08 | microWakeWord independently measured on Picovoice benchmark — no deployable operating point (§3.3.1). |
| 2026-07-08 | **Consolidation into the authoritative SOTA doc.** Folded in the retired `docs/product/2026-07-06_sota-competitive-bar.md` (7-axis field ranking §6.3, PD-DWS technique mining §7, Euphonia proof-point §6.1, governing comparability caveat §0, R-SOTA summary §9). Added the config-explicit measured-standing section (§11) with the 3-way banked/deployable honesty ledger and the three-scoring reconciliation. Fixed the prior self-contradiction attributing "25% FRR @ 0.5 FA/hr" to DistilHuBERT (it is WavLM-L12; DistilHuBERT's banked F01 dual-cascade ceiling is 3.1%). Added paper-reconciliation notes (§13). |
