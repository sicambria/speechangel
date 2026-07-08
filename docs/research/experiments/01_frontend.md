# Domain 01: Feature Extraction & Front-End Engineering

**Goal:** Find the feature representation that maximizes rank-1 discrimination and minimizes FRR at fixed FAR on dysarthric speech, while preserving language-independence.

**Current baseline:** MFCC-13 static, 25ms frame, 10ms shift, 26 mel filters, pre-emphasis 0.97, Hamming window, CMN. Rank-1 55.4% dysarthric / 74.6% control.

**Key insight from CP-1 spike:** The representation change alone (WavLM vs MFCC) doesn't help under DTW — WavLM-under-DTW *ties* MFCC. The interaction with the matcher (pooled-cosine) is what delivers the gain. So front-end experiments must be paired with compatible matchers.

---

## E01-01: Multi-resolution MFCC (frame-length sweep)
**Hypothesis:** Longer frames (30-50ms) capture more spectral structure at the cost of temporal resolution; for dysarthric speech with slower articulatory transitions, longer frames will improve rank-1.
**Description:** Sweep frame lengths 15/20/25/30/40/50ms at fixed shift (10ms). Evaluate rank-1 on TORGO speaker-dependent, matched within each speaker.
**Expected outcome:** 30-35ms frames outperform 25ms baseline on dysarthric speakers by 3-8pp rank-1.
**Win condition:** ≥3pp rank-1 gain on dysarthric subset.
**Constraints:** Must not degrade control speaker accuracy by >2pp.
**How to run:** `make bench-picovoice WINDOW=30/40/50` or modify `MfccConfig` in a bake-off harness.
**Status:** [ ] planned

## E01-02: Delta-order sweep (static vs +Δ vs +ΔΔ) with matched-FAR comparison
**Hypothesis:** Δ and ΔΔ capture temporal dynamics lost in static MFCC; ΔΔ (acceleration) is especially relevant for dysarthric speech with irregular rhythm. But adding dimensions increases the DTW distance space — the net effect at matched FAR is unknown.
**Description:** Compare static(13) vs +Δ(26) vs +ΔΔ(39) at matched held-out FAR on TORGO. Use McNemar to test significance. Pre-register: ΔΔ will reduce FRR by ≥5% rel at matched FAR.
**Expected outcome:** ΔΔ reduces FRR by ≤3% rel — directionally positive but small effect. The dimensionality increase dilutes the gain.
**Win condition:** ≥5% relative FRR reduction at matched FAR.
**Constraints:** Must not increase DTW compute by >3× (39-dim vs 13-dim).
**How to run:** `FrontEndBakeoff` with delta variants; TORGO held-out eval.
**Status:** [~] running — baseline bake-off done, needs held-out FAR-matched comparison per EVAL-002

## E01-03: PLP (Perceptual Linear Prediction) vs MFCC
**Hypothesis:** PLP's equal-loudness pre-emphasis + cubic-root intensity-to-loudness compression is more robust to spectral tilt variation common in dysarthric speech than MFCC's log compression.
**Description:** Implement PLP front-end (Bark-scale critical bands, equal-loudness curve, cubic-root compression, LP-to-cepstral). A/B against MFCC-13 on TORGO at matched FAR.
**Expected outcome:** PLP gives 2-5pp rank-1 gain on severe dysarthric speakers (F01, F04), ties on control.
**Win condition:** ≥3pp rank-1 gain on dysarthric subset.
**Constraints:** Must remain pure-Kotlin deterministic; no external deps.
**How to run:** New `PlpExtractor` in core:dsp, bake-off harness.
**Status:** [ ] planned

## E01-04: RASTA filtering (relAtive SpecTrA)
**Hypothesis:** RASTA's bandpass filtering of each frequency channel's temporal trajectory suppresses stationary channel distortions and slow spectral tilt changes common in dysarthric speech, improving discrimination.
**Description:** Add RASTA filter (IIR bandpass 0.26-12.8 Hz) between mel filterbank and log. Compare RASTA-MFCC vs plain MFCC at matched FAR.
**Expected outcome:** RASTA reduces FRR by 5-10% rel on dysarthric, minimal effect on control.
**Win condition:** ≥5% rel FRR reduction on dysarthric.
**Constraints:** RASTA adds ~2ms latency per frame; must not break determinism.
**How to run:** New RASTA option in MfccExtractor, bake-off.
**Status:** [ ] planned

## E01-05: Cepstral Mean and Variance Normalization (CMVN)
**Hypothesis:** Variance normalization, deliberately excluded from current CMN (to preserve DTW distance scale), may help when using cosine-distance matchers. Test whether CMVN + cosine beats CMN + DTW.
**Description:** Add variance normalization option (CMVN = mean subtraction + divide by std). Compare CMN-DTW vs CMVN-DTW vs CMN-cosine vs CMVN-cosine on TORGO.
**Expected outcome:** CMVN-DTW worse than CMN-DTW (normalized scale hurts Euclidean distances). CMVN-cosine better than CMN-cosine for QbE path.
**Win condition:** For QbE path: ≥5% rel FRR reduction. For DTW path: no regression.
**Constraints:** Separate config for template vs QbE backend.
**How to run:** Add `varianceNormalization: Boolean` to MfccConfig, bake-off.
**Status:** [ ] planned

## E01-06: Multi-taper spectral estimation
**Hypothesis:** Thomson multi-taper reduces variance of spectral estimates, producing more stable MFCCs that improve DTW alignment for variable-quality dysarthric speech.
**Description:** Replace single Hamming-tapered FFT with 3-5 Slepian tapers, weighted average of power spectra. Compare rank-1 and FRR vs single-taper.
**Expected outcome:** 2-4pp rank-1 gain on dysarthric with high within-speaker variability (F04).
**Win condition:** ≥2pp rank-1 gain on highest-variance speaker.
**Constraints:** Multi-taper costs 3-5× FFT compute; must measure latency impact.
**How to run:** New multi-taper option in Fft/MfccExtractor.
**Status:** [ ] planned

## E01-07: Modulation-filtered spectrogram features
**Hypothesis:** Dysarthric speech has abnormal modulation spectra (rate of amplitude change in each frequency band). Features from modulation-filtered spectrograms will capture this pathology better than MFCC.
**Description:** Compute modulation spectrogram (FFT along time axis for each frequency bin), keep modulation rates 2-16 Hz, reconstruct spectrogram, extract MFCC. Compare vs baseline.
**Expected outcome:** 3-5pp rank-1 gain on moderate-to-severe dysarthric.
**Win condition:** ≥3pp rank-1 gain on dysarthric subset.
**Constraints:** Requires ~500ms lookahead — unsuitable for streaming Stage-1, OK for Stage-2.
**How to run:** New modulation filter + bake-off.
**Status:** [ ] planned

## E01-08: Sub-band feature concatenation
**Hypothesis:** Decomposing the spectrum into 3-4 sub-bands and extracting MFCC per sub-band captures frequency-local dynamics that full-band MFCC blurs, especially useful for dysarthric formant distortions.
**Description:** Split 20-8000 Hz into 4 bands (20-400, 400-1200, 1200-3000, 3000-8000 Hz). Extract 7 MFCCs per band, concatenate to 28-dim. A/B vs 13-dim full-band MFCC.
**Expected outcome:** 3-5pp rank-1 gain; sub-band features capture formant structure better.
**Win condition:** ≥3pp rank-1 gain.
**Constraints:** 28-dim increases DTW cost ~2×; measure latency.
**How to run:** New sub-band mode in MfccExtractor.
**Status:** [ ] planned

## E01-09: Pitch-synchronous framing
**Hypothesis:** Standard fixed-length frames misalign with glottal pulses in dysarthric speech (irregular pitch, breathiness). Pitch-synchronous analysis (frame aligned to pitch periods) will produce stabler features.
**Description:** Estimate F0 via autocorrelation, set frame length to 3× pitch period (minimum 20ms, maximum 50ms). Compare pitch-sync vs fixed-frame MFCC on TORGO.
**Expected outcome:** 2-3pp gain on speakers with irregular pitch (dysarthric), neutral on control.
**Win condition:** ≥2pp rank-1 gain on dysarthric.
**Constraints:** F0 estimation adds complexity; may fail on unvoiced segments (fall back to fixed frame).
**How to run:** New PitchEstimator + adaptive MfccExtractor.
**Status:** [ ] planned

## E01-10: Learned filterbank initialization for on-device MFCC
**Hypothesis:** A static mel filterbank is suboptimal for dysarthric speech. A task-optimized filterbank (learned offline on dysarthric data, then frozen on-device) re-weights frequency regions to maximize command discrimination while keeping the same MFCC pipeline determinism.
**Description:** Learn a bank of 26 frequency-domain filters (initialized to mel) via gradient descent on a dysarthric command-discrimination task. Export the optimized filter bank weights to replace the mel filterbank. Compare frozen-learned vs mel on TORGO.
**Expected outcome:** 4-8pp rank-1 gain — the single largest front-end lever.
**Win condition:** ≥5pp rank-1 gain on dysarthric.
**Constraints:** Filterbank is static at inference (preserves determinism); training is offline.
**How to run:** Python training script → export filter weights → Kotlin MelFilterBank with learned weights → bake-off.
**Status:** [ ] planned
