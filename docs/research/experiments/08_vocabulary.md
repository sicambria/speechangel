# Domain 08: Vocabulary & Command Design Optimization

**Goal:** Help users select command vocabularies that maximize acoustic discriminability, minimizing confusion and FRR at the vocabulary-design stage (before enrollment).

**Current baseline:** VocabularyDistinctness advisor (scale-relative DTW + shared-onset detection, NUDGE/WARN severity). Advisory only — never blocks enrollment.

**Key insight:** Vocabulary design is the cheapest accuracy lever — picking acoustically distinct commands can reduce confusion by more than any matcher improvement. The existing tool detects problems; experiments here add quantitative prediction and active recommendation.

---

## E08-01: Command discriminability vs vocabulary size curve
**Hypothesis:** Rank-1 degrades predictably with vocabulary size, following a power-law curve. Knowing the user's vocabulary size predicts the achievable accuracy ceiling before enrollment.
**Description:** On TORGO, measure rank-1 as a function of vocabulary size (5/10/15/20/30/50/100 commands). Fit a power-law curve. Report the knee point where adding commands costs disproportionately more accuracy.
**Expected outcome:** Rank-1 follows `r = r_1 * N^(-α)` with α ≈ 0.15-0.25. Each doubling of vocab costs 3-5pp rank-1. ≤25 commands (the deployment slice target) is the practical range.
**Win condition:** Quantified vocabulary-size-vs-accuracy curve. The deployment recommendation: ≤25 commands for ≥70% rank-1.
**How to run:** TorgoEval with variable vocabulary subset sizes.
**Status:** [ ] planned

## E08-02: Acoustic distance prediction model (pre-enrollment FRR estimate)
**Hypothesis:** It's possible to predict per-command-pair confusion probability from acoustic features computed during enrollment (DTW distance distributions, duration ratios, spectral overlap), creating a pre-enrollment FRR estimator that warns users about risky vocabulary choices before they're locked in.
**Description:** For each command pair, compute features from their enrolled templates: (a) cross-command DTW distance, (b) duration ratio, (c) spectral centroid distance, (d) shared-onset flag, (e) syllable count ratio. Train a simple classifier to predict "this pair will have >5% confusion rate". Evaluate on held-out speakers.
**Expected outcome:** Predictor achieves >80% precision/recall for identifying high-confusion command pairs. The top 3 features: cross-command DTW, shared-onset, and duration ratio.
**Win condition:** Predictor identifies ≥80% of pairs that will show confusion at test time.
**How to run:** Feature extraction from enrolled templates, classifier training, cross-speaker validation.
**Status:** [ ] planned

## E08-03: Optimal command set selection (greedy discriminability maximization)
**Hypothesis:** Given a set of candidate commands the user wants, an algorithm can greedily select the subset that maximizes minimum pairwise acoustic distance, ensuring the best possible discriminability for the chosen vocabulary size.
**Description:** Build an acoustic distance matrix from a small enrollment of each candidate command. Greedy selection: start with the most "central" command, iteratively add the command that maximizes the minimum distance to already-selected commands. Compare rank-1 of greedily-selected vs random vocabulary subset.
**Expected outcome:** Greedy selection improves rank-1 by 5-10pp vs random vocabulary of the same size, by avoiding acoustically similar command clusters.
**Win condition:** ≥5pp rank-1 gain for greedily-selected vs random vocabulary.
**Constraints:** Must not reduce vocabulary below the user's minimum required commands (e.g., "all commands must be selected"). Use this to suggest alternatives for confusing pairs.
**How to run:** Greedy selection algorithm, TorgoEval with variable subsets.
**Status:** [ ] planned

## E08-04: Command duration optimization (optimal command length)
**Hypothesis:** Commands that are too short (<300ms) lack sufficient acoustic detail for DTW discrimination. Commands that are too long (>2s) have more temporal variability (more chance for DTW misalignment). An optimal duration range 500-1500ms maximizes discriminability.
**Description:** Bin TORGO commands by duration: <300ms, 300-500ms, 500-1000ms, 1000-1500ms, 1500-2000ms, >2000ms. Measure per-bin rank-1 and FRR. Fit a curve.
**Expected outcome:** Rank-1 peaks at 500-1500ms. <300ms commands have 5-10pp lower rank-1. >2000ms have 3-5pp lower (DTW misalignment from variable timing).
**Win condition:** Quantified duration-accuracy curve. UX recommendation: nudge users toward 2-4 syllable commands.
**How to run:** Duration-binned TorgoEval.
**Status:** [ ] planned

## E08-05: Syllable count vs discriminability
**Hypothesis:** Single-syllable commands (e.g., "go", "stop") are harder to discriminate than 2-3 syllable commands (e.g., "go home", "stop music") because they have fewer acoustic landmarks. Each additional syllable adds discriminative information.
**Description:** Classify TORGO commands by syllable count (1/2/3/4+). Measure rank-1 per syllable-count bin. Control for vocabulary size.
**Expected outcome:** 1-syllable: baseline. 2-syllable: +5-8pp. 3-syllable: +10-15pp. 4+: saturates. The biggest jump is 1→2 syllables.
**Win condition:** Quantified syllable-count-vs-accuracy curve. UX recommendation: "use at least 2 syllables."
**How to run:** Syllable-count annotation of TORGO commands, per-bin eval.
**Status:** [ ] planned

## E08-06: Vowel diversity as a discriminability metric
**Hypothesis:** Commands with diverse vowels (e.g., /a/, /i/, /u/ in one command) are easier to discriminate than commands with similar or repeated vowels across the vocabulary. Vowel space coverage predicts vocabulary discriminability.
**Description:** For each vocabulary subset, compute vowel space metrics: (a) formant centroid spread (F1×F2 area), (b) per-command vowel uniqueness score, (c) cross-command vowel overlap. Regress vowel metrics against vocabulary-level rank-1.
**Expected outcome:** Vowel diversity explains 30-50% of variance in vocabulary-level rank-1, independent of vocabulary size. Commands with distinct vowel profiles are 3-5× less confusable.
**Win condition:** R² ≥ 0.3 for vowel-diversity→rank-1 regression.
**How to run:** F1/F2 extraction from templates (or MFCC proxy), vowel diversity metrics, vocabulary-level eval.
**Status:** [ ] planned

## E08-07: Consonant-place diversity metric
**Hypothesis:** Consonant place of articulation (labial, alveolar, velar, etc.) is the primary consonant discriminability axis. A vocabulary with diverse consonant places minimizes confusion from shared-onset minimal pairs (e.g., "call"/"carl" — both velar-alveolar).
**Description:** Estimate consonant place from spectral moments in consonant-vowel transitions. Compute place diversity across the vocabulary. Compare confusion rate vs place diversity.
**Expected outcome:** Vocabularies with ≥5 distinct consonant places have 30-50% lower confusion rates than those with ≤3 places.
**Win condition:** Quantified place-diversity-vs-confusion curve.
**How to run:** Spectral moment-based place estimation, diversity scoring, TorgoEval.
**Status:** [ ] planned

## E08-08: Wake-word bleed prevention (command set must exclude wake phonetics)
**Hypothesis:** Commands that share phonetic material with the wake word (e.g., wake="hey angel", command="play angel" → both contain /eɪn.dʒəl/) will cause false Stage-2 triggers (wake word mistakenly classified as a command) and suppress Stage-2 for the real command.
**Description:** Compute DTW distance between the wake template and each command template. Commands with distance below a threshold to the wake word are "bleed candidates." Measure false-wake-rate (wake classified as command) and false-command-rate (command suppressed by wake gate) for bleed pairs.
**Expected outcome:** Commands with DTW distance < 3× intra-command spread to wake word show 10-20× higher mutual confusion. A vocabulary should be designed with the wake word as a "repulsion center."
**Win condition:** Quantified bleed rate; design rule: DTW(wake, any command) ≥ 3× max(intra-wake-spread, intra-command-spread).
**How to run:** Cross-gate confusion measurement in WakeGatedRecognizer.
**Status:** [ ] planned

## E08-09: Minimal-pair detection precision (VocabularyDistinctness vs ground truth)
**Hypothesis:** The current VocabularyDistinctness advisor's shared-onset detection correctly identifies minimal pairs (e.g., "call"/"carl") but may over-flag pairs that are acoustically distinct despite sharing onset (e.g., "play"/"please" — different trajectories after onset).
**Description:** Annotate TORGO command pairs as "truly confusable" (confusion rate >X% in eval) vs "acoustically distinct but share onset." Measure VocabularyDistinctness precision/recall at the NUDGE and WARN thresholds.
**Expected outcome:** Current WARN flag has high recall (catches >90% of truly confusable pairs) but low precision (~40% — many false flags). Tuning the scale-relative threshold can improve precision without sacrificing recall.
**Win condition:** Precision ≥60% at recall ≥90%, or identify the reason precision is low and whether it matters (false NUDGEs are harmless).
**How to run:** VocabularyDistinctness on TORGO pairs, cross-referenced with eval confusion matrix.
**Status:** [ ] planned

## E08-10: Vocabulary recommendation engine (data-driven suggestions)
**Hypothesis:** Given a user's desired actions, a recommendation engine can suggest the most acoustically discriminable command phrases for each action, drawing from a database of "high-discriminability" command templates (pretrained on multilingual data).
**Description:** For a set of 20 common actions (home, back, scroll, call, message, etc.), precompute the 10 most acoustically distinct command phrases across 5+ languages. When the user selects an action, suggest phrases ranked by (a) discriminability from other selected phrases, (b) language-independence (works well across acoustic realizations), (c) brevity. Implement as an optional "suggest" button in the Teach screen.
**Expected outcome:** Suggested vocabulary yields 5-10pp higher rank-1 than user-chosen vocabulary for the same set of actions, especially when users are unaware of acoustic discriminability.
**Win condition:** ≥5pp rank-1 gain for suggested vs naive vocabularies.
**How to run:** Precomputed suggestion database + TORGO-style benchmark.
**Status:** [ ] planned
