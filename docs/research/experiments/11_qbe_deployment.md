# Domain 11: QbE & Neural Embedding — Deployment Pipeline

**Goal:** Operationalize the dormant `QbeEncoder` seam with a 1-2M param encoder that beats MFCC-DTW on dysarthric speech while preserving language-independence + 1-shot + on-device constraints.

**Ceiling:** WavLM-L12 pooled-cosine 71.9% rank-1 vs MFCC-DTW 59.2% (−32% rel error). Target: 65%+ rank-1 at <50ms/utt.

**Enabling OSS:** sherpa-onnx (Apache-2.0) for Android ONNX runtime integration; Hugging Face `transformers` for model training; ONNX Runtime for inference.

---

## E11-01: sherpa-onnx Android KWS integration as Path-A baseline
**Hypothesis:** sherpa-onnx's pre-built Android KWS module (Apache-2.0, keywords from text file, no re-training) provides an immediate Path-A reference point for language-dependent performance on TORGO, establishing the upper ceiling for language-dependent approaches.
**Score:** Impact=250 Feasibility=280 Constraints=150 Evidence=90 → **770 (A)**
**Description:** Integrate `sherpa-onnx` KWS Android library, supply TORGO commands as keyword text file, evaluate rank-1 and FRR/FAR on dysarthric speakers. Compare against MFCC-DTW baseline.
**Expected outcome:** sherpa-onnx scores 30-45% rank-1 on dysarthric (better than MFCC-DTW on mild, worse on severe, language-dependent). Establishes the "what you lose by being language-independent" bound.
**How to run:** Add sherpa-onnx Gradle dep to `:data`, implement `PathABackend`, TORGO eval.

## E11-02: ECAPA-TDNN student distillation from WavLM-L9
**Hypothesis:** A 1.2M-param ECAPA-TDNN student (1D conv + SE-Res2Blocks + attentional statistics pooling) distilled from WavLM-L9 via MSE loss on MSWC + Google Speech Commands v2 will match ≥85% of WavLM's TORGO rank-1 at 1/80th the parameter count, making it on-device-viable.
**Score:** Impact=340 Feasibility=100 Constraints=160 Evidence=85 → **685 (B)**
**Description:** Implement ECAPA-TDNN in PyTorch. Distill from WavLM-L9 on 50k+ multilingual utterances. Export to ONNX → TFLite. Benchmark rank-1 on TORGO, latency on Android emulator.
**Expected outcome:** ECAPA-TDNN achieves 63-67% rank-1 on TORGO (midway between MFCC-DTW 59% and WavLM 72%), inference <25ms/utt, <3MB on disk.
**How to run:** Python training pipeline + ONNX export + Android benchmark harness + TorgoEval.

## E11-03: Phoneme-supervised ZP-KWS encoder from scratch
**Hypothesis:** Training a 1.5M-param phoneme-supervised encoder (ZP-KWS architecture: 4-layer CNN + 2-layer Transformer + phoneme classifier head) on multilingual phoneme data produces language-agnostic embeddings that match or exceed distilled WavLM for command discrimination on dysarthric speech.
**Score:** Impact=350 Feasibility=80 Constraints=170 Evidence=95 → **695 (B)**
**Description:** Implement ZP-KWS per arXiv 2606.20106. Train phoneme classifier on CommonVoice + LibriSpeech (multilingual). Use penultimate layer as embedding. Add optional speaker-verification branch (GE2E-pretrained). Export to ONNX. Compare rank-1 vs distilled ECAPA-TDNN vs MFCC-DTW.
**Expected outcome:** ZP-KWS matches ECAPA-TDNN rank-1 with better language-independence (trained on phonemes, not words). Speaker verification branch reduces FA from unrelated speakers by 50-70%.
**How to run:** ZP-KWS PyTorch impl → phoneme training → ONNX export → TORGO eval.

## E11-04: Mamba SSM speech encoder (linear-time alternative)
**Hypothesis:** A Mamba (State Space Model) encoder with linear-time sequence processing achieves comparable embedding quality to a Transformer at lower latency, making it ideal for on-device deployment where O(n²) attention is prohibitive.
**Score:** Impact=280 Feasibility=90 Constraints=170 Evidence=60 → **600 (B)**
**Description:** Implement Mamba speech encoder (1D conv frontend → Mamba blocks → mean pooling). Train contrastively on MSWC. Compare rank-1 and latency vs ECAPA-TDNN and Transformer baselines.
**Expected outcome:** Mamba matches Transformer rank-1 at 2-3× lower latency, slightly behind ECAPA-TDNN in accuracy but better for longer utterances.
**How to run:** Mamba PyTorch impl → contrastive training → ONNX export → TORGO eval + benchmark.

## E11-05: Streaming-friendly causal encoder (no future context)
**Hypothesis:** Current encoders use bidirectional/full-sequence context — unsuitable for streaming (Stage-1 wake). A causal (left-context-only) encoder with similar architecture but unidirectional attention enables streaming embedding extraction with minimal accuracy loss.
**Score:** Impact=240 Feasibility=120 Constraints=180 Evidence=60 → **600 (B)**
**Description:** Train causal variant of the best student encoder. Measure streaming embedding quality (per-frame vs full-utterance) and latency. Compare rank-1 for streaming vs full-sequence mode.
**Expected outcome:** Causal encoder ranks 3-5pp below full-sequence on full utterances, but enables Stage-1 embedding-based wake gating — worth the trade-off for the always-on path.
**How to run:** Causal encoder training + streaming eval harness.

## E11-06: Quantization-aware training (INT8) for Android NPU deployment
**Hypothesis:** INT8 quantization of the encoder (via QAT or post-training quantization) reduces model size 4× and latency 2-3× on Android NN API / Qualcomm Hexagon NPU with ≤1pp accuracy loss, making the encoder viable on low-end devices.
**Score:** Impact=220 Feasibility=130 Constraints=190 Evidence=80 → **620 (B)**
**Description:** Apply QAT during encoder training or PTQ on the frozen model. Export to TFLite INT8. Benchmark latency and accuracy on Android emulator with NN API delegate. Compare FP32 vs INT8.
**Expected outcome:** INT8 model: <10ms inference, <1MB on disk, ≤1pp rank-1 loss. Unlocks deployment on Android Go devices.
**How to run:** PyTorch QAT → TFLite INT8 export → Android benchmark.

## E11-07: Embedding cache with incremental update (template-aware)
**Hypothesis:** When a new template is enrolled, recomputing all stored embeddings is wasteful. An embedding cache that stores per-template embeddings and only recomputes the new template's embedding, then updates the prototype incrementally, reduces enrollment latency by 80%.
**Score:** Impact=160 Feasibility=250 Constraints=200 Evidence=70 → **680 (B)**
**Description:** Implement embedding cache in QbeSpeechBackend. On new enrollment: compute embedding for new template, update prototype as running weighted average. On query: cache hit rate >95% (prototype is precomputed).
**Expected outcome:** Enrollment latency drops from O(N_templates) to O(1) per new template. Stage-2 recognition unchanged (prototype is precomputed).
**How to run:** Embedding cache + prototype update logic in core:enrollment.

## E11-08: MFCC+Embedding joint feature space alignment
**Hypothesis:** MFCC features and learned embeddings inhabit different metric spaces. Training a small projection network that maps MFCC features to the embedding space (and vice versa) enables hybrid matching where a DTW path found in MFCC space is scored in embedding space, combining DTW's alignment with embedding's discrimination.
**Score:** Impact=260 Feasibility=140 Constraints=160 Evidence=60 → **620 (B)**
**Description:** Train an MLP projector (MFCC→embedding_dim) using triplet loss (MFCC, positive embedding, negative embedding). At inference: extract MFCC, project to embedding space, compute cosine prototype. Alternatively: find DTW path in MFCC space, accumulate cosine distances in embedding space along that path.
**Expected outcome:** Hybrid matching achieves 2-4pp gain over pure MFCC-DTW and 1-2pp gain over pure embedding-cosine — combines the best of both.
**How to run:** Projector training + hybrid matcher in core:matching.

## E11-09: Self-supervised pretraining on user's own unlabeled audio
**Hint:** In deployment, the always-on mic captures hours of the user's own speech (including ambient, partial commands, conversation). Self-supervised pretraining on this in-domain, speaker-specific audio (BYOL-A / SimCLR style) could fine-tune the encoder to the user's acoustic characteristics without any labels.
**Score:** Impact=300 Feasibility=80 Constraints=140 Evidence=70 → **590 (B)**
**Description:** Collect 1-5 hours of always-on audio from a single speaker. Apply SimCLR-style contrastive learning (augmentations: noise, pitch, time-stretch, reverb) to fine-tune the pretrained encoder. Measure rank-1 improvement on that speaker's commands vs frozen encoder.
**Expected outcome:** 5-10pp rank-1 gain for the adapted speaker. Adaptation takes ~30 min on-device (background, low-priority). Privacy-preserving (stays on device).
**How to run:** On-device SSL loop + encoder fine-tuning + per-speaker eval.

## E11-10: Open-vocabulary embedding via multilingual MSWC pretraining
**Hypothesis:** Training the encoder on the Multilingual Spoken Word Corpus (MSWC, 50+ languages, CC-BY-4.0) with a contrastive objective (same word = positive, different word = negative) produces embeddings that generalize across languages and words, truly achieving language-independence.
**Score:** Impact=320 Feasibility=90 Constraints=170 Evidence=80 → **660 (B)**
**Description:** Download MSWC (~6000h, 50 langs). Train contrastive encoder (NT-Xent loss: same word across speakers/lang = positive). Evaluate rank-1 on TORGO (English dysarthric — unseen during training). Test on non-English commands for language-independence.
**Expected outcome:** MSWC-pretrained encoder achieves 65-70% rank-1 on TORGO, with <5pp drop on non-English commands. Truly language-independent by construction.
**How to run:** MSWC download + contrastive training + TORGO + multilingual eval.
