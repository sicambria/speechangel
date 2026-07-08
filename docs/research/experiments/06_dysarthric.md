# Domain 06: Dysarthric Speech Specialization

**Goal:** Close the dysarthric-vs-control rank-1 gap (currently 55.4% vs 74.6% = 19.2pp gap) to ≤5pp, by using techniques specifically designed for impaired speech characteristics.

**Current baseline:** Rank-1 55.4% dysarthric (F01 mild, F03 moderate, F04 severe) vs 74.6% control. The gap is driven by: inconsistent articulation, irregular timing, reduced spectral contrast, irregular pitch/energy.

**Key insight:** The ~10% FRR neural baselines on dysarthric (PD-DWS) are closed-vocab, trained on that vocabulary. But the *population IS tractable* — Euphonia hits 13.9% WER personalized on dysarthric. The techniques that work for general dysarthric ASR (spectral normalization, duration modeling, phonetic priors) should be evaluated for template matching.

---

## E06-01: Per-severity analysis (F0 mild / F03 moderate / F04 severe)
**Hypothesis:** MRCC-DTW rank-1 degrades monotonically with severity. Understanding the severity-degradation curve identifies which severity level is the gating factor and where the largest gains are.
**Description:** Stratify TORGO results by severity (F01=mild, F03=moderate, F04=severe) and by control speaker. Report per-severity rank-1, FRR-vs-FAR, and confusion patterns. Identify which severity drives the majority of errors.
**Expected outcome:** Severe (F04) has rank-1 ~30-40%, moderate (F03) ~50-60%, mild (F01) ~65-75%. Severe speakers account for disproportionate share of errors.
**Win condition:** Quantified per-severity baseline. SOTA target: ≥60% rank-1 for severe, ≥75% for moderate, ≥85% for mild.
**How to run:** TorgoEval with per-speaker breakdown (already partially available).
**Status:** [ ] planned

## E06-02: Formant-aware features (F1/F2 tracking)
**Hypothesis:** Dysarthric speech is characterized by reduced vowel space (F1/F2 formant centralization) and imprecise formant transitions. Features that explicitly track formant frequencies and bandwidths will capture dysarthria-specific information that MFCCs blur.
**Description:** Extract F1, F2, F3 formant frequencies + bandwidths + amplitudes per frame via LPC root-solving. Concatenate with MFCC as a joint feature vector. Compare MFCC-only vs MFCC+formant on dysarthric subset.
**Expected outcome:** Formant features improve rank-1 by 5-10pp on severe dysarthric (where formant centralization is most informative) and have minimal effect on control.
**Win condition:** ≥5pp rank-1 gain on severe dysarthric (F04).
**Constraints:** Formant tracking is less stable than MFCC; may need smoothing and voiced-only extraction.
**How to run:** New FormantTracker in core:dsp, joint feature extraction, bake-off.
**Status:** [ ] planned

## E06-03: Jitter/shimmer/HNR features (voice quality)
**Hypothesis:** Dysarthric speech often has pathological voice quality (breathiness, roughness, strain). Acoustic measures like jitter (pitch perturbation), shimmer (amplitude perturbation), and Harmonics-to-Noise Ratio (HNR) capture voice quality dimensions that MFCCs are insensitive to.
**Description:** Extract per-frame jitter (cycle-to-cycle F0 variation), shimmer (cycle-to-cycle amplitude variation), and HNR. Add as 3-4 extra feature dimensions. Compare MFCC-only vs MFCC+voice-quality on dysarthric.
**Expected outcome:** Voice quality features add 3-5pp rank-1 for speakers with breathy/rough voice (common in dysarthria) and are neutral-to-positive for control.
**Win condition:** ≥3pp rank-1 gain on dysarthric.
**Constraints:** Jitter/shimmer require reliable F0 estimation, which fails on unvoiced frames (set to 0).
**How to run:** New VoiceQualityExtractor, feature concatenation, bake-off.
**Status:** [ ] planned

## E06-04: Articulatory features (spectral moment analysis)
**Hypothesis:** Spectral moments (centroid, spread, skewness, kurtosis) capture articulatory information (place/manner of constriction) that correlates with dysarthria severity and is more robust to vocal tract distortions than MFCC.
**Description:** Compute spectral moments per frame: centroid, bandwidth, skewness, kurtosis of the power spectrum. Add as 4 extra feature dimensions. Compare MFCC-only vs MFCC+moments on dysarthric.
**Expected outcome:** Moments add 2-4pp rank-1, especially for moderate-to-severe dysarthric where articulatory precision is degraded.
**Win condition:** ≥2pp rank-1 gain on dysarthric.
**How to run:** New SpectralMomentExtractor, concatenation, bake-off.
**Status:** [ ] planned

## E06-05: Speaking-rate-adaptive DTW window
**Hypothesis:** Dysarthric speech is typically slower than control speech, with variable within-utterance rate. The Sakoe-Chiba band constraint (currently fixed at 10% of template length) should adapt to estimated speaking rate: wider band for slow speech (more temporal variability), narrower for fast.
**Description:** Estimate speaking rate from the number of energy peaks per second (syllable-rate proxy). Set Sakoe-Chiba band as `max(10%, rate * k)%` of template length. Compare rate-adaptive vs fixed band.
**Expected outcome:** Rate-adaptive band reduces FRR by 3-5% rel on slowest and fastest utterances where fixed 10% band is mismatched.
**Win condition:** ≥3% rel FRR reduction at matched FAR.
**How to run:** Rate estimator + adaptive band in Dtw.kt.
**Status:** [ ] planned

## E06-06: Dysarthric-specific template clustering
**Hypothesis:** A dysarthric speaker's utterances of the same command may form multiple clusters (good-day vs bad-day realizations) rather than a single cluster. Using cluster-aware matching (match to nearest cluster centroid first, then within cluster) may improve discrimination for highly variable speakers.
**Description:** Cluster a speaker's templates per command using DTW distance matrix (hierarchical clustering). For recognition, match query to each cluster's medoid, take best cluster's best template. Compare vs flat min-DTW on high-variability speakers.
**Expected outcome:** Cluster-aware matching improves rank-1 by 5-10pp on F04 (severe dysarthric, highest variability) but is neutral on control (where clusters don't form).
**Win condition:** ≥5pp rank-1 gain on high-variability dysarthric speakers.
**How to run:** Template clustering in TemplateMatcher, per-variability evaluation.
**Status:** [ ] planned

## E06-07: Duration normalization (tempo-invariant features)
**Hypothesis:** Dysarthric speakers have irregular articulation rates. Pitch-synchronous overlap-add (PSOLA) time-scale modification can normalize all utterances to a canonical duration before feature extraction, removing tempo as a confounding factor in DTW matching.
**Description:** Apply PSOLA time-scaling to stretch/compress all utterances (both enrollment and query) to a fixed syllable-rate-normalized duration. Extract MFCC from time-normalized audio. Compare rank-1 vs raw-duration approach.
**Expected outcome:** Duration normalization improves rank-1 by 3-5pp on speakers with high rate variability and reduces the speaker-dependent calibration drift.
**Win condition:** ≥3pp rank-1 gain on dysarthric.
**Constraints:** PSOLA introduces artifacts at extreme scaling; limit to 0.7-1.3× range.
**How to run:** AudioAugment PSOLA time-scaling + time-normalized MfccExtractor.
**Status:** [ ] planned

## E06-08: Syllable-locked features (syllable nucleus detection)
**Hypothesis:** Syllable nuclei (vowel centers) are the most stable acoustic landmarks in dysarthric speech. Extracting features only at syllable nuclei, or weighting frames by distance to the nearest nucleus, improves robustness to the variable consonant articulation that characterizes dysarthria.
**Description:** Detect syllable nuclei from energy peaks in the 300-2000 Hz band (reflecting sonorant energy). Extract MFCC at nuclei + interpolate between nuclei. Alternatively, weight frames by proximity to nuclei. Compare vs uniform-frame approach.
**Expected outcome:** Nucleus-weighted features give 5-10pp rank-1 gain on severe dysarthric where consonant articulation is highly inconsistent.
**Win condition:** ≥5pp rank-1 gain on severe dysarthric.
**How to run:** SyllableNucleusDetector + weighted feature extraction.
**Status:** [ ] planned

## E06-09: Personalized spectral normalization (speaker z-score)
**Hypothesis:** Dysarthric speakers have speaker-specific spectral baselines (e.g., consistently reduced high-frequency energy). Normalizing each speaker's features to z-scores within-speaker (subtract speaker mean, divide by speaker std) removes this systematic bias, improving cross-command discrimination.
**Description:** Compute per-speaker mean and std of each MFCC dimension across all enrolled templates. Z-score normalize both enrollment and query features. Compare rank-1 with and without speaker z-scoring.
**Expected outcome:** Speaker z-scoring gives 3-5pp rank-1 gain by removing baseline spectral tilt differences and reducing the distance scale to within-speaker variation.
**Win condition:** ≥3pp rank-1 gain on dysarthric.
**Constraints:** Z-scoring requires multiple enrolled templates to estimate speaker stats; degrades with <5 templates.
**How to run:** SpeakerStats computation + z-score normalization in MfccExtractor.
**Status:** [ ] planned

## E06-10: Dysarthric severity-adaptive pipeline
**Hypothesis:** The optimal feature set, DTW band width, and threshold depend on dysarthria severity. A severity-detection front-end that estimates severity from voice quality features and selects the appropriate pipeline configuration will outperform a one-size-fits-all pipeline.
**Description:** Estimate severity from jitter, shimmer, HNR, speaking rate, and vowel space area (if formants are tracked). Classify into mild/moderate/severe. Pre-configure optimal pipeline per class. Compare severity-adaptive vs uniform pipeline.
**Expected outcome:** Severity-adaptive pipeline reduces FRR by 10-15% rel vs uniform pipeline on the mixed-severity population by applying the right technique for each severity level.
**Win condition:** ≥10% rel FRR reduction on mixed-severity set.
**Constraints:** Severity estimation must not require labeled data; unsupervised clustering of voice quality features may suffice.
**How to run:** Severity estimator + adaptive pipeline selection, per-speaker eval.
**Status:** [ ] planned
