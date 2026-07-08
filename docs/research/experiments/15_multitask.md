# Domain 15: Multi-Task & Multi-Modal Learning

**Goal:** Leverage auxiliary tasks (speaker ID, emotion, phoneme recognition, VAD, SNR estimation) to improve the primary command-discrimination task through shared representations.

**Enabling OSS:** PyTorch Lightning (Apache-2.0); Hugging Face `transformers`.

---

## E15-01: Joint command+speaker embedding (dual-head encoder)
**Hypothesis:** Training the encoder with both command-discrimination and speaker-identification heads forces the embedding to disentangle "what was said" from "who said it." The command-discriminative subspace is cleaner and more robust to voice changes.
**Score:** Impact=280 Feasibility=140 Constraints=170 Evidence=80 → **670 (B)**
**Description:** Add a speaker-ID head to the encoder architecture. Train jointly: L = L_contrastive(command) + λ·L_crossentropy(speaker). Use gradient reversal layer (GRL) on the speaker head to encourage command-specific features. Compare rank-1 on within-speaker vs cross-condition commands.
**Expected outcome:** 3-5pp rank-1 gain on cross-condition (tired vs normal voice) queries. The disentangled representation is more robust to voice drift.
**How to run:** Dual-head encoder training + condition-stratified eval.

## E15-02: Auxiliary VAD task for frame-level speech detection
**Hypothesis:** Adding a per-frame VAD (speech/non-speech) prediction head to the encoder during training produces embeddings that are inherently robust to silence and noise frames — the encoder learns to ignore non-speech without needing explicit VAD trimming.
**Score:** Impact=220 Feasibility=170 Constraints=190 Evidence=70 → **650 (B)**
**Description:** Add a frame-level binary classifier (speech/non-speech) to intermediate encoder layers. Train with labeled VAD frames from TORGO. At inference, use only the command-discrimination head. Compare rank-1 with and without VAD trimming on noisy input.
**Expected outcome:** 2-4pp rank-1 gain on noisy input where VAD trimming is imperfect. The VAD head regularizes the encoder to speech-relevant features.
**How to run:** VAD-supervised encoder training + noise-condition eval.

## E15-03: SNR estimation as auxiliary task
**Hypothesis:** Adding an SNR estimation head forces the encoder to be aware of signal quality. This auxiliary task improves robustness because the encoder learns to discount noise-dominated frequency regions without explicit noise reduction.
**Score:** Impact=200 Feasibility=160 Constraints=190 Evidence=60 → **610 (B)**
**Description:** Add SNR regression head (predict SNR in dB). Train on MUAN-mixed data with known SNRs. Use SNR prediction to weight per-frame contribution to the utterance embedding (low-SNR frames → lower weight). Compare vs baseline encoder on noisy data.
**Expected outcome:** 2-3pp rank-1 gain at SNR≤10 dB. SNR-weighted frame aggregation is the key mechanism.
**How to run:** SNR-supervised training + SNR-weighted pooling + noise-condition eval.

## E15-04: Phoneme boundary detection for dysarthric alignment
**Hypothesis:** Phoneme boundaries are more stable acoustic landmarks than arbitrary frame boundaries in dysarthric speech. Training an encoder to predict phoneme boundaries (via forced alignment on typical speech) creates features that align better across dysarthric utterances.
**Score:** Impact=260 Feasibility=100 Constraints=160 Evidence=70 → **590 (B)**
**Description:** Train encoder with auxiliary phoneme-boundary prediction head (binary: is this frame a phoneme boundary?) on typical speech with forced-alignment labels. Fine-tune on dysarthric speech. Compare DTW alignment quality (path smoothness, rank-1).
**Expected outcome:** 2-4pp rank-1 gain. Phoneme-boundary-aware features produce smoother, more physically-plausible DTW alignment paths.
**How to run:** Forced alignment + phoneme-boundary training + alignment quality eval.

## E15-05: Dysarthria severity classification as auxiliary task
**Hypothesis:** Training the encoder to predict dysarthria severity (mild/moderate/severe) from the utterance embedding creates a severity-aware representation. The severity prediction can be used to select the appropriate pipeline configuration (severity-adaptive, E06-10).
**Score:** Impact=240 Feasibility=130 Constraints=180 Evidence=60 → **610 (B)**
**Description:** Add severity classification head (3-class) trained on TORGO severity labels. At inference: (a) use severity prediction to select pipeline, (b) use severity-conditional thresholds. Compare rank-1 vs uniform pipeline.
**Expected outcome:** 3-6pp rank-1 gain on mixed-severity population. Severity prediction AUC >0.85. Enables the E06-10 severity-adaptive pipeline.
**How to run:** Severity-supervised training + adaptive pipeline eval.

## E15-06: Contrastive predictive coding (CPC) for speech representation
**Hypothesis:** CPC (predicting future latent representations from past context) learns representations that capture slow-varying speech dynamics (formants, prosody) while ignoring fast-varying noise. CPC-pretrained encoders should produce more robust embeddings for DTW matching.
**Score:** Impact=260 Feasibility=120 Constraints=170 Evidence=80 → **630 (B)**
**Description:** Pretrain encoder with CPC loss on MSWC: encode past frames, predict future latent representations, contrast with negative samples from other utterances. Fine-tune with command-discrimination loss. Compare rank-1 vs purely-discriminative encoder.
**Expected outcome:** 3-5pp rank-1 gain. CPC captures the temporal structure of speech better than pure contrastive objectives — this benefits DTW which relies on temporal alignment.
**How to run:** CPC pretraining + discriminative fine-tuning + TORGO eval.

## E15-07: Wav2Vec2-style masked feature prediction pretraining
**Hypothesis:** Wav2Vec2's masked feature prediction pretraining (mask random frames, predict the quantized representations) is the SOTA approach for general speech representations. Fine-tuning a wav2vec2-base model on command discrimination should give strong results as a ceiling.
**Score:** Impact=300 Feasibility=120 Constraints=130 Evidence=90 → **640 (B)**
**Description:** Fine-tune `facebook/wav2vec2-base` (95M params, too large for on-device) on command discrimination as a ceiling measurement. Then distill to 1-2M param student. Compare rank-1.
**Expected outcome:** Wav2Vec2 fine-tuned: 75-80% rank-1 on TORGO (approaches WavLM-L12). Distilled student: 65-70%. The distillation gap (5-10pp) is the cost of on-device constraints.
**How to run:** Wav2Vec2 fine-tuning + distillation + TORGO eval.

## E15-08: Multimodal enrollment (audio + visual lip reading)
**Hypothesis:** For users who can position the phone to see their face, visual lip-reading features (from the front camera) provide complementary information to audio. Fusing audio and visual embeddings during enrollment improves discrimination, especially in noise.
**Score:** Impact=220 Feasibility=50 Constraints=100 Evidence=50 → **420 (C)**
**Description:** Use a lightweight lip-reading model (e.g., LipNet-lite) to extract visual features during enrollment. Concatenate with audio embedding. Match queries with audio+visual prototype. Compare rank-1 vs audio-only on noisy data.
**Expected outcome:** 5-10pp rank-1 gain in noise (SNR<5dB) where audio is degraded. Marginal gain in quiet. Camera availability is the gating UX constraint.
**How to run:** Visual feature extraction + audiovisual fusion + noise-condition eval.
**Status:** Long-term research — blocked on camera access and UX viability.

## E15-09: Wake word + command joint optimization (shared encoder)
**Hypothesis:** Training the encoder jointly for wake-word detection and command recognition, with a shared backbone and separate heads, produces a representation that serves both stages — enabling embedding-based wake gating and command matching from a single encoder.
**Score:** Impact=280 Feasibility=130 Constraints=170 Evidence=60 → **640 (B)**
**Description:** Train encoder with two heads: (1) wake/no-wake binary classifier, (2) command-discrimination contrastive head. At inference: Stage-1 uses wake head (fast binary decision), Stage-2 uses embedding prototype matching (finer discrimination). Compare Stage-1 wake detection vs separate wake gate.
**Expected outcome:** Shared encoder: 3-5pp better wake detection than MFCC-DTW wake word at matched FA/hr. Unifies the stack — one encoder, two operating modes.
**How to run:** Joint wake+command training + two-mode eval.

## E15-10: Command intent clustering (unsupervised discovery)
**Hypothesis:** In always-on operation, the system hears many utterances. Unsupervised clustering of query embeddings can discover new "potential commands" that the user frequently says but hasn't enrolled — suggesting them for enrollment without explicit labeling.
**Score:** Impact=180 Feasibility=160 Constraints=180 Evidence=50 → **570 (B)**
**Description:** Run online clustering (e.g., DBSCAN or streaming k-means) on query embeddings over days of use. When a cluster exceeds a threshold density and is acoustically distinct from enrolled commands, suggest: "You often say something like this. Would you like to make it a command?"
**Expected outcome:** 2-5 new commands discovered per week of use without explicit user intent. Delight feature, not accuracy-critical.
**How to run:** Online clustering + suggestion UX + user-acceptance measurement.
