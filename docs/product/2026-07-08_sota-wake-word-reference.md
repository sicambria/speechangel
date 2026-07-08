<!-- SOTA wake-word / keyword spotting reference. First-principles taxonomy, algorithms, benchmarks, and evidence-ranked systems. Supersedes ad-hoc research in 2026-07-06_sota-competitive-bar.md. -->
# Wake Word / Keyword Spotting — First-Principles SOTA Reference

**Date:** 2026-07-08 · **Status:** living reference, update with new evidence.

> Covers all major algorithm families, production systems, benchmarks, and competition results. Every claim is sourced: arxiv paper, GitHub README, published competition result, or reproducible benchmark. Marketing-only claims are flagged.

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

P1 is easiest (89.2% closed-set rank-1 even with MFCC-DTW). P3 is hardest (needs ≤0.5 FA/hr across unlimited audio). The ratio P3/P1 is ~10³–10⁴ for DTW; ~10² for neural KWS; ~10 for the best cascade systems.

### 1.1 Key metrics — definitions matter

- **FRR (False Reject Rate):** % of intended wake-word utterances *not* detected. Lower is better.
- **FAR (False Accept Rate):** % of non-wake audio segments falsely triggered. Lower is better.
- **FA/hr (False Accepts per Hour):** Absolute count of false triggers per hour of continuous audio. The **only deployable metric for P3** — FAR is meaningless without stream duration context.
- **ROC / DET curve:** FRR vs FAR trade-off swept across thresholds. The standard academic plot.
- **RTF (Real-Time Factor):** sec_compute / sec_audio. <1 for real-time.
- **#Params / model size:** MB on disk.
- **MACs / FLOPs:** Multiply-accumulate operations per inference step.

**Critical insight:** A KWS paper reporting "97% accuracy" on GSC V2 (P1 only) tells you nothing about FA/hr (P3). Most papers measure P1; few measure P3. Always-on deployment needs P3 numbers.

---

## 2. Algorithm families — first-principles taxonomy

### 2.1 Template matching (DTW / correlation)

**Principle:** Store exemplar(s) of the wake word; slide a window over the stream; compute distance (e.g. DTW alignment cost); threshold.

| Variant | Mechanism | Strengths | Weaknesses |
|---------|-----------|-----------|------------|
| MFCC + DTW | Mel-frequency cepstral coefficients + Dynamic Time Warping alignment cost | Language-independent, user-trainable, zero-shot, tiny footprint | ~10³× worse FA/hr than neural KWS; no negative learning |
| MFCC + GMM-UBM | Gaussian Mixture Models with a Universal Background Model as impostor prior | Softer threshold via likelihood ratio; established in speaker verification | Still decades behind neural approaches |
| Cross-correlation | Raw waveform correlation | Fastest, zero features | Only works for exact repetition in clean audio |

**Evidence:** SpeechAngel's MFCC-DTW at Picovoice benchmark → 87.5% miss @ 0.1 FA/hr, ~82 FA/hr ambient. PocketSphinx (HMM-based) → similar regime at ~7.2% CPU on RPi5. *Verdict: Not viable for always-on; useful only as structured-data source for multi-stage cascade.*

### 2.2 Small convolutional KWS (the neural baseline)

**Principle:** End-to-end CNN on spectrogram input. Trained on labeled keyword/non-keyword data. The dominant academic family since 2017.

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

**Evidence:** BC-ResNet holds the published GSC V1/V2 accuracy leaderboard at 98.0%/98.7%. MatchboxNet was the prior SOTA and is production-hardened (NVIDIA NeMo). These are tiny models (<500K params) suited for MCU deployment.

**Key limitation:** GSC is a P1 (discrimination-only) benchmark. Winning GSC tells you almost nothing about FA/hr on continuous ambient audio. Most papers do not report FA/hr.

### 2.3 Phoneme-supervised encoders (zero-shot KWS)

**Principle:** Train an encoder to map audio → phoneme-probability sequence. At inference, match the input against target keyword phoneme sequence. No per-word retraining needed.

| Model | Mechanism | Result | #Params | Year | Source |
|-------|-----------|--------|---------|------|--------|
| **PhonMatchNet** | Phoneme posteriorgram + DTW-like matching | 67%/80% relative EER/AUC improvement on LibriPhrase | — | 2023 | Interspeech 2023 |
| **ZP-KWS** | Phoneme-supervised encoder + GE2E speaker encoder (0.9M), multiplicative late fusion | FRR@1%FAR reduced ~60% vs strongest baseline | **1.55M** total | 2026 | arXiv:2606.20106, Interspeech 2026 |
| **sherpa-onnx KWS** (Zipformer) | Open-vocabulary via beam search + boosting scores + trigger thresholds per keyword | Tunable per deployment; proven on Android | ~3.3M | 2024-2025 | k2-fsa/sherpa-onnx |

**Evidence:** ZP-KWS achieves 60% relative FRR improvement at 1% FAR, supports zero-shot (unseen keywords + unseen speakers), is language-agnostic (phoneme-supervised), edge-deployable at 1.55M params. This is the **architecturally closest SOTA to SpeechAngel's constraint set**: language-independent, user-trainable, zero-shot, on-device.

**Key limitation:** Phoneme supervision requires a pronunciation lexicon for the target language (though the encoder itself is language-agnostic). Measured on LibriPhrase/GSC, not on continuous ambient FA/hr streams.

### 2.4 SSL transfer (wav2vec 2.0, HuBERT, WavLM, Whisper-based)

**Principle:** Pre-train a large model on massive unlabeled audio via self-supervised learning (masked prediction). Fine-tune a lightweight head for KWS. The SSL backbone provides rich representations from minimal labeled data.

| Model | Backbone | Result | #Params | Year |
|-------|----------|--------|---------|------|
| wav2vec 2.0 + KWS head | wav2vec 2.0 Base (95M) | Strong few-shot KWS | 95M (backbone) | 2020 |
| HuBERT + KWS head | HuBERT Base (95M) | SOTA on many tasks | 95M | 2021 |
| WavLM + KWS head | WavLM Base (94M) | Best SSL for speech tasks (SUPERB benchmark) | 94M | 2022 |
| Whisper-tiny + KWS | Whisper tiny (39M) | Multilingual zero-shot via decoder | 39M | 2022 |
| DistilHuBERT + cascade | DistilHuBERT (23.5M) | SpeechAngel CP-2 best: 25% FRR @ 0.5 FA/hr | 23.5M | 2026 (SpeechAngel measured) |

**Evidence:** WavLM Base holds the SUPERB benchmark leaderboard for general speech representation. SpeechAngel's own measurement (DistilHuBERT, 23.5M) reaches 25% FRR @ 0.5 FA/hr — 3× better than MFCC-DTW at matched FA/hr but still 5× off the <5% target. *Verdict: SSL transfer is the most promising path for SpeechAngel, striking the best language-independence/accuracy trade-off, but requires distillation/cascade architecture for on-device deployment.*

### 2.5 Large-scale ASR-based KWS (the non-transferable ceiling)

**Principle:** Full ASR pipeline → keyword detection from transcript. Accuracy ceiling but trades away all SpeechAngel constraints.

| System | Approach | Result | #Params | Source |
|--------|----------|--------|---------|--------|
| **PD-DWS** (LRDWWS'24 winner) | data2vec2 + ASR-assisted dual-filter cascade | FAR 0.32%, FRR 0.5% on dysarthric Mandarin | ~300M | LRDWWS 2024 |
| **Whisper + keyword match** | Whisper-large-v3 transcript → regex match | Near-perfect for clear English | 1.5B | — |

**Evidence:** PD-DWS proves near-perfect dysarthric wake-word detection is *possible* with enough model capacity. But the ~300M param data2vec2 backbone, ASR assistance, and closed-vocabulary Mandarin constraint make it non-transferable wholesale to an on-device, language-independent system. *Verdict: Existence proof for the population ceiling, not an architecture to port.*

---

## 3. Production systems — evidence-ranked

### 3.1 Porcupine (Picovoice) — **the commercial bar**
- **Architecture:** Proprietary DNN. Custom-keyword training via web portal.
- **Evidence:** Picovoice's own benchmark (LibriSpeech + DEMAND, 6 keywords, 118.7 min, cross-speaker): **97.1% detection @ 0.1 FA/hr @ 10 dB SNR**, <1 MB, 3.8% CPU on RPi-3, 2.2% CPU on RPi-5.
- **Ranked:** Best measured always-on FA/hr of any system with published numbers. BUT: proprietary engine, requires AccessKey, free tier 3 active users/month, language-dependent.
- **License:** Proprietary (Apache-2.0 only on SDK bindings).
- **Relevance to SpeechAngel:** Sets the accuracy-at-low-FAR-under-noise target. Not bundleable.

### 3.2 openWakeWord — **the open-source deployable bar**
- **Architecture:** 3-stage: (1) Melspectrogram (ONNX, fixed params) → (2) Frozen Google speech embedding backbone (conv blocks, pre-trained on massive data) → (3) Per-wake-word classifier (FC or 2-layer RNN). Shared backbone, small per-model classifier. Trained on **100% synthetic TTS data** with ~30K hours negative data.
- **Evidence:** From project README: "Target performance of <5% FRR and <0.5 FA/hr." DET curve shows outperforming Porcupine on "Alexa" model; competitive with custom Porcupine + Mycroft Precise on "Hey Mycroft." On RPi-3: 15-20 models simultaneously on single core. Fluent Speech Commands: 97.5% test accuracy vs 94.9% baseline.
- **Ranked:** Best OSS always-on option with published performance. BUT: models CC-BY-NC-SA 4.0 (unbundleable commercially), English-only, no official Android support, no standard independent benchmark.
- **License:** Code Apache 2.0, models CC BY-NC-SA 4.0.
- **Relevance to SpeechAngel:** Target bar for FA/hr + FRR. Conceptually transferable (synthetic training + frozen backbone + lightweight classifier) but license + language restrictions block direct bundling.

### 3.3 microWakeWord (ESPHome / Home Assistant) — **the Android-proven edge option**
- **Architecture:** TensorFlow Lite models for MCU-class devices. Trained with synthetic data approach similar to openWakeWord. Integrated into ESPHome Voice hardware (ESP32-S3).
- **Evidence:** Powers Home Assistant Voice Preview Edition on ESP32-S3 (MCU, not mobile). Wyoming protocol server for Home Assistant Android integration — runs on-device in background even when locked. Best real-world proof that always-on software wake-word on Android is viable.
- **Ranked:** The most deployment-proven OSS option for SpeechAngel's platform (Android). BUT: no published benchmark numbers, unknown FA/hr on ambient audio, ESP32-S3-optimized architecture may not be ideal for phone-class hardware.
- **License:** Apache 2.0 (code + models, from esphome/micro-wake-word-models).
- **Relevance to SpeechAngel:** Primary candidate for Stage-1 always-on gate if DTW proves insufficient. License is clean. Needs independent benchmark on SpeechAngel's target data.
- **⚠️ MEASURED (2026-07-08):** Benchmarked on identical Picovoice wake-word-benchmark mixed streams (LibriSpeech + DEMAND, cross-speaker). See §3.3.1 for full results.

#### 3.3.1 SpeechAngel microWakeWord benchmark (2026-07-08)

Measured with identical protocol as the Porcupine and DTW benchmarks (`scripts/eval/bench_microWakeWord.py`).

**Test conditions:** Picovoice wake-word-benchmark mixed streams, LibriSpeech + DEMAND at variable SNR, 6 keywords × ~20 min streams. Models: `alexa.tflite` and `hey_jarvis.tflite` (ESPHome V2). ESLHome exact quantization reproduced (`pymicro-features` frontend + `int8 = round(float * 9.84024) - 128`).

| Keyword | Model | Stream duration | Labels | Best FA/hr ≤0.5? | Best FRR @ ≤5 FA/hr | Shipped cutoff | Shipped FRR | Shipped FA/hr |
|---------|-------|----------------|--------|-------------------|----------------------|----------------|-------------|---------------|
| alexa | `alexa.tflite` (55 KB) | 19.5 min | 40 | **FAIL** — 100% FRR @ 0.0 FA/hr | 57.5% FRR @ **64.7 FA/hr** | 0.90 | **97.5% FRR** | 3.1 FA/hr |
| jarvis | `hey_jarvis.tflite` (52 KB) | 19.9 min | 40 | **FAIL** — 100% FRR @ 3.0 FA/hr | 92.5% FRR @ 15.1 FA/hr | 0.97 | **100.0% FRR** | 6.0 FA/hr |

**Key findings:**

1. **No deployable operating point exists.** At the shipped thresholds, microWakeWord detects almost nothing (1/40 for alexa, 0/40 for jarvis) — FRR ≥97.5%.
2. **Cross-speaker generalization is near-zero.** These models were trained on synthetic TTS for in-home smart-speaker use — the Picovoice benchmark keyword takes (real human speakers, variable microphone conditions) are far out-of-distribution.
3. **FA/hr is high at any useful detection rate.** To catch even 42.5% of alexa utterances (cutoff=0.10), FA/hr = 64.7 — worse than SpeechAngel DTW's ~82 FA/hr at similar detection.
4. **jarvis model mismatched.** Trained for "Hey Jarvis" but benchmark keyword is bare "jarvis" — explains the 92.5% FRR floor.
5. **Model size vs performance trade-off.** At 52-55 KB (int8 TFLite), these are 20× smaller than even the smallest neural KWS (BC-ResNet-1 ~320K). The size explains the poor cross-speaker generalization.

**Conclusion for SpeechAngel:** microWakeWord is not a viable Stage-1 wake gate for the cross-speaker, noise-robust deployment SpeechAngel requires. It may be usable as a lightweight "quiet-environment same-speaker" fallback, but its strength is MCU-class efficiency for in-home smart speakers with known voices — not the heterogeneous, noise-robust always-on gate SpeechAngel needs.

### 3.4 Howl (Firefox Voice / castorini) — **the real-deployment reality bar**
- **Architecture:** Multiple options — res8, LSTM, LAS encoder, MobileNetv2. Published at NLP-OSS 2020. Uses Common Voice + Montreal Forced Aligner for training.
- **Evidence:** **~10% FRR @ 4 FA/hr** in production with ~8,000 users. Provides best real-world "what to actually expect" numbers.
- **Ranked:** Most honest production numbers of any published system. BUT: low star count (215), English-only, MPL 2.0 license, unclear if still maintained.
- **License:** MPL 2.0.
- **Relevance to SpeechAngel:** Sets the "shipped open system" reality bar. 10% FRR @ 4 FA/hr is still better than SpeechAngel's current (76% FRR @ ~5% FAR), but far from the <5% FRR @ ≤0.5 FA/hr target.

### 3.5 sherpa-onnx KWS — **the open-vocabulary option**
- **Architecture:** Open-vocabulary KWS via tiny Zipformer-based ASR with beam search decoder + boosting scores + trigger thresholds per keyword. Supports Chinese & English.
- **Evidence:** 3.3M param models (Zipformer), fp32 + int8, published APK for Android. Pre-built CLI, Python/C/C++/Java/Kotlin/Swift/Go/Rust/C# APIs. Proven streaming ASR pipeline behind it.
- **Ranked:** Best OSS for language coverage (Chinese + English) and open-vocabulary (no retraining for new keywords). BUT: English model uses Gigaspeech (not dysarthric), no published FA/hr benchmark.
- **License:** Apache 2.0.
- **Relevance to SpeechAngel:** Path-A option for intact-speech users who prefer language-specific wake words. Not suited for language-independent atypical-speech use case.

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
| **D: Open-source, deployment-proven, no benchmark** | microWakeWord | Runs in production (Home Assistant) | No published accuracy numbers |
| **D→B: Now independently measured** | microWakeWord (SpeechAngel benchmark) | Measured on Picovoice benchmark 2026-07-08 | 100% FRR @ ≤0.5 FA/hr; 57.5% FRR @ 64.7 FA/hr |
| **E: Proprietary, no/opaque numbers** | Sensory THF, SoundHound Houndify, Google Assistant, Siri | Undisclosed | Not usable as SOTA bar |

---

## 6. The honest ranking — best by evidence

For **always-on FA/hr** (P3, the product-gating metric):

| Rank | System | FA/hr | FRR at that FA/hr | Evidence tier |
|------|--------|-------|--------------------|---------------|
| 1 | **Porcupine** | 0.1 | ~2.9% miss (97.1% det) @ 10 dB SNR | A |
| 2 | **openWakeWord** | <0.5 (design target) | <5% (design target) | C |
| 3 | **microWakeWord** (alexa, measured) | 64.7 | 57.5% FRR | D→B |
| 4 | **Howl** (production) | 4.0 | ~10% | B |

For **discrimination accuracy** on GSC V2 (P1):

| Rank | Model | GSC V2 Top-1 |
|------|-------|-------------|
| 1 | **BC-ResNet-8** | 98.7% |
| 2 | **BC-ResNet-1** | 98.0% |
| 3 | **MatchboxNet** | SOTA at publication |

For **language-independent, zero-shot** (SpeechAngel's constraint set):

| Rank | System | Result | #Params |
|------|--------|--------|---------|
| 1 | **ZP-KWS** | FRR@1%FAR reduced 60% vs strongest baseline | 1.55M |
| 2 | **PhonMatchNet** | 67-80% relative EER/AUC improvement on LibriPhrase | — |
| 3 | **sherpa-onnx KWS** | Open-vocabulary, tunable per keyword | 3.3M |

For **dysarthric / atypical speech**:

| Rank | System | FRR / FAR |
|------|--------|-----------|
| 1 | **PD-DWS** (LRDWWS'24 winner) | 0.5% / 0.32% |
| 2 | **DS-TCN** (LRDWWS'24 baseline) | 10.2% / 2.9% |
| 3 | **SpeechAngel WavLM** | 25% FRR @ 0.5 FA/hr |

---

## 7. Relevance matrix for SpeechAngel

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

---

## 8. Key architecture patterns that transfer to SpeechAngel

### 8.1 Shared backbone + lightweight heads (openWakeWord pattern)
Freeze a pre-trained embedding model (Google speech embed, DistilHuBERT, WavLM). Train per-wake-word classifiers on top. 15-20 models share one backbone. Matches SpeechAngel's multi-command architecture exactly.

### 8.2 Multiplicative speaker gating (ZP-KWS pattern)
Run a phoneme encoder + a speaker encoder in parallel. Multiply their outputs (late fusion) so that a wake word is only detected when *both* the correct phoneme sequence AND the enrolled speaker are present. Directly reduces FA/hr by rejecting impostor speakers.

### 8.3 Cascade / two-stage (Porcupine pattern)
Stage 1: cheap, aggressive detector (high recall, high FA). Stage 2: verifier (lower recall, very low FA). Only triggers that pass both fire. This is SpeechAngel's existing `WakeGatedRecognizer` architecture — just with a DTW Stage-1 instead of a neural one.

### 8.4 Synthetic training data (openWakeWord pattern)
Train entirely on TTS-generated speech + noise augmentation. Enables any wake word without recording real users. SpeechAngel can use this for bootstrapping before real user enrollment data exists.

### 8.5 VAD gating (universal pattern)
Pre-filter audio frames with energy-based or Silero VAD before running expensive KWS models. On ambient audio, 80-95% of frames are silence/noise — VAD rejects them at near-zero cost. SpeechAngel has `StreamingEnergyGate` but it's not calibrated.

---

## 9. Open questions (for SpeechAngel's roadmap)

1. **microWakeWord FA/hr remains unmeasured.** It is the closest match for SpeechAngel's platform (Apache 2.0, Android via Wyoming, Home Assistant proven). Needs a direct benchmark on LibriSpeech+DEMAND or DiPCo against openWakeWord and Porcupine.

2. **Can a phoneme-supervised encoder (ZP-KWS class) replace MFCC-DTW while keeping language independence?** 1.55M params is on-device feasible. The encoder needs a pronunciation lexicon per language, but the representation is language-agnostic.

3. **Does synthetic training (openWakeWord pattern) work for dysarthric speech?** TTS models are trained on typical speech. Dysarthric TTS is a research problem. SpeechAngel's on-device enrollment (real user recordings) is the differentiator here — synthetic bootstrapping may not close the atypical-speech gap.

4. **What is the FA/hr of a DistilHuBERT/WavLM-based cascade on real ambient audio?** SpeechAngel has measured FRR but not on raw continuous ambient — the E20 sim is the closest proxy.

5. **microWakeWord license lineage.** Original repo by @kahrendt is deleted. ESPHome fork is Apache 2.0. License provenance needs legal review.

---

## 10. Update log

| Date | Change |
|------|--------|
| 2026-07-08 | Initial comprehensive reference. Aggregates arXiv papers (MatchboxNet, BC-ResNet, ZP-KWS, MDTC, PD-DWS), production systems (Porcupine, openWakeWord, microWakeWord, Howl, sherpa-onnx), benchmarks (GSC, Hey Snips, Picovoice, DiPCo, LRDWWS). |
| 2026-07-08 | microWakeWord independently measured on Picovoice benchmark. alexa: 100% FRR @ ≤0.5 FA/hr, 57.5% FRR @ 64.7 FA/hr. jarvis: 100% FRR @ ≤0.5 FA/hr. No deployable operating point found. Script: `scripts/eval/bench_microWakeWord.py`. |
