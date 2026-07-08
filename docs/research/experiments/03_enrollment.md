# Domain 03: Template Enrollment Optimization

**Goal:** Maximize per-command discrimination with minimal enrollment burden, by optimizing template quality, diversity, and representation.

**Current baseline:** 1 template per command, Enroller trims + quality checks (min 8 speech frames). Multi-template stored, matched by min-DTW.

**Key insight:** Enrollment is the differentiator — it's what makes SpeechAngel unique. But poor enrollment (bad sample, wrong condition, insufficient variety) directly causes poor recognition. Optimizing enrollment is the cheapest accuracy lever.

---

## E03-01: Enrollment count sweep (1 vs 2 vs 3 vs 5 vs 10 templates)
**Hypothesis:** Rank-1 saturates at 3-5 templates/command for control speakers, 5-7 for dysarthric. Beyond that, within-condition redundancy adds no discrimination. This determines the UX cost (how many recordings to ask for) vs accuracy payoff.
**Description:** For each TORGO speaker, enroll 1/2/3/5/10 templates per command (held-out folds for query). Measure rank-1 and FRR-vs-FAR curves at each size. Report the saturating curve.
**Expected outcome:** 1→2: +15pp, 2→3: +5pp, 3→5: +2pp, 5→10: +1pp. Saturation at 3-5 for control, 5-7 for dysarthric.
**Win condition:** Quantity the exact per-user saturation curve. The win is knowing the optimal enrollment ask.
**How to run:** TorgoEval with variable enroll counts.
**Status:** [ ] planned

## E03-02: Quality-filtered enrollment (reject low-SNR, clipped, or short templates)
**Hypothesis:** Enrolling bad-quality samples (clipped, noisy, too short/quiet) degrades recognition more than having fewer templates. Automatic quality filtering with strict thresholds will improve rank-1 at the same enrollment count.
**Description:** Add quality metrics to Enroller: (a) SNR estimate (signal RMS / noise-floor RMS), (b) clipping detection (% samples at ±1.0), (c) effective duration (VAD-trimmed length). Reject templates below quality thresholds. Sweep thresholds; compare filtered-vs-unfiltered rank-1.
**Expected outcome:** At threshold SNR≥10dB, clip%<5%, duration≥1.0s: rank-1 improves 3-5pp vs unfiltered same-count enrollment (fewer templates but all clean).
**Win condition:** ≥3pp rank-1 gain at matched enrollment count.
**Constraints:** Quality thresholds must not reject >30% of user attempts (usability).
**How to run:** Extend Enroller with quality gates, TorgoEval.
**Status:** [ ] planned

## E03-03: Diverse enrollment (maximize intra-command template variety)
**Hypothesis:** Not all diverse enrollments are beneficial — enrolling a very distorted ("tired") version alongside a "normal" version increases intra-command spread, which can increase confusion with other commands. There is a sweet spot: diverse enough to capture voice variation, not so diverse that cluster boundaries blur.
**Description:** On TORGO, which has multiple sessions per speaker spanning weeks, compare: (a) enroll from earliest session only, (b) enroll from latest session only, (c) enroll spanning all sessions (temporal diversity). Measure rank-1 and inter-command confusion at each.
**Expected outcome:** Temporal diversity (c) beats single-session (a/b) by 5-10pp rank-1 on speakers where voice changed across sessions.
**Win condition:** ≥5pp rank-1 gain with multi-session enrollment vs single-session.
**How to run:** TorgoEval with session-aware enrollment splits.
**Status:** [ ] planned

## E03-04: Prototype enrollment (few-shot averaging)
**Hypothesis:** Instead of storing all enrolled templates and matching by min-DTW, compute a single "prototype" per command by frame-aligning templates (via DTW barycenter averaging / DBA) and storing the averaged sequence. Single-prototype matching reduces compute and may improve generalization.
**Description:** For each command, compute DBA (iteratively align all templates to a reference, average aligned frames, repeat). Store DBA prototype. Match with DTW: query → prototype. Compare 1-prototype vs k-template min-DTW.
**Expected outcome:** DBA prototype matches or beats 3-template min-DTW at 1/3 the storage and computation — effective compression.
**Win condition:** rank-1 within 2pp of k-template at significantly reduced storage.
**Constraints:** DBA computation on-device must complete in <1s for typical command.
**How to run:** Implement DBA, integrate into Enroller/Matcher, bake-off.
**Status:** [ ] planned

## E03-05: Condition-aware template selection (NORMAL/TIRED/ILL)
**Hypothesis:** Templates labeled with `VoiceCondition` and selected by the nearest condition to the current voice state will outperform random template selection. A user who is tired should match against their "TIRED" templates.
**Description:** On TORGO, label sessions by intelligibility/severity as proxy for VoiceCondition. Compare: (a) match against all templates, (b) match against condition-matched templates only based on a "morning vs evening" or "session adjacency" oracle.
**Expected outcome:** Condition-matched matching improves rank-1 by 5-8pp when the condition gap is large (e.g., dysarthric severe-vs-mild sessions).
**Win condition:** ≥5pp gain on high-condition-variability speakers.
**How to run:** ConditionEval with session labels; TorgoCorpus extension.
**Status:** [ ] planned

## E03-06: Active enrollment (interactive selection)
**Hypothesis:** Instead of blindly enrolling N samples, an active strategy suggests: "say it louder," "say it slower," "say it when you're tired" — targeting specific condition dimensions that maximize coverage. This gets more discriminative enrollment with fewer recordings.
**Description:** Simulate active enrollment: after each enrollment, compute the intra-command DTW spread and the inter-command nearest-neighbor distance. If intra > 0.5 × inter, ask for a more distinct sample; if intra is small, ask for a variant (different energy, speed). Compare active-vs-random enrollment order.
**Expected outcome:** Active enrollment reaches saturation rank-1 with 2 fewer recordings than random enrollment — reducing user burden by 30-40%.
**Win condition:** Same rank-1 with ≥30% fewer enrollments.
**How to run:** Simulate in eval; UX implementation is app-side.
**Status:** [ ] planned

## E03-07: Channel-robust enrollment (multiple device conditions)
**Hypothesis:** Enrolling with the phone at different distances/angles (near-mouth, arm's-length, on-table) captures acoustic variability that improves far-field recognition, without needing a far-field corpus.
**Description:** Apply RIR convolution + distance attenuation (60cm, 120cm, 200cm) to TORGO enrollment samples. Compare: (a) near-field enrollment only, (b) multi-distance enrollment. Test queries at various distances.
**Expected outcome:** Multi-distance enrollment reduces FRR at far-field (120cm+) by 10-20% rel vs near-field only enrollment.
**Win condition:** ≥10% rel FRR reduction at far-field operating point.
**How to run:** AudioAugment distance simulation + multi-condition enrollment, ConditionEval.
**Status:** [ ] planned

## E03-08: Template pruning (remove redundant enrollments)
**Hypothesis:** Some enrolled templates are redundant (very similar to others of the same command) and increase compute without improving discrimination. Pruning templates that are within a tight DTW distance of another same-command template preserves accuracy while reducing storage and matching cost.
**Description:** For each command, compute pairwise DTW between all templates. Greedily remove templates that are "covered" (min intra-command DTW < coverage_threshold). Sweep threshold. Measure rank-1 loss vs template count reduction.
**Expected outcome:** Remove 30-50% of templates at ≤1pp rank-1 loss. Compute cost reduces proportionally.
**Win condition:** ≥30% template count reduction at ≤1pp rank-1 loss.
**Constraints:** Never prune the last template for a command.
**How to run:** AdaptationDecision already has redundancy logic; extend to eval.
**Status:** [ ] planned

## E03-09: Enrollment augmentation (pitch/time perturbation)
**Hypothesis:** Synthetically perturbing enrolled templates (pitch shift ±50 cents, time stretch 0.9-1.1×) and adding them as additional "virtual" templates captures vocal variation without requiring more user recordings.
**Description:** For each enrolled template, generate 4 augmented variants: pitch +50c, pitch -50c, faster 0.9×, slower 1.1×. Enroll originals + augmentations. Compare rank-1 at matched original-count.
**Expected outcome:** Augmented enrollment (1 real + 4 synthetic per command) matches or beats 3-real-template enrollment at 1/3 the user recording burden.
**Win condition:** Rank-1 within 2pp of 3-template enrollment with 1-template + augmentations.
**Constraints:** Augmentation adds computation but no user burden; must sound natural.
**How to run:** AudioAugment pitch/time transforms, augmented enrollment in TorgoEval.
**Status:** [ ] planned

## E03-10: Cross-user template transfer (cohort normalization)
**Hypothesis:** Templates from other users saying the same word provide a "reference manifold" that helps normalize within-user templates, reducing speaker-specific idiosyncrasies. This is analogous to cohort scoring in speaker verification.
**Description:** For each command, compute a reference prototype from all other speakers' templates of that command (DTW barycenter of cross-user examples). Score = (distance to own template) / (distance to cohort prototype). Compare ratio vs absolute distance.
**Expected outcome:** Ratio scoring increases separability for commands where the user's realization is acoustically ambiguous but the cohort reference provides context.
**Win condition:** ≥3pp rank-1 gain on commands with low intra-user discriminability.
**Constraints:** Requires shared command vocabulary across users; may not be available in deployment.
**How to run:** TorgoEval with cross-speaker cohort, ratio scoring.
**Status:** [ ] planned
