# Domain 05: Noise Robustness & Real-World Deployment

**Goal:** Maintain recognition accuracy under real-world noise, distance, and acoustic variability, measured as FRR-vs-SNR curves and far-field degradation.

**Current baseline:** SPECTRAL_SUBTRACTION noise reduction (α=1.5, β=0.05, 10th percentile noise floor). Directionally but not significantly better than no noise reduction on TORGO. SOTA competitive bar scores SpeechAngel 25/100 on noise (vs mature-shipped 45-85).

**Key insight:** Noise is the dominant degrader in the condition-simulation harness. Multi-condition enrollment + augmentation + SNR-adaptive thresholds form the three-pronged attack.

---

## E05-01: Noise reduction parameter sweep (α, β, percentile)
**Hypothesis:** The current spectral subtraction parameters (α=1.5, β=0.05, 10th percentile) are reasonable defaults but not optimized for dysarthric speech. Optimizing these parameters on noisy TORGO will find settings that give significant improvement.
**Description:** Sweep α (over-subtraction: 1.0, 1.5, 2.0, 3.0, 4.0), β (spectral floor: 0.01, 0.05, 0.1, 0.2), percentile (noise floor: 5th, 10th, 20th, 30th). Mix TORGO with MUSAN noise at SNRs 0/5/10/15 dB. Measure rank-1 and FRR with noise reduction on/off at each parameter set.
**Expected outcome:** α=2.0, β=0.05-0.1, 10th percentile optimizes the trade-off between noise suppression and speech distortion. Rank-1 gain of 2-4pp at SNR=5dB vs baseline noise reduction.
**Win condition:** ≥2pp rank-1 gain at SNR≤5dB vs current noise reduction.
**How to run:** Noise reduction param sweep in MfccConfig, AudioAugment noise mixing, TorgoEval.
**Status:** [ ] planned

## E05-02: Wiener filter vs spectral subtraction
**Hypothesis:** Wiener filtering (MMSE-based, uses noise+speech variance estimate) better preserves speech harmonics than spectral subtraction (which can introduce musical noise artifacts), giving cleaner MFCCs for DTW matching in moderate noise (SNR 5-15 dB).
**Description:** Implement Wiener filter: estimate per-band signal+noise power during speech frames, noise power during silence. Apply `H = max(S/(S+N), β)`. Compare vs spectral subtraction at matched conditions.
**Expected outcome:** Wiener filter gives 2-3pp higher rank-1 at SNR 5-10 dB by preserving harmonic structure. Spectral subtraction is similar at SNR≥15 dB.
**Win condition:** ≥2pp rank-1 gain at SNR 5-10 dB vs spectral subtraction.
**How to run:** New WienerFilter option alongside SPECTRAL_SUBTRACTION in MfccConfig.
**Status:** [ ] planned

## E05-03: Log-MMSE noise reduction
**Hypothesis:** Log-MMSE (Ephraim-Malah) minimizes log-spectral distortion, which aligns well with MFCC's log-mel domain — it preserves the cepstral features better than MMSE in the power domain or spectral subtraction.
**Description:** Implement Log-MMSE estimator. Calculate a priori and a posteriori SNRs per frequency bin, apply Ephraim-Malah gain function. A/B vs spectral subtraction and Wiener on noisy TORGO.
**Expected outcome:** Log-MMSE gives best MFCC preservation of the three, especially at SNR 0-5 dB.
**Win condition:** ≥1pp rank-1 gain over Wiener at SNR≤5 dB.
**How to run:** New NoiseReduction mode in MfccConfig.
**Status:** [ ] planned

## E05-04: MUSAN noise augmentation for enrollment
**Hypothesis:** Enrolling with noise-augmented templates (additive MUSAN noise at varied SNRs) will improve rank-1 on noisy queries by training the template set to include noise variability, without changing the matcher.
**Description:** Augment TORGO enrollment samples with MUSAN noise at SNRs 5/10/15/20/clean dB. Keep 1 template per condition. Test noisy queries. Compare: (a) clean enrollment → noisy query, (b) noise-augmented enrollment → noisy query.
**Expected outcome:** Noise-augmented enrollment reduces FRR at matched SNR by 10-20% rel vs clean-only enrollment. Cross-condition (train at 10dB, test at 5dB) still shows benefit.
**Win condition:** ≥10% rel FRR reduction at SNR≤10 dB.
**How to run:** AudioAugment MUSAN mixing, multi-condition enrollment, TorgoEval.
**Status:** [ ] planned

## E05-05: RIR (Room Impulse Response) convolution for far-field robustness
**Hypothesis:** Convolving TORGO speech with measured room impulse responses (small room, medium room, large room, with various distances) creates realistic far-field audio for benchmarking and enrollment augmentation.
**Description:** Apply OpenSLR RIR convolutions to TORGO at distances 0.3m/1m/2m/4m. Measure FRR-vs-distance curves with and without RIR-augmented enrollment. Identify the distance at which FRR doubles.
**Expected outcome:** FRR doubles at ~2m distance with near-field enrollment. RIR-augmented enrollment pushes the double-FRR distance to ~3-4m.
**Win condition:** ≥50% increase in "usable distance" (distance at which FRR doubles).
**How to run:** AudioAugment RIR convolution, DistanceCondition in ConditionEval.
**Status:** [ ] planned

## E05-06: Room+Noise combined augmentation (MUSAN + RIR)
**Hypothesis:** Real-world conditions combine reverb AND noise. The interaction is multiplicative — reverb smears spectral features, noise adds to the smeared signal. Augmenting enrollment with combined RIR+MUSAN creates the most realistic training data.
**Description:** Apply RIR first (distance-varying), then add MUSAN noise. Compare: (a) clean enrollment, (b) noise-only aug, (c) RIR-only aug, (d) RIR+noise aug. Test on combined reverb+noise queries.
**Expected outcome:** Combined augmentation (d) outperforms either alone by 5-10% rel FRR. The interaction is synergistic — noise-only augmentation helps but doesn't address reverb smearing.
**Win condition:** ≥5% rel FRR gain over best single-factor augmentation.
**How to run:** AudioAugment chain RIR→noise, combined conditions, TorgoEval.
**Status:** [ ] planned

## E05-07: SNR-adaptive acceptance threshold
**Hypothesis:** The per-command acceptance threshold should rise (become more selective) when SNR is low, because DTW distances inflate for both same-command and different-command matches, making the absolute threshold less meaningful. A threshold that tracks SNR preserves the FAR budget.
**Description:** For each query, estimate SNR from the VAD noise floor. Apply threshold offset: `effective = base + k / (snr + c)`. Calibrate k and c to maintain target FAR across SNR levels. Compare adaptive vs fixed threshold on variable-SNR data.
**Expected outcome:** Adaptive threshold maintains FAR within 2× of target across SNR 0-30 dB, while fixed threshold either over-rejects in noise (high FRR) or over-accepts in quiet (high FAR).
**Win condition:** FAR within 2× of target across SNR 0-30 dB.
**How to run:** SNR-adaptive threshold in TemplateMatcher, SNR-condition sweep.
**Status:** [ ] planned

## E05-08: Band-limited robustness (telephone/microphone frequency response)
**Hypothesis:** Real-world microphones vary in frequency response (phone mic, headset, smart speaker). The system should be robust to band-limiting (300-3400 Hz telephone band, or a low-quality mic that rolls off below 500 Hz and above 6000 Hz).
**Description:** Apply bandpass filters (300-3400, 80-8000, 300-8000, 300-6000 Hz) to queries. Measure FRR degradation vs full-band. Test whether augmenting enrollment with band-limited templates helps.
**Expected outcome:** 300-3400 Hz (telephone band) degrades rank-1 by 10-15pp. Frequencies below 500 Hz carry significant dysarthric voicing information — losing them hurts more than losing high frequencies.
**Win condition:** Quantify the degradation curve. If telephone-band enrollment augmentation reduces degradation by ≥50%, it's worth shipping as a mode.
**How to run:** AudioAugment band-limiting, ConditionEval.
**Status:** [ ] planned

## E05-09: Packet-loss / stutter robustness (streaming audio artifacts)
**Hypothesis:** On-device real-time audio streaming can drop frames (GC pause, CPU contention). Random frame dropping (5-15% of frames) simulates this. DTW's temporal warping should handle small gaps — but at what dropout rate does rank-1 break?
**Description:** Randomly drop 1%/2%/5%/10%/15%/20% of query frames (consecutive bursts of 1-3 frames). Measure rank-1 degradation. Test whether frame interpolation (linear interpolation of dropped frames) restores accuracy.
**Expected outcome:** DTW absorbs ≤5% random frame loss with ≤2pp degradation. ≥10% loss causes 5-10pp degradation. Interpolation of dropped frames recovers most of the loss.
**Win condition:** Quantify the dropout tolerance curve; determine whether interpolation is worth the compute.
**How to run:** AudioAugment frame dropping, ConditionEval.
**Status:** [ ] planned

## E05-10: Multi-microphone / beamforming simulation
**Hypothesis:** Although SpeechAngel runs on a single-mic phone, simulating a 2-mic delay-and-sum beamformer (as a preprocessing step) could improve SNR by 3-6 dB in far-field, giving a noise-robustness boost that's worth measuring.
**Description:** Create a simulated 2-mic array from TORGO: original signal at mic1, delayed+attenuated copy at mic2 (with small noise at each). Apply delay-and-sum beamforming. Compare MFCC from beamformed output vs single-mic.
**Expected outcome:** Simulated beamforming gives 2-4pp rank-1 gain at far-field conditions. This is a "what if" to determine whether recommending a dual-mic setup to users is worthwhile.
**Win condition:** Quantify the beamforming benefit.
**How to run:** AudioAugment simulated array + beamforming, ConditionEval.
**Status:** [ ] planned
