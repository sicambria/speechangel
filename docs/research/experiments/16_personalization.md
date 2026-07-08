# Domain 16: Speaker Personalization & On-Device Adaptation

**Goal:** Enable the system to adapt to individual users over time with minimal labeled data, improving accuracy through personalization without compromising the deterministic, language-independent core.

**Enabling OSS:** `higher` (PyTorch meta-learning, Apache-2.0), `learn2learn` (MIT).

---

## E16-01: Per-user embedding shift (residual adapter)
**Hypothesis:** Instead of fine-tuning the entire encoder, training a small residual adapter (a 2-layer MLP, 10-50k params) that shifts the encoder's output embedding toward the user's acoustic space achieves comparable personalization gains with 100× fewer trained parameters.
**Score:** Impact=300 Feasibility=150 Constraints=180 Evidence=80 → **710 (A)**
**Description:** Add a small residual adapter block after the frozen encoder: `embedding_adapted = embedding + adapter(embedding)`. Train the adapter only on the user's enrolled templates (contrastive: same command = positive). Compare rank-1 vs frozen encoder vs full fine-tuning.
**Expected outcome:** Adapter improves rank-1 by 5-8pp, matching 80-90% of full fine-tuning gain at 1% of the parameter update cost. Adapter size: 10-50k params (< 100 KB).
**How to run:** Adapter architecture + per-user fine-tuning + TORGO per-speaker eval.

## E16-02: MAML (Model-Agnostic Meta-Learning) for rapid adaptation
**Hypothesis:** MAML pretraining produces encoder initializations that can adapt to a new speaker's voice with just 1-3 gradient steps on 3-5 enrollment examples, achieving better few-shot performance than standard pretraining.
**Score:** Impact=280 Feasibility=90 Constraints=170 Evidence=70 → **610 (B)**
**Description:** Pretrain encoder with MAML on MSWC: for each training task (a speaker), split their utterances into support (3-5 examples) and query sets. Inner loop: gradient steps on support. Outer loop: meta-gradient through query loss. Evaluate TORGO rank-1 after MAML adaptation.
**Expected outcome:** MAML-pretrained encoder achieves 3-5pp higher rank-1 at 3-shot enrollment vs standard-pretrained encoder. The meta-learned initialization is "closer" to any new speaker's optimum.
**How to run:** MAML pretraining + few-shot adaptation + TORGO eval.

## E16-03: Online prototype refinement (streaming mean update)
**Hypothesis:** As the user uses the system, confirmed matches provide valuable new examples of each command. Updating the prototype as a running weighted average (α_new=0.8 recent, 0.2 historical) improves prototype quality without needing explicit re-enrollment.
**Score:** Impact=260 Feasibility=240 Constraints=200 Evidence=80 → **780 (A)**
**Description:** When a match is confirmed (user doesn't reject or the action is correct per confirmation-gated logic), add the query embedding to that command's prototype with weight α. Older examples decay exponentially. Compare prototype quality (rank-1) vs static prototype over simulated usage sessions.
**Expected outcome:** Online refinement improves rank-1 by 3-5pp over 50+ confirmed uses. The prototype naturally tracks voice drift. Confirmation-gating prevents contamination from false accepts.
**How to run:** Streaming prototype update + simulated session eval.

## E16-04: Confirmation-gated hard negative mining
**Hypothesis:** When the user rejects a match and manually selects the correct command, the rejected pair (query embedding, wrong command) is a valuable hard negative. Adding rejected queries as negative examples for the wrong command improves discrimination.
**Score:** Impact=250 Feasibility=230 Constraints=200 Evidence=70 → **750 (A)**
**Description:** Track rejection events: user said X, system matched Y, user corrected to X. Store query embedding as a hard negative for command Y (and a positive for X). Adjust prototype comparison: penalize commands that have nearby hard negatives.
**Expected outcome:** 5-10pp reduction in repeat confusions. The system learns from its mistakes — the most valuable training signal.
**How to run:** Rejection tracking + negative bank + prototype scoring adjustment.

## E16-05: Federated personalization (privacy-preserving)
**Hypothesis:** Aggregating adapter updates across multiple users (via federated averaging) improves the base adapter initialization without sharing raw audio. SpeechAngel could benefit from federated learning across consenting users while maintaining complete audio privacy.
**Score:** Impact=240 Feasibility=50 Constraints=120 Evidence=60 → **470 (C)**
**Description:** Federated averaging of adapter weights across simulated users. Each user trains locally on their own data; only adapter deltas are shared. Measure: (a) improvement over purely-local adaptation, (b) privacy guarantees (differential privacy noise).
**Expected outcome:** Federated initialization improves rank-1 by 2-3pp over local-only, especially for users with very few enrollment examples (cold-start problem).
**How to run:** Federated simulation across TORGO speakers + adapter aggregation.
**Status:** Long-term — requires multi-device deployment and consent framework.

## E16-06: Voice condition detection and adaptation trigger
**Hypothesis:** Automatic detection of voice condition change (e.g., morning voice vs evening voice, good day vs bad day) via embedding drift can trigger proactive re-enrollment suggestions: "Your voice sounds different today. Want to re-teach the commands?"
**Score:** Impact=200 Feasibility=200 Constraints=190 Evidence=50 → **640 (B)**
**Description:** Maintain a moving average of query-vs-prototype embedding distance. When the moving average exceeds a threshold (3σ above the baseline mean), flag a voice condition change. Prompt the user for re-enrollment or automatically switch to condition-matched templates.
**Expected outcome:** Condition detection accuracy >80% for large voice changes (tired, ill). Enables proactive re-enrollment, reducing FRR during degraded voice days.
**How to run:** Embedding drift monitoring + condition detection + re-enrollment prompt eval.

## E16-07: Template quality scoring and ranking
**Hypothesis:** Not all enrolled templates are equally useful — some may be poorly recorded, others may be excellent. Scoring templates by their "representativeness" (distance to prototype, cross-validation consistency) and using only the top-k for matching improves accuracy.
**Score:** Impact=220 Feasibility=250 Constraints=200 Evidence=70 → **740 (A)**
**Description:** For each command's templates, compute quality score: (a) distance to command prototype (lower = more representative), (b) leave-one-out cross-validation accuracy (was this template correctly matched to its command?). Use top-k quality templates for matching. Sweep k.
**Expected outcome:** Top-3 quality templates achieve same or better rank-1 as top-5 random templates — fewer templates, less compute, better accuracy.
**How to run:** Quality scoring + top-k selection + TorgoEval per template count.

## E16-08: Cross-session template retirement (temporal decay)
**Hypothesis:** Templates from weeks/months ago may no longer match the user's current voice (voice drift). Applying temporal decay — older templates receive lower weight in the prototype — keeps the system aligned with the user's current voice.
**Score:** Impact=240 Feasibility=250 Constraints=200 Evidence=70 → **760 (A)**
**Description:** When computing prototype, weight each template by `w = exp(-λ * age_in_days)`. Sweep λ (decay rate). Compare rank-1 with temporal decay vs uniform-weight prototype on longitudinal TORGO data (multi-session).
**Expected outcome:** Temporal decay improves rank-1 by 3-5pp on sessions separated by >2 weeks. Automatically handles voice drift without explicit re-enrollment.
**How to run:** Temporal weighting + longitudinal session eval.

## E16-09: Enrollment voice guidance (real-time quality feedback)
**Hypothesis:** During enrollment, real-time feedback on recording quality (SNR, clipping, duration, speaking rate) guides the user to produce better templates. "Speak a bit louder" / "That was too fast, try again" improves template quality at enrollment time.
**Score:** Impact=200 Feasibility=230 Constraints=200 Evidence=60 → **690 (B)**
**Description:** After each enrollment recording, compute: (a) estimated SNR, (b) clipping %, (c) duration, (d) speaking rate (syllables/sec). Provide simple feedback: green check for good, yellow warning with suggestion. Compare template quality of guided vs unguided enrollment.
**Expected outcome:** Guided enrollment produces templates with 20-30% lower intra-class variance, translating to 2-4pp rank-1 improvement at test time.
**How to run:** Quality metrics extraction + guided UX + template quality comparison.

## E16-10: Cross-device template transfer (phone ↔ watch ↔ speaker)
**Hypothesis:** A user may enroll commands on their phone but also use a smart speaker or watch. Transferring template prototypes across devices (scaled by device-specific calibration factors) enables multi-device use with single enrollment.
**Score:** Impact=180 Feasibility=130 Constraints=140 Evidence=40 → **490 (C)**
**Description:** Record same commands on phone and smart speaker. Learn a device-specific affine transform (mean + scale shift per embedding dimension) that maps phone embeddings to speaker embeddings. Apply transform to transfer phone-enrolled templates to the speaker.
**Expected outcome:** Transferred templates achieve 80-90% of natively-enrolled rank-1. Reduces enrollment burden for multi-device households.
**How to run:** Device calibration recording + affine transform estimation + cross-device eval.
**Status:** Medium-term — requires multi-device setup.
