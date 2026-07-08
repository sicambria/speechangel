# Domain 18: Transfer Learning & Foundation Models

**Goal:** Leverage pre-trained speech foundation models (SSL, ASR, multimodal) to bootstrap the SpeechAngel encoder, maximizing accuracy while minimizing training data requirements for dysarthric speech.

**Enabling OSS:** Hugging Face `transformers`, `s3prl` (Apache-2.0), `fairseq` (MIT), `espnet` (Apache-2.0).

---

## E18-01: Whisper encoder as frozen feature extractor
**Hypothesis:** OpenAI Whisper's encoder (trained on 680k hours of multilingual speech) produces high-quality frame-level features. Freezing the Whisper encoder and training only a small pooling+projection head for command discrimination may achieve strong dysarthric performance despite Whisper being ASR-trained (language-dependent).
**Score:** Impact=280 Feasibility=150 Constraints=140 Evidence=80 → **650 (B)**
**Description:** Extract frame-level features from `whisper-tiny.en` encoder (39M params, too large for on-device). Train a 100k-param pooling+projection head on TORGO. Measure rank-1. If promising, distill to 1-2M param student. Compare vs WavLM-distilled and from-scratch encoders.
**Expected outcome:** Whisper-tiny features + trained head achieve 65-70% rank-1. Better than from-scratch, slightly below WavLM-distilled. Whisper's multilingual training provides implicit language-independence.
**How to run:** Whisper feature extraction + head training + TORGO eval + optional distillation.

## E18-02: HuBERT-based iterative clustering for dysarthric units
**Hypothesis:** HuBERT's iterative clustering discovers acoustic units from unlabeled speech without any linguistic supervision. Running HuBERT-style clustering on a mix of typical + dysarthric speech may discover "dysarthria-aware" acoustic units that improve command discrimination.
**Score:** Impact=260 Feasibility=80 Constraints=150 Evidence=70 → **560 (B)**
**Description:** Apply HuBERT pretraining on TORGO + MSWC: (1) cluster MFCCs into K pseudo-labels, (2) train transformer to predict cluster IDs from masked input, (3) re-cluster transformer features, (4) repeat. Extract features from penultimate layer for command discrimination.
**Expected outcome:** HuBERT-dysarthric features achieve 60-65% rank-1. The unsupervised approach discovers acoustic units specific to this data mixture, potentially better for dysarthric than purely typical-speech-pretrained SSL models.
**How to run:** HuBERT-style pretraining + feature extraction + TORGO eval.

## E18-03: Data2Vec 2.0 speech teacher for dysarthric-aware distillation
**Hypothesis:** data2vec 2.0 (d2v2), used in PD-DWS, produces contextual representations by predicting latent representations from masked input. Training d2v2 on typical speech and fine-tuning on TORGO creates a dysarthric-aware teacher that can be distilled to a small student.
**Score:** Impact=300 Feasibility=100 Constraints=150 Evidence=85 → **635 (B)**
**Description:** Fine-tune `facebook/data2vec-audio-base` on TORGO with the masked-prediction objective. Use fine-tuned model as teacher for the 1-2M param student. Compare student rank-1 vs teacher-distilled-from-vanilla-d2v2 and vs from-scratch.
**Expected outcome:** Dysarthric-fine-tuned teacher → student improves rank-1 by 3-5pp vs vanilla-d2v2 teacher → student. The teacher's adaptation to dysarthric speech transfers through distillation.
**How to run:** d2v2 fine-tuning + distillation + TORGO eval.

## E18-04: Multilingual XLS-R distillation for language-agnostic embedding
**Hypothesis:** XLS-R (wav2vec2 trained on 128 languages) is the most language-diverse SSL model. Its embeddings are inherently language-agnostic. Distilling from XLS-R-300M to a 1-2M param student preserves language-independence better than English-only WavLM.
**Score:** Impact=300 Feasibility=100 Constraints=170 Evidence=80 → **650 (B)**
**Description:** Extract XLS-R-300M embeddings for TORGO + MSWC utterances. Distill to student via MSE loss. Test rank-1 on TORGO (English) and on non-English commands (from Common Voice). Compare cross-language rank-1 degradation vs WavLM-distilled student.
**Expected outcome:** XLS-R-distilled student: rank-1 63-68% on TORGO, <3pp drop on non-English. WavLM-distilled student: <5-8pp drop on non-English. XLS-R wins the language-independence criterion.
**How to run:** XLS-R embedding extraction + distillation + multilingual eval.

## E18-05: CLAP-style multimodal contrastive alignment
**Hypothesis:** CLAP (Contrastive Language-Audio Pretraining) aligns audio and text in a shared embedding space. Training a small audio encoder (student) to match CLAP audio embeddings enables zero-shot command recognition: the user types a command phrase, and the system matches against its text embedding without any audio enrollment.
**Score:** Impact=340 Feasibility=80 Constraints=120 Evidence=70 → **610 (B)**
**Description:** Train student audio encoder to predict CLAP audio embeddings from MFCC input. Enroll commands by computing CLAP text embedding of the command phrase. Match query audio embedding to text embeddings. This is **not** language-independent (requires text), but enables zero-shot mode.
**Expected outcome:** CLAP-based zero-shot mode achieves 50-60% rank-1 without enrollment. Not the primary mode, but a powerful optional capability for users who can type.
**How to run:** CLAP alignment training + text-embedding enrollment + zero-shot eval.
**Status:** Optional Path-A enhancement — breaks language-independence but adds zero-shot capability.

## E18-06: Self-supervised model soup (weight averaging)
**Hypothesis:** Averaging the weights of multiple fine-tuned copies of the same student model (each trained with different random seeds, data orders, or hyperparameters) produces a "model soup" that generalizes better than any single model — a proven technique from the vision domain that should transfer to speech.
**Score:** Impact=180 Feasibility=200 Constraints=180 Evidence=80 → **640 (B)**
**Description:** Train 5 student models with different seeds. Compute weight-average (uniform or greedy). Compare soup rank-1 vs best single model. Export soup model to ONNX.
**Expected outcome:** Model soup improves rank-1 by 1-3pp vs best single model, with zero inference cost increase. Pure accuracy gain from reduced overfitting variance.
**How to run:** Multi-seed training + weight averaging + soup eval.

## E18-07: Neural architecture search (NAS) for optimal encoder design
**Hypothesis:** Manual architecture design (ECAPA, Conformer, Mamba) may miss non-obvious architectures that are Pareto-optimal for accuracy-vs-latency. A lightweight NAS (e.g., DARTS, Once-for-All) can search the architecture space for the best on-device speech encoder.
**Score:** Impact=240 Feasibility=70 Constraints=170 Evidence=60 → **540 (C)**
**Description:** Define search space: kernel sizes (3,5,7), channel counts (32,64,128), layer counts (2,3,4), skip connection patterns. Run DARTS or evolutionary search with accuracy-latency reward. Train winning architecture on MSWC. Export to ONNX. Compare vs ECAPA-TDNN baseline.
**Expected outcome:** NAS-found architecture improves Pareto frontier by 5-10% (better accuracy at same latency, or same accuracy at lower latency). Architecture improvement is permanent — amortizes over all future deployments.
**How to run:** NAS search space + DARTS/evolution + winning architecture eval.
**Status:** Medium-term — NAS is compute-intensive but architecture gain is permanent.

## E18-08: Open-vocabulary embedding via MSWC (CC-BY-4.0, Apache-2.0 compatible)
**Hypothesis:** The Multilingual Spoken Word Corpus (MSWC, ~6000 hours, 50 languages, CC-BY-4.0) is the only large-scale multilingual command dataset with a permissive license. Contrastive training on MSWC produces embeddings that generalize across languages, words, and speakers — a foundation for truly language-independent command matching.
**Score:** Impact=320 Feasibility=100 Constraints=180 Evidence=80 → **680 (B)**
**Description:** Download MSWC (available on TensorFlow Datasets). Train contrastive encoder: same word across speakers/languages = positive. Evaluate: (a) TORGO rank-1 (English dysarthric, unseen words), (b) non-English command rank-1 from Common Voice keywords, (c) intra-word vs inter-word cosine separability.
**Expected outcome:** MSWC encoder achieves 63-67% rank-1 on TORGO (comparable to distilled encoders), with excellent cross-language generalization. This is the most constraint-preserving approach — trained on multilingual words, no phoneme dependency.
**How to run:** MSWC download + contrastive training + TORGO + multilingual eval.

## E18-09: Speech command foundation model benchmark (multi-task)
**Hypothesis:** A systematized benchmark comparing speech foundation models (WavLM, HuBERT, wav2vec2, XLS-R, Whisper, d2v2) on the speech-command-discrimination task reveals which model class is best for distillation, per the constraint-preservation criteria.
**Score:** Impact=220 Feasibility=180 Constraints=170 Evidence=80 → **650 (B)**
**Description:** Extract embeddings from 6 foundation models. For each, evaluate: (a) TORGO rank-1 (cosine prototype, 1-NN), (b) rank-1 on non-English commands, (c) rank-1-vs-model-size trade-off, (d) per-severity performance. Publish results as a "SpeechAngel Foundation Model Leaderboard."
**Expected outcome:** XLS-R wins language-independence. WavLM wins dysarthric accuracy. Whisper is competitive despite being ASR-trained. Quantified trade-offs inform the distillation target choice.
**How to run:** Multi-model embedding extraction + uniform eval protocol + leaderboard.

## E18-10: Parameter-efficient fine-tuning (LoRA, AdaLoRA) for on-device adaptation
**Hypothesis:** Low-Rank Adaptation (LoRA) — adding small trainable rank-decomposition matrices to frozen model weights — provides effective on-device fine-tuning with 99% fewer trainable parameters than full fine-tuning. A user can personalize the encoder with <200k extra params updated on-device.
**Score:** Impact=280 Feasibility=130 Constraints=170 Evidence=80 → **660 (B)**
**Description:** Apply LoRA to the encoder's attention and feed-forward layers. Train LoRA weights only on the user's enrolled templates. Compare rank-1 of LoRA-adapted vs frozen encoder vs full fine-tuning. Measure: (a) LoRA param count, (b) training time on-device, (c) accuracy gain per training step.
**Expected outcome:** LoRA achieves 70-85% of full fine-tuning gain with 1% of parameters. LoRA weights: 50-200k params per user. Training: 5-10 minutes on-device for 5 commands × 3 templates.
**How to run:** LoRA implementation in PyTorch → on-device training benchmark → TORGO eval.
