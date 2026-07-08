# Domain 07: On-Device Learned Encoders (QbE)

**Goal:** Distill a WavLM-class pooled-cosine encoder (71.9% rank-1) into a 1-2M param, on-device-runnable encoder that preserves language-independence + 1-shot enrollment and beats MFCC-DTW (55.4%) on dysarthric speech.

**Current baseline:** NoopQbeEncoder (dormant). CP-1 ceiling: WavLM-L12 pooled-cosine 71.9% rank-1 vs MFCC-DTW 55.4% (−37% rel error, McNemar p=2×10⁻⁶).

**Key insight from CP-1 2×2:** The lever is **QbE embedding + cosine**, not a front-end swap. WavLM-under-DTW ties MFCC; WavLM-under-pooled-cosine wins by 17pp. The target: a small model that preserves this interaction.

**Constraint gate (CP-1):** Any learned encoder must (a) be language-independent (no phoneme-dependency for the core), (b) support 1-shot enrollment (few-shot cosine prototype from 1-3 examples), (c) run on-device at <50ms per utterance, (d) be <5 MB on disk.

---

## E07-01: Embedding dimension sweep (32 vs 64 vs 128 vs 256 vs 512 vs 768)
**Hypothesis:** WavLM-L12's 768-dim embeddings are overkill for speaker-dependent command discrimination. A much smaller embedding (64-128 dim) preserves most of the discriminative power while being 6-12× cheaper for cosine prototype matching.
**Description:** Take WavLM-L12 embeddings, apply PCA to reduce to 32/64/128/256/512 dimensions. Measure rank-1 at each reduced dimension. Find the knee of the curve.
**Expected outcome:** Rank-1 plateaus at 128-256 dimensions. 128-dim preserves >95% of 768-dim rank-1. Below 64 dim, performance drops sharply.
**Win condition:** Identify the minimum dimension that preserves ≥95% of full-dim rank-1.
**How to run:** PCA on WavLM embeddings from CP-1 spike harness, rank-1 sweep.
**Status:** [ ] planned

## E07-02: WavLM layer selection (which transformer layer is best?)
**Hypothesis:** Different transformer layers encode different levels of acoustic abstraction. For dysarthric speech, middle layers (6-8) that encode phonetic-like information without full word-level abstraction may be better for language-independent command matching than final layers (11-12).
**Description:** Extract embeddings from WavLM layers 1/3/6/9/12. Compare rank-1 with mean-pooled cosine at each layer. Test on dysarthric vs control separately.
**Expected outcome:** Layer 6-9 gives best dysarthric rank-1 (phonetic-like features). Layer 12 gives best control rank-1 (word-level features). For deployment, layer 6 or 9 is the best compromise.
**Win condition:** Identify the optimal layer; if layer 6 beats layer 12 on dysarthric by ≥3pp, that enables a shallower student model.
**How to run:** Layer-wise embeddings from CP-1 spike harness.
**Status:** [ ] planned

## E07-03: Student architecture bake-off (CNN vs Transformer vs Conformer vs Mamba)
**Hypothesis:** Different student architectures have different efficiency-discrimination trade-offs. A small CNN (TDNN/ECAPA-lite) may match a 1M-param transformer for speaker-dependent embedding at lower latency. Mamba (SSM) is a wildcard with linear-time sequence modeling.
**Description:** Train 4 student architectures to mimic WavLM-L9 embeddings: (a) 3-layer TDNN/ECAPA-TDNN, (b) 2-layer Conformer (convolution + attention), (c) 4-layer lightweight Transformer, (d) Mamba SSM block. All ~1-2M params. Compare rank-1 on TORGO, latency on Android, model size.
**Expected outcome:** ECAPA-TDNN gives best accuracy-vs-latency trade-off for speaker-dependent tasks. Conformer is the accuracy ceiling at higher cost. Mamba is the latency-efficiency ceiling.
**Win condition:** Student rank-1 ≥65% on TORGO (midpoint between MFCC-DTW 55.4% and WavLM 71.9%) at <50ms inference.
**How to run:** PyTorch training pipeline → ONNX export → Android benchmark.
**Status:** [ ] planned

## E07-04: Multi-task training (discriminative + reconstructive loss)
**Hypothesis:** Training the encoder with both a discriminative loss (contrastive: pull same-command embeddings together, push different-command apart) and a reconstructive loss (predict MFCC features from embedding) will produce embeddings that capture both command identity and acoustic detail, improving few-shot generalization.
**Description:** Joint loss: L = L_contrastive (NT-Xent / SupCon) + λ * L_reconstruction (MSE between decoder output and input MFCC). Sweep λ. Compare single-task vs multi-task embeddings on TORGO 1-shot enrollment.
**Expected outcome:** Multi-task embeddings give 3-5pp higher rank-1 at 1-shot enrollment than contrastive-only, because the reconstruction loss preserves acoustic detail needed for fine-grained similarity.
**Win condition:** ≥3pp rank-1 gain at 1-shot enrollment vs single-task baseline.
**How to run:** Multi-task training pipeline, TORGO eval.
**Status:** [ ] planned

## E07-05: Knowledge distillation (WavLM teacher → small student)
**Hypothesis:** Direct distillation (MSE between student and teacher embeddings) transfers WavLM's representation quality more efficiently than training from scratch, especially with limited dysarthric training data.
**Description:** Train student model to minimize MSE(embedding_student, embedding_WavLM_L9) on MSWC (multilingual spoken words) + Google Speech Commands v2. Compare rank-1 of distilled student vs same architecture trained from scratch with contrastive loss.
**Expected outcome:** Distilled student reaches 3-5pp higher rank-1 than from-scratch student at the same architecture, because the WavLM teacher provides richer supervision than a binary same/different contrastive signal.
**Win condition:** Distilled student rank-1 ≥ from-scratch student + 3pp.
**How to run:** Distillation training pipeline (teacher forward pass → student loss), TORGO eval.
**Status:** [ ] planned

## E07-06: Phoneme-supervised pretraining (ZP-KWS style)
**Hypothesis:** Phoneme-supervised pretraining (predict phoneme labels from speech, learn phoneme-discriminative features) produces language-agnostic embeddings that outperform pure SSL features for command discrimination, because phoneme boundaries are universal acoustic landmarks. This is the ZP-KWS approach (arXiv 2606.20106).
**Description:** Pretrain encoder on multilingual phoneme recognition (CommonVoice + LibriSpeech) with a frame-level phoneme classifier. Use the penultimate layer as the embedding. Compare phoneme-supervised vs SSL (WavLM/whisper-encoder) rank-1 on TORGO.
**Expected outcome:** Phoneme-supervised embeddings match or slightly exceed SSL embeddings for command discrimination (phonemes are the right level of abstraction for "are these the same word?"), with much smaller model size (1-2M params directly, no distillation).
**Win condition:** Rank-1 ≥ WavLM-distilled student at same param count.
**How to run:** Phoneme recognizer training → embedding extraction → TORGO eval.
**Status:** [ ] planned

## E07-07: Prototype selection strategies (mean vs median vs attention-weighted)
**Hypothesis:** The simple mean prototype (average of enrolled embeddings) is sensitive to outlier enrollments. Median or attention-weighted prototypes (learn per-sample weights based on quality) will produce more robust templates.
**Description:** Compare prototype strategies on TORGO 1/3/5-shot enrollment: (a) mean, (b) median (per-dimension), (c) distance-weighted mean (weight = 1/distance_to_others), (d) learnable attention weights. Measure rank-1.
**Expected outcome:** Distance-weighted mean gives best 1-shot robustness (attenuates outlier effect). Mean ties with more shots. Attention weights overfit with ≤3 shots.
**Win condition:** ≥2pp rank-1 gain at 1-shot vs simple mean prototype.
**How to run:** Prototype strategies in QbeSpeechBackend, TORGO eval.
**Status:** [ ] planned

## E07-08: Embedding + DTW fusion (dual-path matcher)
**Hypothesis:** The cosine distance between prototype embeddings captures global shape similarity; DTW on MFCC captures temporal alignment. A simple score fusion (weighted sum of normalized scores) outperforms either alone — this is the natural endpoint of the CP-1 2×2 finding that the interaction drives the gain.
**Description:** Compute: (a) cosine distance to QbE prototype, (b) normalized DTW distance to nearest MFCC template. Fuse with learnable or tuned weight α. Compare rank-1 vs single-matcher baselines. Pre-register α=0.6 (slight DTW preference for temporal precision).
**Expected outcome:** Fusion beats both single-matcher baselines by 3-5pp rank-1. The matchers are complementary — QbE captures global shape, DTW captures local alignment.
**Win condition:** ≥3pp rank-1 gain over best single matcher.
**How to run:** Fused matcher combining QbeSpeechBackend + TemplateMatcher scores.
**Status:** [ ] planned

## E07-09: On-device latency benchmark (student model inference time)
**Hypothesis:** A 1-2M param encoder should run in <30ms on a modern Android phone CPU (4 threads, ONNX Runtime or TFLite). Above 50ms, it's not viable for Stage-2 (which has an ~1500ms window but must process within a frame step).
**Description:** Export student model to ONNX/TFLite. Benchmark on Android emulator and physical device. Measure: (a) single-utterance inference time (cold/warm start), (b) memory usage, (c) APK size impact. Sweep thread counts (1/2/4/8).
**Expected outcome:** 2M-param CNN: ~10-20ms warm inference. 2M-param Conformer: ~20-40ms. 2M-param Transformer: ~30-60ms. All viable for Stage-2.
**Win condition:** ≤50ms warm inference on a mid-range (Snapdragon 7-series equivalent) device.
**How to run:** Android benchmark harness with ONNX/TFLite, on-device profiling.
**Status:** [ ] planned

## E07-10: Language-independence validation (multilingual command set)
**Hypothesis:** A learned encoder trained only on English data may embed non-English commands poorly (out-of-distribution acoustics), undermining the language-independence claim. Testing on non-English commands is the gate for CP-1.
**Description:** Test the student encoder on commands from 5+ languages (via Common Voice keyword data or a custom multilingual command recording). Compare rank-1 for English vs non-English. Test whether the phoneme-supervised encoder (E07-06) generalizes better than the pure-SSL distilled encoder.
**Expected outcome:** Phoneme-supervised encoder generalizes well (>90% of English rank-1 on non-English). Pure-SSL distilled encoder may drop 10-20% on non-English. This is the language-independence gate.
**Win condition:** Non-English rank-1 ≥90% of English rank-1 = language-independent. <80% = fails the gate, encoder must be retrained on multilingual data.
**How to run:** Multilingual TORGO-like corpus or Common Voice keywords, rank-1 comparison.
**Status:** [ ] planned
