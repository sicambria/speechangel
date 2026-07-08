# Domain 12: Matcher Architecture Innovation

**Goal:** Find matching algorithms that go beyond DTW to maximize discrimination at matched FAR, with a focus on techniques that exploit the matcher×representation interaction (the CP-1 2×2 finding).

**Enabling OSS:** `tslearn` (Python DTW variants, BSD), `dtaidistance` (fast DTW, Apache-2.0), `nmslib` (approximate nearest neighbors, Apache-2.0).

---

## E12-01: Siamese neural distance metric (learned DTW cost)
**Hypothesis:** Instead of Euclidean distance between MFCC frames, a small Siamese network (2-layer MLP: (frame_a, frame_b) → scalar distance) can learn a task-optimized local distance metric that improves DTW alignment for dysarthric speech.
**Score:** Impact=280 Feasibility=130 Constraints=170 Evidence=70 → **650 (B)**
**Description:** Train a Siamese MLP on MFCC frame pairs from TORGO. Positive pairs: frames from same command; negative: different commands. Replace Euclidean in DTW with learned distance. Must be deterministic after training. Compare rank-1 vs Euclidean DTW.
**Expected outcome:** 3-7pp rank-1 gain. The learned metric de-emphasizes noisy MFCC dimensions and emphasizes discriminative ones for this specific speaker/task.
**How to run:** Siamese training → export weights → learned-distance DTW in Kotlin.

## E12-02: Graph-based approximate nearest neighbor (HNSW) for fast retrieval
**Hypothesis:** HNSW (Hierarchical Navigable Small World) graphs provide O(log N) approximate nearest-neighbor search in the embedding space, enabling real-time matching against 100+ templates with negligible accuracy loss.
**Score:** Impact=180 Feasibility=220 Constraints=190 Evidence=80 → **670 (B)**
**Description:** Implement HNSW index over stored template embeddings. Replace exhaustive cosine search with HNSW k-NN. Measure speedup and recall@1 vs exact search.
**Expected outcome:** 10-50× speedup vs exhaustive at recall@1 >99%. Enables scaling to 100+ commands without linear slowdown.
**How to run:** HNSW impl (or reuse `nmslib` Java port) + embedding index + benchmark.

## E12-03: Inverted-file DTW (fast approximate DTW retrieval)
**Hypothesis:** For MFCC sequences, clustering templates by their frame-averaged feature vector and using an inverted index to prune DTW candidates reduces DTW computation by 80-90% at ≤1pp rank-1 loss, solving the O(N×T) scaling problem.
**Score:** Impact=200 Feasibility=180 Constraints=200 Evidence=60 → **640 (B)**
**Description:** Build inverted index: cluster templates by their per-command mean MFCC vector. For a query, only run DTW against templates in the top-k nearest clusters. Sweep k and cluster count to find optimal accuracy-vs-speed trade-off.
**Expected outcome:** 80-90% DTW computation reduction at ≤1pp rank-1 loss. Critical for scaling beyond 25 commands.
**How to run:** Inverted index + cluster-pruned DTW in TemplateMatcher.

## E12-04: Early-termination DTW (pruning during alignment)
**Hypothesis:** During DTW computation, if the accumulated distance at any alignment point exceeds the current best distance (for a different command) by a margin, the DTW can be terminated early — saving 50-70% of computation without affecting the final decision.
**Score:** Impact=160 Feasibility=260 Constraints=200 Evidence=70 → **690 (B)**
**Description:** Add early-termination to DTW: maintain `current_best_distance` across commands. If `accumulated[i][j] * (1 + remaining_steps_weight) > current_best_distance`, stop computing this command's DTW. Measure speedup and verify no rank-1 change.
**Expected outcome:** 50-70% DTW compute reduction, zero accuracy loss (provably correct — the lower bound is conservative).
**How to run:** Early-termination logic in Dtw.kt.

## E12-05: Open-set prototype networks (Prototypical Networks for OOV)
**Hypothesis:** Prototypical Networks' distance-to-prototype scoring naturally handles open-set rejection: the query's distance to the nearest prototype, normalized by the average prototype spread, is a better OOV detector than DTW threshold alone.
**Score:** Impact=260 Feasibility=180 Constraints=180 Evidence=80 → **700 (A)**
**Description:** For each enrolled command, compute prototype (mean embedding) and spread (std of embedding distances). Score = distance(query, prototype) / (spread + ε). Reject if score > τ for all commands. Compare OOV rejection rate vs DTW threshold at matched in-vocab FRR.
**Expected outcome:** OOV rejection improves by 20-40% at matched in-vocab FRR. The spread normalization is the key — commands with tight intra-class clusters receive stricter rejection.
**How to run:** Prototype + spread scoring in QbeSpeechBackend, open-set eval.

## E12-06: Momentum contrastive queue (MoCo-style negative bank)
**Hypothesis:** For downstream matching, negative examples from a large queue of past utterances (stored as embeddings) provide richer contrast than the limited set of enrolled commands. A MoCo-style dynamic queue of recent queries improves prototype-vs-background discrimination.
**Score:** Impact=220 Feasibility=140 Constraints=160 Evidence=80 → **600 (B)**
**Description:** Maintain a FIFO queue of 1024 recent query embeddings. For each new query, compute contrastive score: distance to nearest prototype divided by mean distance to queue negatives. This provides a dynamically-updated background model.
**Expected outcome:** Dynamic queue reduces FAR by 30-50% vs static prototype-only matching by providing an always-updating noise floor estimate.
**How to run:** MoCo queue in QbeSpeechBackend, AmbientFar eval.

## E12-07: Transductive few-shot inference (label propagation)
**Hypothesis:** When multiple unlabeled queries arrive in a session (typical for always-on), transductive inference — jointly classifying all queries by propagating labels through their embedding-space graph — improves accuracy over independent per-query classification by exploiting within-session consistency.
**Score:** Impact=200 Feasibility=130 Constraints=160 Evidence=60 → **550 (B)**
**Description:** After each query, store its embedding. When a new query arrives, construct a k-NN graph over (enrolled templates + recent queries). Propagate labels via Label Spreading. Classify new query by its propagated label.
**Expected outcome:** 2-4pp rank-1 gain in sessions with ≥5 queries. Exploits the fact that in a session, the user tends to repeat the same subset of commands.
**How to run:** Label propagation on embedding graph, session-level eval.

## E12-08: Differentiable DTW with learned step pattern
**Hypothesis:** The standard DTW step pattern (symmetric with no local constraints beyond Sakoe-Chiba band) may not be optimal. A parameterized step pattern with learnable transition costs, trained via Soft-DTW on dysarthric data, will improve alignment quality.
**Score:** Impact=180 Feasibility=100 Constraints=180 Evidence=50 → **510 (C)**
**Description:** Implement learned step pattern: transition cost matrix with 3 learnable parameters (horizontal, vertical, diagonal weights). Optimize via Soft-DTW gradient on training data. Freeze and use in standard DTW.
**Expected outcome:** 1-3pp rank-1 gain. Learned patterns penalize large warping steps more than symmetric pattern, reducing pathological alignments.
**How to run:** Learned step pattern training + frozen-DTW eval.

## E12-09: Runtime-synthesized negative templates via audio augmentation
**Hypothesis:** At enrollment time, synthesize 10-20 "negative template" variants of each command by applying pitch shift, time stretch, noise, and reverb — then enroll them as explicit negatives for other commands. This provides tighter decision boundaries without requiring real negative examples.
**Score:** Impact=280 Feasibility=240 Constraints=200 Evidence=70 → **790 (A)**
**Description:** When a new command is enrolled, generate augmented variants. For each existing command, check if the new command's variants are "too close." If so, add the variant as an explicit negative template: score = min(distance to command templates) / max(distance to negative templates, ε).
**Expected outcome:** 10-20% rel FRR reduction by preventing cross-command leakage. The augmented negatives create a "safety margin" around each command's cluster.
**How to run:** AudioAugment negative synthesis + TemplateMatcher negative scoring.

## E12-10: Metric learning on DTW alignment paths (path-constrained embedding)
**Hypothesis:** The DTW alignment path itself encodes useful information about HOW two utterances match — a "straight" path (near-diagonal) indicates similar timing; a "crooked" path indicates irregular tempo. Using the path + distance as a joint feature for a binary "same-command" classifier improves over distance-only scoring.
**Score:** Impact=200 Feasibility=160 Constraints=180 Evidence=50 → **590 (B)**
**Description:** Extract features from DTW path: (a) mean deviation from diagonal, (b) variance of slope, (c) fraction of path within diagonal band, (d) number of path segments with slope >2 or <0.5. Train small logistic regression "same command?" classifier. Score = sigmoid(β·[distance, path_features]).
**Expected outcome:** Path features add 2-4pp rank-1 by identifying "crooked" alignments that indicate irregular timing (common in dysarthria) and downweighting their distance.
**How to run:** Path feature extraction in Dtw.kt + logistic regression in TemplateMatcher.
