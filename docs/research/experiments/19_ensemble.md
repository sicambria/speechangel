# Domain 19: Ensemble & Cascade Architecture Design

**Goal:** Design multi-stage recognition architectures that cascade from cheap to expensive models, fuse complementary matchers, and combine multiple decision signals for maximum accuracy at minimum computation.

---

## E19-01: Three-stage cascade (energy → MFCC-DTW → QbE embedding)
**Hypothesis:** A cascade that routes queries through increasingly expensive but accurate matchers — (1) energy VAD gate (filters 80% of frames), (2) MFCC-DTW (filters 90% of remaining), (3) QbE embedding cosine (final decision) — achieves the accuracy of the expensive QbE matcher at near the compute cost of the cheap DTW matcher, because most queries are resolved early.
**Score:** Impact=320 Feasibility=200 Constraints=190 Evidence=80 → **790 (A)**
**Description:** Build cascade: Stage-1: energy VAD gate (cheap, filters silence). Stage-2: MFCC-DTW with permissive threshold (leave 10-20% of queries un-resolved in the "uncertain" zone). Stage-3: QbE embedding cosine for uncertain queries only. Measure: (a) accuracy vs pure-QbE, (b) compute vs pure-QbE, (c) cascade rejection rate (queries resolved per stage).
**Expected outcome:** Cascade achieves >95% of pure-QbE accuracy at <30% of pure-QbE compute. The permissive Stage-2 resolves the clear cases; Stage-3 handles the ambiguous ones.
**How to run:** Three-stage cascade implementation + accuracy-vs-compute curve.

## E19-02: Multi-matcher voting (DTW + cosine + segmental)
**Hypothesis:** Fusing 3+ complementary matchers (DTW for temporal alignment, cosine prototype for global shape, segmental DTW for multi-word commands) via soft voting (weighted average of confidences) reduces FRR by outperforming any single matcher.
**Score:** Impact=280 Feasibility=200 Constraints=180 Evidence=70 → **730 (A)**
**Description:** Run 3 matchers independently: (1) MFCC-DTW, (2) embedding cosine prototype, (3) segmental DTW. Fuse: vote = ensemble weighted average of per-command confidence scores. Weights optimized on held-out data. Compare rank-1 vs best single matcher.
**Expected outcome:** Ensemble improves rank-1 by 3-5pp over best single matcher. Different matchers fail on different queries — the ensemble covers the weaknesses of each.
**How to run:** Multi-matcher ensemble + weight optimization + TORGO eval.

## E19-03: Matcher gating network (learned router)
**Hypothesis:** Instead of fixed ensemble weights, a small gating network (MLP: utterance features → {which matcher to trust}) can learn per-utterance which matcher is most reliable, routing each query to the right expert.
**Score:** Impact=260 Feasibility=150 Constraints=180 Evidence=60 → **650 (B)**
**Description:** Train a 10k-param gating MLP that takes utterance-level features (duration, energy variance, spectral centroid, speaking rate) and predicts which matcher (DTW or cosine or both) will be correct. Use confidence of the routed matcher. Compare vs fixed ensemble.
**Expected outcome:** Gated routing improves over fixed ensemble by 1-3pp by routing each query to the right expert. Speaking rate is the strongest routing feature (DTW better for slow speech, cosine better for fast).
**How to run:** Gating network training + routed inference + TORGO eval.

## E19-04: Stacked generalization (meta-classifier over matchers)
**Hypothesis:** A meta-classifier (logistic regression or small MLP) trained on the output scores of multiple matchers (DTW distance, cosine distance, confidences, path features) as input features learns to make the final command decision, outperforming any weighted fusion rule.
**Score:** Impact=280 Feasibility=180 Constraints=180 Evidence=80 → **720 (A)**
**Description:** For each query, collect per-matcher outputs: (DTW distance, cosine distance, confidences, margin, path deviation, etc.) as a flat feature vector. Train a meta-classifier (logistic regression with L2 regularization) to predict the correct command from these features. Compare rank-1 vs best single matcher and simple fusion.
**Expected outcome:** Meta-classifier improves rank-1 by 2-4pp over simple fusion. The learned non-linear combination captures matcher interactions that linear fusion misses.
**How to run:** Meta-feature extraction + logistic regression training + TORGO eval.

## E19-05: Calibrated confidence cascade with oracle stopping
**Hypothesis:** A cascade where each stage outputs a calibrated confidence (Platt-scaled probability) and stops when confidence exceeds a threshold. This achieves the cascade's compute savings while maintaining accuracy guarantees — the system can promise "I'm X% sure this is correct" and escalate uncertain cases.
**Score:** Impact=260 Feasibility=200 Constraints=190 Evidence=70 → **720 (A)**
**Description:** Calibrate each stage's confidence via Platt scaling on held-out data. Set cascade thresholds: Stage-1 confidence >0.95 → accept (no further stages). Stage-2 confidence >0.95 → accept. Stage-3 always outputs final decision. Measure: (a) fraction resolved per stage, (b) accuracy vs oracle, (c) confidence calibration error (ECE).
**Expected outcome:** 70-85% of queries resolved at Stage-1/2 with >95% calibrated confidence. ECE <0.05 at all stages. The calibration makes the cascade trustworthy — the user sees "95% sure" and it actually means 95%.
**How to run:** Confidence calibration (E09-04) + cascade + ECE measurement.

## E19-06: Wake-word gating with command confirmation (two-gate architecture)
**Hypothesis:** A wake word followed immediately by a command should show temporal consistency: the same speaker within 5 seconds, consistent energy levels. Verifying these temporal/energy consistencies adds a "second gate" that reduces false command triggers by 30-50%.
**Score:** Impact=240 Feasibility=230 Constraints=200 Evidence=60 → **730 (A)**
**Description:** After wake detection, before Stage-2 command recognition, verify: (a) energy level of command segment is within 3× of wake segment (same speaker distance), (b) spectral centroid is within 2× of wake, (c) gap between wake and command is <3s. Reject as "not a command" if verification fails.
**Expected outcome:** Temporal-energy consistency check reduces false command triggers by 30-50% with <2pp command rejection. Ambient sounds that trigger the wake gate but don't have the consistency signature of a wake-then-command pattern are filtered.
**How to run:** Consistency features + verification gate + WakeGatedRecognizer eval.

## E19-07: Early-exit ensemble (incremental depth)
**Hypothesis:** An encoder with multiple exit heads at different depths — shallow (layer 2: fast, less accurate), medium (layer 4), deep (layer 6: slow, most accurate) — can exit early for easy queries and go deeper for hard ones. An integrated cascade in one model.
**Score:** Impact=240 Feasibility=110 Constraints=170 Evidence=60 → **580 (B)**
**Description:** Train encoder with exit classifiers at layers 2, 4, 6. At inference: compute layer-2 embedding, if confidence > threshold, exit. Otherwise, compute layer-4, same logic. Otherwise, layer-6. Measure accuracy-vs-compute Pareto curve.
**Expected outcome:** 60-70% of queries exit at layer 2 (fastest). 20-30% at layer 4. 5-10% at layer 6 (slowest). Average compute <50% of layer-6-only. Accuracy within 1pp of layer-6-only.
**How to run:** Multi-exit encoder training + early-exit inference + accuracy-vs-latency curve.

## E19-08: Cross-modal consistency check (audio + accelerometer)
**Hypothesis:** On a phone, the accelerometer can detect when the user is speaking (jaw/mouth vibration transmitted through contact). Correlating audio energy peaks with accelerometer vibration peaks provides a "liveness check" that rejects recorded/replayed audio attacks and reduces ambient false accepts.
**Score:** Impact=200 Feasibility=140 Constraints=160 Evidence=40 → **540 (C)**
**Description:** Register accelerometer listener during listening. Compute cross-correlation between audio energy and accelerometer magnitude. If peak correlation <0.3 (no vibration when there should be), flag as "probably not the user speaking" — increase rejection threshold.
**Expected outcome:** Accelerometer correlation reduces ambient false accepts by 20-40% when phone is in hand or on table (contact-transmitted vibration). Not effective when phone is on a soft surface.
**How to run:** Accelerometer + audio correlation + ambient FA measurement.
**Status:** Optional — requires sensor access, only works in some phone positions.

## E19-09: One-vs-rest binary classifier bank (per-command detectors)
**Hypothesis:** Instead of 1-NN prototype matching over all commands, training a small binary classifier per command (Is this "go home" or not?) creates independent decision boundaries for each command, naturally handling open-set rejection and threshold optimization per command.
**Score:** Impact=260 Feasibility=140 Constraints=170 Evidence=70 → **640 (B)**
**Description:** For each enrolled command, train a small binary classifier (logistic regression on embedding + DTW features) on: (a) that command's templates = positive, (b) all other commands' templates + negative bank = negative. At inference: each classifier votes independently. Classify as the command with highest probability above threshold.
**Expected outcome:** Per-command binary classifiers improve rank-1 by 3-5pp over prototype matching by learning command-specific decision boundaries. Each classifier is tiny (10-50 params) and fast.
**How to run:** Per-command binary classifier training + independent-voting inference + TORGO eval.

## E19-10: Uncertainty-aware rejection (conformal prediction)
**Hypothesis:** Conformal prediction provides distribution-free confidence sets with guaranteed coverage: for a user-specified error rate α, the system returns a set of commands that contains the true command with probability ≥1-α. If the set is empty, reject. If singleton, accept. If multiple, ask for disambiguation.
**Score:** Impact=220 Feasibility=150 Constraints=180 Evidence=80 → **630 (B)**
**Description:** Calibrate conformal predictor on held-out enrollment data: compute nonconformity scores (1 - cosine_similarity) for each command. For a new query, include command c in the prediction set if its nonconformity score ≤ calibrated threshold. Reject if set empty. Measure: (a) set size distribution, (b) coverage guarantee fulfillment, (c) rejection rate.
**Expected outcome:** Conformal prediction provides mathematically-guaranteed error control. For α=0.05 (95% coverage), average set size 1.2-1.8 (usually singleton, sometimes 2-3 commands need disambiguation). Rejection rate <2%.
**How to run:** Conformal predictor calibration + prediction-set inference + coverage verification.
