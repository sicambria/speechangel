# Domain 04: Wake Word & False Accept Suppression

**Goal:** Achieve ≤0.5 FA/hr at the Stage-1 wake gate while maintaining ≥90% wake detection on real ambient audio, enabling always-on operation without false-firing.

**Current baseline:** ~82 FA/hr ambient (single-template, uncalibrated). In-regime (own words as gate): MFCC reaches ~65-69% detection at ~0 FA/hr. Best WavLM: FRR 25% at 0.5 FA/hr. **Need FRR <5% at ≤0.5 FA/hr.**

**Key insight from CP-2:** The ~82 FA/hr figure was substantially a cross-speaker-benchmark artifact. In the product regime (speaker's own words as gate), MFCC reaches 65-69% detection at ~0 FA/hr. The lever is **threshold calibration / dedicated rejection model**, not a better encoder.

---

## E04-01: Wake template set optimization (1 vs 3 vs 5 vs 10 wake templates)
**Hypothesis:** Multiple diverse wake templates (different conditions, times of day, distances) improve wake detection without proportionally increasing FA, because the min-DTW over diverse templates has a "tighter noise floor" than a single template.
**Description:** Enroll 1/3/5/10 wake templates from the speaker's own recorded examples. Run against ambient background (MUSAN noise or silence). Measure detection-vs-FA/hr curves. Report the operating points.
**Expected outcome:** 3-5 templates give the best detection-vs-FA trade-off; >5 templates provide marginal improvement but slightly increase FA (more chances for a noise false match).
**Win condition:** FRR reduction ≥10pp at matched FA/hr (≤0.5) from 1→3 templates.
**How to run:** AmbientFar with variable wake template counts.
**Status:** [ ] planned

## E04-02: Wake threshold calibration per-speaker (leave-one-out)
**Hypothesis:** A fixed wake threshold (e.g., DTW 4.0) is suboptimal — the optimal threshold varies by speaker's acoustic characteristics and background noise profile. Per-speaker calibration on held-out ambient data will find the threshold that maximizes detection at the FA budget.
**Description:** For each speaker, calibrate wake threshold on a held-out ambient segment to achieve target FA/hr (0.1, 0.5, 1.0). Measure detection rate on held-out wake utterances. Compare per-speaker vs global threshold.
**Expected outcome:** Per-speaker thresholds reduce FRR by 5-15pp at matched FA/hr vs global threshold.
**Win condition:** ≥5pp FRR reduction at ≤0.5 FA/hr.
**Constraints:** Requires ~1 minute of ambient audio to calibrate per speaker.
**How to run:** ThresholdCalibrator on wake templates + ambient, speaker-stratified.
**Status:** [ ] planned

## E04-03: Two-stage wake cascade (energy gate → DTW gate)
**Hypothesis:** The StreamingEnergyGate should be tuned to let through 15-20% of ambient frames (not 5% or 50%). Too tight: misses quiet wake attempts. Too loose: DTW runs on too many noise frames. The optimal cascade ratio minimizes total compute at target detection.
**Description:** Sweep StreamingEnergyGate threshold ratio (1.5×, 2×, 3×, 4×, 5× noise floor). For each, measure: (a) % of frames passed to DTW, (b) wake detection rate, (c) total compute per hour. Find the Pareto-optimal cascade point.
**Expected outcome:** 3× noise floor (current default) is near-optimal. 2× passes too many noise frames (increases compute, risk of DTW false accept). 4× misses quiet wake attempts.
**Win condition:** Verify the existing default is near-Pareto-optimal, or find the optimal point.
**How to run:** WakeGatedRecognizer parametrized with variable energy gate thresholds, benchmarked.
**Status:** [ ] planned

## E04-04: Dedicated rejection model (binary classifier on DTW matches)
**Hypothesis:** A simple binary classifier trained to distinguish "true wake matches" from "ambient noise false matches" using features of the DTW alignment (path length, warping cost, distance, endpoint alignment, energy profile) will reduce FA/hr by ≥50% at ≤2pp wake detection loss.
**Description:** Extract per-match features: (a) DTW distance, (b) normalized path length, (c) warping path variance, (d) start/end frame energy ratio, (e) VAD speech fraction. Train logistic regression / small MLP to classify true-vs-false wake. Evaluate on held-out speakers.
**Expected outcome:** Rejection model reduces FA/hr by 50-70% at ≤2pp detection loss, similar to dual-filter cascade (E02-08) but potentially stronger.
**Win condition:** ≥50% FA/hr reduction at ≤2pp wake detection loss.
**Constraints:** Features must be computable from existing internal DTW/VAD state.
**How to run:** Extract match features, train classifier, AmbientFar eval.
**Status:** [ ] planned

## E04-05: Onset-only wake matching (first 500ms of wake word)
**Hypothesis:** Wake words like "Hey SpeechAngel" or "OK Angel" have a distinctive onset (the first syllable) that carries most of the discriminatory information. Matching only the onset reduces compute and may reduce FA by ignoring the more variable tail of the utterance.
**Description:** Trim wake enrollments and queries to first 400/500/600/750ms. Compare onset-only DTW vs full-utterance DTW on detection-vs-FA curves.
**Expected outcome:** 500ms onset matching: 5-10% rel FA reduction at same detection as full utterance, with ~30% less DTW compute.
**Win condition:** ≥5% rel FA reduction at matched detection.
**Constraints:** Not all wake words have distinctive onsets; verify per-language.
**How to run:** Onset-trimmed wake matching in WakeWordGate.
**Status:** [ ] planned

## E04-06: Multi-frame persistence (require N consecutive wake detections)
**Hypothesis:** A single DTW match to a noise window is noise; requiring 2-3 consecutive wake-positive frames before triggering Stage-2 eliminates transient false accepts at minimal detection cost (the user says the wake word across multiple frames anyway).
**Description:** Require N consecutive wake detections (N=1/2/3/5) before waking. For a 150ms frame step, N=3 means 450ms of consecutive positive matches. Measure detection loss vs FA reduction.
**Expected outcome:** N=3 reduces FA/hr by 80-90% at ≤5pp detection loss, because real wake utterances span 500-2000ms (multiple frames) while noise false matches are transient.
**Win condition:** ≥80% FA/hr reduction at ≤5pp detection loss.
**How to run:** Add persistence counter to WakeGatedRecognizer state machine.
**Status:** [ ] planned

## E04-07: Wake word distinctness optimization
**Hypothesis:** Some wake words are inherently more FA-resistant than others based on acoustic complexity. A wake word chosen from an acoustically distinct syllable sequence (e.g., "OK Angel" with two very different vowels) will have lower ambient FA than a monotonous word (e.g., single repeated vowel).
**Description:** Enumerate wake word candidates with varied acoustic properties (vowel diversity, consonant-vowel ratio, syllable count, duration). Measure ambient FA/hr for each. Rank by FA-resistance.
**Expected outcome:** 2-syllable words with distinct vowels (e.g., /o/-/eɪ/) have 3-5× lower FA/hr than 1-syllable or monotone words.
**Win condition:** Identify the FA-optimal wake word design principles.
**How to run:** Vocab-quality sweep with wake-only templates, AmbientFar.
**Status:** [ ] planned

## E04-08: Negative template enrollment (anti-wake models)
**Hypothesis:** Enrolling typical ambient sounds (fan noise, TV, keyboard, traffic) as explicit "negative templates" and requiring a wake match to be closer to the wake template than to any negative template provides a cheap, interpretable FA suppression layer.
**Description:** Record 10-30 ambient sound clips per environment. When a candidate Wake is found, also run DTW against negative templates. Reject if distance to nearest negative < distance to nearest wake template. Compare FA/hr with and without negatives.
**Expected outcome:** Negatives reduce FA/hr by 30-50% at ≤3pp detection loss; especially effective for stationary noise (fans, AC).
**Win condition:** ≥30% FA/hr reduction at ≤3pp detection loss.
**How to run:** Negative template bank + rejection rule in WakeWordGate.
**Status:** [ ] planned

## E04-09: SNR-adaptive wake threshold
**Hypothesis:** A fixed wake threshold is too strict in quiet (where DTW distances are smaller for both true and false matches) and too loose in noise (where distances are inflated). Adapting the threshold based on estimated SNR will maintain constant FA/hr across environments.
**Description:** Estimate per-frame SNR from StreamingEnergyGate (signal RMS / noise-floor RMS). Apply SNR-dependent threshold offset: `threshold(snr) = base + a / (snr + b)`. Calibrate a, b on ambient data. Compare adaptive vs fixed threshold on variable-SNR data.
**Expected outcome:** Adaptive threshold reduces FA/hr in quiet by 30-50% without detection loss; maintains detection in noise where fixed threshold would reject.
**Win condition:** ≥20% FA/hr reduction at matched detection across variable SNR.
**How to run:** SNR-adaptive threshold in WakeWordGate, AmbientFar at variable SNR.
**Status:** [ ] planned

## E04-10: OpenWakeWord reference benchmark
**Hypothesis:** OpenWakeWord (OWW) achieves ≤0.5 FA/hr on continuous ambient — this is the reference standard for always-on wake. Benchmarking the SpeechAngel DTW wake against OWW on the same ambient data quantifies the gap and identifies whether OWW should be integrated as the Stage-1 gate (while keeping the DTW matcher for Stage-2 commands).
**Description:** Run openWakeWord (on-device or via Python API) on the same ambient audio used for CP-2 measurements. Compare FA/hr and detection rate vs SpeechAngel DTW wake at matched conditions. Report the head-to-head.
**Expected outcome:** OWW has lower FA/hr (0.2-0.5) but detection is English-only, so SpeechAngel DTW wake is the constraint-preserving option. The gap quantifies what personalization buys vs what a generic model can do.
**Win condition:** Quantified OWW-vs-DTW gap. Decision: integrate OWW as optional Stage-1, or close the gap with E04-01..09 techniques.
**How to run:** Python harness with OWW API + same ambient audio, compare FA/hr curves.
**Status:** [ ] planned
