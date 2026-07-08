# Domain 09: Operating Point & Threshold Optimization

**Goal:** Find the threshold strategy that minimizes FRR at the target FAR budget (≤5% for Stage-2 commands, ≤0.5 FA/hr for Stage-1 wake), with thresholds that generalize held-out.

**Current baseline:** Global acceptance threshold = 8.0 (DTW distance scale). Per-command calibration = non-improvement (held-out FAR balloons to 24-34%). ThresholdCalibrator is in-sample → optimistic in the field.

**Key insight from EVAL-002/003:** Threshold selection must be held-out (leave-one-fold-out). Per-command calibration is not a free lunch — it reduces degrees of freedom and inflates held-out FAR. The approach is: calibrate thresholds held-out, and compare methods at matched (realized, not intended) FAR.

---

## E09-01: Global threshold sweep (EER and low-FAR operating points)
**Hypothesis:** The single global threshold that minimizes EER (or FRR at target FAR) varies by front-end, matcher, and speaker population. A systematic sweep identifies the optimal point for each configuration.
**Description:** Sweep global threshold from 0.5 to 20.0 in 0.25 steps. For each threshold, compute held-out FRR and FAR (via leave-one-fold-out). Report EER and FRR at predefined FAR targets (1%, 5%, 10%, 20%). This is the baseline operating curve.
**Expected outcome:** EER for MFCC-DTW on TORGO is ~30-35%. FRR @ FAR=5% is ~76% (consistent with existing measurements). The curve shape confirms whether DTW distance has a usable discriminative range.
**Win condition:** Baseline DET curve established for all major pipeline configurations.
**How to run:** Global threshold sweep in TorgoEval, per-configuration.
**Status:** [ ] planned

## E09-02: Command-level threshold calibration held-out
**Hypothesis:** The per-command calibration failure (held-out FAR 24-34%) came from calibrating on the same data. Leave-one-fold-out calibration (calibrate threshold on train folds, evaluate on held-out fold) will restore per-command calibration's benefit: lower FRR at the same global FAR budget, without FAR inflation.
**Description:** For each command, calibrate threshold on train folds to bound false accepts within the per-command FAR budget (= total_budget / N_commands). Evaluate on the held-out fold. Compare FRR of held-out per-command thresholds vs held-out global threshold at matched realized FAR.
**Expected outcome:** Held-out per-command calibration reduces FRR by 5-15% rel vs global threshold at matched FAR, by tightening thresholds for "easy" commands and loosening for "hard" ones within the global budget.
**Win condition:** ≥5% rel FRR reduction at matched FAR vs global threshold.
**How to run:** Held-out threshold calibration in TorgoEval (leave-one-fold-out per command).
**Status:** [ ] planned

## E09-03: Budget allocation strategies (equal vs proportional vs adaptive)
**Hypothesis:** Equal FAR budget split (each command gets 1/N of the total FA budget) is suboptimal. Commands with high intra-class variability need a larger budget to avoid excessive rejection. An adaptive split based on intra-class DTW spread will reduce overall FRR.
**Description:** Compare budget allocation strategies: (a) equal split (current), (b) proportional to intra-class DTW variance, (c) proportional to template count, (d) optimization-based (minimize expected FRR given total budget via linear programming). Evaluate held-out FRR at target FAR.
**Expected outcome:** Variance-proportional allocation reduces FRR by 3-7% rel vs equal split. The gains come from giving more budget to "hard" commands (high intra-class variability) without starving "easy" ones.
**Win condition:** ≥3% rel FRR reduction vs equal-split calibration.
**How to run:** Budget allocation strategies in ThresholdCalibrator, held-out eval.
**Status:** [ ] planned

## E09-04: Confidence-score calibration (Platt scaling / isotonic regression)
**Hypothesis:** The raw confidence score `(1 - distance/threshold)` is not well-calibrated — a score of 0.8 does not mean 80% probability of correct match. Platt scaling (logistic regression on raw scores) or isotonic regression will calibrate confidence to be a reliable "probability of correct match," enabling better rejection decisions.
**Description:** Fit Platt scaling (or isotonic regression) to map raw DTW confidence scores to calibrated probabilities using a held-out calibration set. Measure calibration error (ECE — expected calibration error) and the effect on rejection decisions at various confidence thresholds.
**Expected outcome:** Raw confidence is moderately miscalibrated (ECE ~0.1-0.2). Platt scaling reduces ECE to ≤0.05. Calibrated confidence enables reliable "only accept if ≥95% confident" behavior.
**Win condition:** ECE ≤ 0.05 post-calibration.
**How to run:** Platt scaling fit on train folds, ECE measurement on held-out fold.
**Status:** [ ] planned

## E09-05: Operating point selection by cost ratio (C_miss / C_fa)
**Hypothesis:** The optimal operating point depends on the relative cost of a miss (user must repeat command = annoyance) vs a false accept (wrong action executed = trust erosion). A cost-ratio framework lets the user or caregiver tune the sensitivity.
**Description:** Parameterize: `operating_point = argmin (C_miss * FRR + C_fa * FAR)`. Offer 3 preset cost ratios: (a) "lenient" (C_fa/C_miss=5 — prioritize avoiding wrong actions), (b) "balanced" (C_fa/C_miss=1), (c) "sensitive" (C_fa/C_miss=0.2 — prioritize catching all commands). Map each to the corresponding threshold.
**Expected outcome:** "Lenient" mode: higher threshold, lower FAR/higher FRR. "Sensitive": lower threshold, higher FAR/lower FRR. Spans ~15-20pp FRR and ~10× FAR trade-off. Users with severe impairment prefer "sensitive" (catching every command matters more than occasional false fires that can be dismissed).
**Win condition:** 3 useful operating points spanning the meaningful trade-off range.
**How to run:** Cost-ratio threshold selection, DET curve analysis.
**Status:** [ ] planned

## E09-06: Multi-template threshold interaction (how does threshold scale with N templates?)
**Hypothesis:** As more templates are enrolled per command, the min-DTW distance to the nearest template decreases (more chances to find a good match). The acceptance threshold should decrease proportionally to maintain the same FAR. The scaling relationship is threshold(N) ∝ threshold(1) * f(N) where f(N) needs measurement.
**Description:** Measure the min-DTW distance distribution for same-command (true) and different-command (false) as a function of template count N=1..10. Fit the scaling curve for the acceptance threshold. Verify that threshold f(N) maintains constant FAR.
**Expected outcome:** Min-distance decreases roughly as 1/√N for true matches (standard extreme-value scaling) and as 1/N for false matches (more chances to accidentally find a close match). The optimal threshold should decrease as ~1/√N to maintain FAR.
**Win condition:** Quantified scaling law; threshold adaptation for multi-template.
**How to run:** Distance distribution analysis at varying template counts, TorgoEval.
**Status:** [ ] planned

## E09-07: Temporal threshold adaptation (short-term history)
**Hypothesis:** The optimal threshold drifts over minutes-to-hours on the same device (mic position shifts, background noise changes, user's voice warms up). A short-term adaptive threshold that tracks the running mean of recent "reject" distances can adjust to drift without explicit re-calibration.
**Description:** Maintain a running EMA (α=0.01-0.05) of the DTW distance for rejected utterances. Shift the acceptance threshold proportionally: `effective_threshold = base_threshold - β * (running_mean_reject_distance - baseline_reject_distance)`. Evaluate on long-duration (10+ minute) sessions.
**Expected outcome:** Adaptive threshold reduces FRR by 5-10% rel during long sessions where the fixed threshold drifts away from optimal due to acoustic changes.
**Win condition:** ≥5% rel FRR reduction on >5-minute continuous sessions.
**How to run:** Temporal threshold adaptation, long-session simulation from TORGO multi-session data.
**Status:** [ ] planned

## E09-08: Two-threshold hysteresis (accept / reject / uncertain)
**Hypothesis:** A single threshold creates instability near the boundary (slight acoustic variation flips between accept and reject). A hysteresis band — with a lower "accept" threshold and a higher "reject" threshold, and an "uncertain" zone between them — improves consistency.
**Description:** Define three regions: distance < T_low → accept, distance > T_high → reject, T_low ≤ distance ≤ T_high → uncertain. In the uncertain zone, use additional signal: (a) persistence (accept if n previous uncertains were accepts), (b) ask for confirmation (in the UX), (c) use a second matcher (dual-filter cascade).
**Expected outcome:** Hysteresis + confidence zone reduces flip-flop at the boundary by 50-70% at ≤2pp added FRR.
**Win condition:** ≥50% reduction in boundary flip-flop at ≤2pp added FRR.
**How to run:** Hysteresis logic in TemplateMatcher, boundary-instability measurement.
**Status:** [ ] planned

## E09-09: Population prior for threshold initialization
**Hypothesis:** A new user starts with no calibration data. Initializing the threshold from a population prior (the median optimal threshold for speakers with similar acoustic characteristics) provides a better starting point than the global default (8.0), reducing the number of interactions needed before the user reaches their optimal threshold.
**Description:** Cluster TORGO speakers by acoustic profile (F0 mean, formant spread, speaking rate, energy variance). For each cluster, compute the optimal cluster-median threshold. When a new user enrolls, classify their cluster from enrollment data and set initial threshold to the cluster median. Compare FRR after N interactions vs global default.
**Expected outcome:** Cluster-prior initialization reduces "ramp-up" time by 40-60% — the user reaches near-optimal FRR after half as many interactions.
**Win condition:** ≥40% reduction in interactions to reach 90% of optimal FRR.
**How to run:** Speaker clustering from enrollment features, cluster-median thresholds, new-user simulation.
**Status:** [ ] planned

## E09-10: Per-command rejection reason distribution (diagnostic tool)
**Hypothesis:** Different commands fail for different reasons — some are confused with specific other commands (confusion), some always fall below the global threshold (threshold mismatch), some have inconsistent enrollment (high intra-class variance). A per-command failure diagnosis enables targeted fixing.
**Description:** For each command in TORGO, break down failures by type: (a) confused with command X (incorrect command had lower distance), (b) rejected below threshold (correct command won but distance > threshold), (c) VAD failure (speech not detected). Report the top failure mode per command.
**Expected outcome:** ~40% of failures are confusion (wrong command won), ~50% are rejection (right command won but below threshold), ~10% are VAD failures. This breakdown determines whether to invest in better matching or better thresholding.
**Win condition:** Quantified failure-mode distribution per command, per speaker, per severity.
**How to run:** Per-command failure analysis in TorgoEval with rejection-reason tracking.
**Status:** [ ] planned
