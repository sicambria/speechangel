# Domain 13: Data Augmentation & Synthetic Dysarthric Training

**Goal:** Generate realistic dysarthric speech data for training encoders and calibrating thresholds, addressing the critical data scarcity for impaired speech.

**Enabling OSS:** Coqui TTS / Piper TTS (MIT, Apache-2.0) for TTS-based augmentation; MUSAN (various licenses) for noise; OpenSLR RIRs (Apache-2.0) for reverb; Audiomentations (MIT) for audio transforms.

---

## E13-01: TTS-dysarthric augmentation (PD-DWS technique)
**Hypothesis:** Text-to-speech synthesis of dysarthric command utterances — by manipulating TTS rate, pitch, and spectral tilt to mimic dysarthric characteristics — creates realistic training data that improves encoder robustness to dysarthric speech. This is the technique that helped PD-DWS win LRDWWS'24 (FAR 0.32%/FRR 0.5%).
**Score:** Impact=340 Feasibility=150 Constraints=180 Evidence=90 → **760 (A)**
**Description:** Use Piper TTS (Apache-2.0, on-device compatible) or a Python TTS pipeline to synthesize each TORGO command with dysarthric-style distortions: (a) slowed rate 0.5-0.8×, (b) pitch monotonicity (reduce F0 variance), (c) reduced spectral contrast (compress formant amplitudes), (d) breathiness (add filtered noise). Mix real + synthetic data for encoder training.
**Expected outcome:** Encoders trained with TTS-dysarthric augmentation improve rank-1 by 5-10pp on real dysarthric speakers vs encoders trained on typical speech only.
**How to run:** TTS synthesis pipeline + mixed training + TORGO eval.

## E13-02: Voice conversion for dysarthric speaker augmentation
**Hypothesis:** Using voice conversion to transform typical-speech command recordings into "dysarthric-sounding" versions (preserving content, changing speaker characteristics) generates paired (clean, dysarthric) training data that helps the encoder learn speaker-invariant command representations.
**Score:** Impact=280 Feasibility=100 Constraints=170 Evidence=70 → **620 (B)**
**Description:** Train a voice conversion model (e.g., StarGAN-VC, FreeVC) on TORGO to map control→dysarthric voice. Apply to Google Speech Commands v2 to create "pseudo-dysarthric" training data (content from GSCv2, voice from TORGO dysarthric speakers). Train encoder on this data.
**Expected outcome:** 3-5pp rank-1 gain on real dysarthric speakers. The encoder learns to ignore voice characteristics and focus on command content.
**How to run:** Voice conversion training + pseudo-dysarthric data generation + encoder training.

## E13-03: CycleGAN-based dysarthric–control domain translation
**Hypothesis:** A CycleGAN trained to translate between dysarthric and control speech spectrograms can augment the limited real dysarthric data by generating plausible dysarthric variants of control utterances, providing a rich data source for encoder pretraining.
**Score:** Impact=260 Feasibility=90 Constraints=170 Evidence=60 → **580 (B)**
**Description:** Train CycleGAN (or DiffVC/DiffSVC) on paired TORGO control+dysarthric speaker spectrograms. Generate dysarthric-augmented versions of MSWC utterances. Train encoder on real + cycleGAN-augmented data.
**Expected outcome:** 4-8pp rank-1 gain. CycleGAN augmentation is more realistic than parameter-based TTS augmentation but requires careful training to avoid artifacts.
**How to run:** CycleGAN training + spectrogram-to-audio + augmented encoder training.

## E13-04: SpecAugment for speech (time/frequency masking)
**Hypothesis:** SpecAugment (random time masking, frequency masking, time warping applied to mel spectrograms during training) acts as a powerful regularizer for speech encoders, improving robustness to dysarthric variability without requiring real dysarthric data.
**Score:** Impact=240 Feasibility=260 Constraints=190 Evidence=90 → **780 (A)**
**Description:** During encoder training, apply SpecAugment: (a) time masking: zero out 0-10 consecutive time frames, (b) frequency masking: zero out 0-5 mel bands, (c) time warping: random piecewise linear time scaling. Train with and without SpecAugment. Compare rank-1 on TORGO.
**Expected outcome:** SpecAugment improves rank-1 by 3-5pp on dysarthric, especially for encoders trained on typical speech. Acts as a cheap proxy for the temporal/spectral variability of dysarthric speech.
**How to run:** SpecAugment layer in encoder training pipeline.

## E13-05: Adversarial noise injection for FAR-budget calibration
**Hypothesis:** Instead of random noise, adversarially-selected noise clips (from MUSAN) that cause the highest false DTW matches can be used to "vaccinate" the threshold calibrator — training it on the hardest negatives produces thresholds that generalize better to real ambient.
**Score:** Impact=250 Feasibility=180 Constraints=200 Evidence=60 → **690 (B)**
**Description:** From a large MUSAN noise bank, select clips that produce DTW distances below various thresholds to enrolled templates (i.e., "hard negatives"). Use these as calibration negatives. Compare held-out FAR of adversarially-calibrated vs randomly-calibrated thresholds.
**Expected outcome:** Adversarial calibration reduces held-out FAR by 20-40% at matched FRR by finding thresholds that are robust to the most deceptive noise patterns.
**How to run:** Adversarial noise selection + ThresholdCalibrator with hard negatives.

## E13-06: Acoustic room simulator (pyroomacoustics integration)
**Hypothesis:** pyroomacoustics (MIT, Python) provides physically-realistic room simulation (geometry-based RIRs, multi-source, moving sources) that is more realistic than static RIR convolution, enabling better far-field robustness training.
**Score:** Impact=220 Feasibility=160 Constraints=200 Evidence=70 → **650 (B)**
**Description:** Use pyroomacoustics to simulate 10-20 room configurations (small office, living room, kitchen, hallway, outdoor with echo) with moving speaker positions. Convolve TORGO + MSWC with simulated RIRs. Train encoder on room-augmented data.
**Expected outcome:** Room-sim-augmented training improves far-field FRR by 10-15% rel vs clean-only training by creating a more realistic reverberation prior.
**How to run:** pyroomacoustics simulation + RIR generation + augmented training.

## E13-07: Background babble augmentation (multi-speaker mixing)
**Hypothesis:** Mixing target speech with multi-speaker babble (from LibriSpeech or CommonVoice) simulates the most challenging real-world condition. Babble-augmented training teaches the encoder to separate command identity from interfering speech.
**Score:** Impact=280 Feasibility=200 Constraints=200 Evidence=80 → **760 (A)**
**Description:** Mix TORGO/MSWC utterances with 2-5 overlapping speaker streams at SNR 0-15 dB. Create "babblified" training pairs. Train encoder with contrastive loss where the positive is the same command with different babble, negative is different command. Measure babble-robustness.
**Expected outcome:** Babble-augmented training improves babble-condition rank-1 by 10-20pp. This is the hardest condition and the one where real deployment fails most.
**How to run:** Multi-speaker mixing + babble-augmented training + babble-condition eval.

## E13-08: Pitch-shifted enrollment augmentation for voice condition coverage
**Hypothesis:** Systematic pitch shifting (±100 cents in 25-cent steps) during enrollment creates templates covering the full pitch range a user might produce across conditions (tired → lower pitch, stressed → higher pitch), improving condition-robustness without requiring multi-session recordings.
**Score:** Impact=260 Feasibility=260 Constraints=200 Evidence=80 → **800 (A)**
**Description:** For each enrolled template, generate 8 pitch-shifted variants at ±25/50/75/100 cents. Compare rank-1 with and without pitch-augmented enrollment, stratified by the pitch deviation between enrollment and query.
**Expected outcome:** Pitch-augmented enrollment improves rank-1 by 5-8pp for speakers with high pitch variability and neutral for consistent-pitch speakers. Nearly-free accuracy gain (augmentation cost is trivial).
**How to run:** Pitch-shift AudioAugment + multi-variant enrollment + TorgoEval.

## E13-09: Dysarthric severity interpolation for data-scarce severities
**Hypothesis:** Since severe dysarthric data is scarcest (TORGO has only 1 severe speaker), interpolating between moderate and severe speaker features (in embedding space) generates synthetic "moderate-to-severe" examples that improve encoder performance on the scarcest severity levels.
**Score:** Impact=240 Feasibility=90 Constraints=170 Evidence=50 → **550 (B)**
**Description:** Encode moderate (F03) and severe (F04) utterances into WavLM embeddings. Linear interpolate: `e_synthetic = α·e_severe + (1-α)·e_moderate` for α ∈ (0,1). Train encoder with synthetic severe examples. Measure improvement on F04.
**Expected outcome:** 3-5pp rank-1 gain on F04. Interpolation in embedding space is a cheap way to augment the scarcest data category.
**How to run:** Embedding interpolation + augmented encoder training + severity-stratified eval.

## E13-10: Active learning for data-efficient encoder fine-tuning
**Hypothesis:** When fine-tuning the encoder on a user's speech (on-device), active selection of which utterances to use for fine-tuning (those with highest embedding uncertainty or lowest confidence) achieves the same accuracy gain with 50% fewer fine-tuning examples.
**Score:** Impact=200 Feasibility=120 Constraints=170 Evidence=60 → **550 (B)**
**Description:** Maintain an "uncertainty buffer" of recent queries. When the user confirms/rejects a match, add the utterance to the fine-tuning set only if it meets an uncertainty criterion (e.g., margin between top-2 commands < threshold, or confidence < 0.7). Fine-tune encoder with active subset vs random subset.
**Expected outcome:** Active selection reduces per-user fine-tuning data requirement by 40-60% for the same accuracy gain.
**How to run:** Uncertainty scoring + active selection + fine-tuning eval.
