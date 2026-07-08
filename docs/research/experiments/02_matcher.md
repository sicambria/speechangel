# Domain 02: Matching Algorithms

**Goal:** Find the matching algorithm that maximizes discrimination between enrolled commands at matched FAR, while preserving language-independence and determinism.

**Current baseline:** Length-normalized DTW with Euclidean local distance, Sakoe-Chiba band (10% of longer sequence), 1-NN per-command min-distance. Rank-1 55.4% dysarthric.

**Key insight from CP-1 2×2:** The matcher matters more than the front-end for speech-impairment discrimination. WavLM-under-DTW ties MFCC; WavLM-under-pooled-cosine wins by 17pp. The interaction (representation × matcher) is the lever.

---

## E02-01: Cosine distance DTW (replace Euclidean local distance)
**Hypothesis:** Cosine distance between feature frames is invariant to overall amplitude scaling (common in dysarthric speech) and may align sequences better than Euclidean distance. Keep length-normalized DTW structure, change only the local dissimilarity.
**Description:** Replace `euclidean(a,b)` with `1 - cosineSimilarity(a,b)` in Dtw.kt. Compare at matched FAR against Euclidean DTW on TORGO.
**Expected outcome:** Cosine-DTW gives 3-6pp rank-1 gain on dysarthric (amplitude-invariant), neutral on control.
**Win condition:** ≥3pp rank-1 gain on dysarthric.
**Constraints:** Cosine is ~1.3× more expensive per frame pair than Euclidean (dot product + norm product replaces L2).
**How to run:** Modify Dtw.kt local distance function, bake-off.
**Status:** [ ] planned

## E02-02: Derivative DTW (D-DTW)
**Hypothesis:** DTW on the *derivative* of feature trajectories (first-order temporal difference of MFCC frames) emphasizes spectral change rate rather than absolute spectral shape, reducing sensitivity to static channel/tilt distortions. The original D-DTW paper (Keogh & Pazzani 2001) shows improved classification for time-series with varying baselines.
**Description:** Compute Δ-MFCC per frame, run DTW on derivative sequences. Compare D-DTW vs plain DTW at matched FAR.
**Expected outcome:** D-DTW reduces FRR by 5-10% rel on dysarthric speakers with high spectral tilt variability.
**Win condition:** ≥5% rel FRR reduction.
**Constraints:** Derivative amplifies frame-to-frame noise; test with and without smoothing.
**How to run:** New option in Dtw/TemplateMatcher, bake-off.
**Status:** [ ] planned

## E02-03: Subsequence DTW (open-begin-end matching)
**Hypothesis:** Current Sakoe-Chiba-constrained full-sequence DTW forces endpoint alignment. Subsequence DTW (allowing query to match any contiguous subsegment of template) handles variable-length utterances and partial commands better for dysarthric speech where users may trail off or start hesitantly.
**Description:** Implement open-begin-end DTW (relax start/end constraints). Score = best open-ended match. Normalize by (query length + matched template subsegment length). Compare vs endpoint-constrained on TORGO.
**Expected outcome:** 3-5pp rank-1 gain; handles variable-length dysarthric utterances better.
**Win condition:** ≥3pp rank-1 gain.
**Constraints:** Slightly more compute (relaxed constraints); may increase false accepts.
**How to run:** New subsequence DTW mode in Dtw.kt.
**Status:** [ ] planned

## E02-04: Weighted DTW (learned frame weights)
**Hypothesis:** Not all MFCC frames are equally discriminative — voiced regions (vowels) carry more command identity than unvoiced (fricatives, silence). Weighting frames by estimated voicing/speech presence before DTW will improve rank-1.
**Description:** Compute per-frame weight w_i ∈ [0,1] from voice-activity confidence (harmonicity, or energy above noise floor). Use weighted DTW: local cost c(i,j) = w_i * w_j * d(x_i, y_j). Compare vs unweighted DTW.
**Expected outcome:** 2-4pp rank-1 gain; downweights silences and noise frames.
**Win condition:** ≥2pp rank-1 gain.
**Constraints:** Weight computation must be deterministic and cheap (use existing EnergyVad confidence, not a new model).
**How to run:** New weighted mode in Dtw.kt, pass weights from VAD.
**Status:** [ ] planned

## E02-05: k-NN matching (k > 1) with distance fusion
**Hypothesis:** Current 1-NN (single nearest template) discards information from the 2nd/3rd nearest templates. Averaging distances from top-k templates per command reduces variance and improves robustness to outlier enrollments.
**Description:** For each command, compute the mean (or median) distance of the k nearest templates to the query. Select best command by fused distance. k=3 as pre-registered candidate. Compare k-NN vs 1-NN at matched FAR.
**Expected outcome:** k=3 reduces FRR by 3-5% rel by reducing variance from single-template outliers.
**Win condition:** ≥3% rel FRR reduction.
**Constraints:** Compute cost grows linearly in k; k=3 adds minimal overhead.
**How to run:** TemplateMatcher option for k > 1.
**Status:** [ ] planned

## E02-06: Mahalanobis distance in PCA-reduced space
**Hypothesis:** MFCC dimensions are correlated; Euclidean DTW treats them as independent, inflating distances along high-correlation axes. Projecting to PCA space and using Mahalanobis distance normalizes per-axis variance and removes correlation.
**Description:** Compute PCA on all enrolled templates (or a reference set), retain 95% variance dimensions. Project query and templates, run DTW with Mahalanobis distance (or equivalently, Euclidean in whitened PCA space). Compare vs baseline.
**Expected outcome:** 3-5pp rank-1 gain; better separation of command clusters.
**Win condition:** ≥3pp rank-1 gain.
**Constraints:** PCA must be computed per user (on-device) from their templates; needs stable covariance estimate from limited data.
**How to run:** New PCA preprocessor + Mahalanobis mode in Dtw.kt.
**Status:** [ ] planned

## E02-07: Soft-DTW for gradient-aware matching
**Hypothesis:** Standard DTW uses a hard "min" operator that makes the alignment path discontinuous w.r.t. input — small input changes can flip the optimal path, introducing variance. Soft-DTW (Cuturi & Blondel 2017) uses a smoothed min (log-sum-exp) that produces a differentiable, lower-variance alignment, especially beneficial for dysarthric speech with irregular timing.
**Description:** Implement Soft-DTW with smoothing parameter γ (sweep 0.01, 0.1, 1.0). The soft-min operator: `min^γ(a,b) = -γ log(exp(-a/γ) + exp(-b/γ))`. Compare rank-1 vs hard-DTW.
**Expected outcome:** γ=0.1 gives 2-4pp rank-1 gain via smoother alignment; γ=1.0 over-smooths and degrades.
**Win condition:** ≥2pp rank-1 gain.
**Constraints:** Log-sum-exp is ~2× more expensive per DP cell than min; smoothing may increase false accepts.
**How to run:** New Soft-DTW mode in Dtw.kt.
**Status:** [ ] planned

## E02-08: Dual-filter cascade (second-opinion rejection)
**Hypothesis:** From LRDWWS'24 winner: a length-based second-opinion filter rejects DTW matches where the aligned path length deviates too far from the expected utterance duration, killing false accepts from partial/brief noise matches. This is the highest-leverage FAR reduction technique.
**Description:** After DTW match, reject if `|alignedPathLength - expectedLength| / expectedLength > tolerance`. Expected length = median of all successful match path lengths for that command. Sweep tolerance (0.2, 0.3, 0.4, 0.5). Measure FRR vs FAR reduction.
**Expected outcome:** FAR reduced by 50-70% at ≤3pp FRR cost. The single largest FAR lever.
**Win condition:** ≥50% FAR reduction at ≤3pp FRR increase.
**Constraints:** Must track path length in DTW (add a return value); expected length adapts per command.
**How to run:** Add path-length tracking to Dtw.kt, dual-filter in TemplateMatcher.
**Status:** [ ] planned

## E02-09: Segmental DTW (word-boundary-aware matching)
**Hypothesis:** For multi-word commands, DTW can be misled by cross-word alignment (aligning syllable from word-1 with syllable from word-2 of a different command). Segmenting at energy valleys and doing piecewise DTW per segment should improve discrimination for multi-syllable commands.
**Description:** Detect segment boundaries via energy-VAD valleys (>200ms silence or >6dB dip). Run independent DTW per segment, sum normalized distances. Compare vs whole-utterance DTW.
**Expected outcome:** 2-4pp rank-1 gain on multi-word commands; neutral on single-word commands.
**Win condition:** ≥2pp gain on multi-word command subset (≥5 words).
**How to run:** New segmental mode in TemplateMatcher.
**Status:** [ ] planned

## E02-10: Matcher fusion (DTW + cosine prototype)
**Hypothesis:** DTW excels at temporal alignment, cosine prototype at global shape matching — they are complementary. A simple linear combination of normalized DTW score and 1-cosine(prototype) will outperform either alone.
**Description:** For each command, compute: (a) 1-NN DTW distance to nearest template, (b) cosine distance to the mean prototype vector (frame-averaged MFCC). Fuse: `score = α·dtw_score + (1-α)·cosine_score`. Sweep α and compare at matched FAR.
**Expected outcome:** α=0.6-0.7 gives 3-5pp rank-1 gain over DTW alone; fusion captures both temporal and shape information.
**Win condition:** ≥3pp rank-1 gain over DTW-only.
**Constraints:** Prototype computation is O(N) cheap; fusion adds negligible cost.
**How to run:** New fused matcher in TemplateMatcher or as a separate backend.
**Status:** [ ] planned
