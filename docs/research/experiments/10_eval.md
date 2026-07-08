# Domain 10: Evaluation Methodology & Benchmarking

**Goal:** Build a rigorous, reproducible, multi-corpus evaluation framework that measures what matters (FRR at matched FAR, per-severity, per-condition, held-out) and enables statistically valid comparison of experiments.

**Current baseline:** TORGO eval (speaker-dependent, held-out, rank-1 + FRR @ FAR, McNemar). Picovoice benchmark (wake-word protocol). ConditionEval (noise/distance/reverb grid). RejectionEval (rejection scoring). AmbientFar (continuous FA/hr). SyntheticCorpus (harness testing).

**Key insight from EVAL-001..005:** Evaluation methodology IS the product accuracy. Bad methodology (in-sample thresholds, confounded comparisons, unreplicated tails, unregistered hypotheses) produces phantom wins and missed real gains.

---

## E10-01: EER/DET curve as standard report format
**Hypothesis:** Reporting a single FRR/FAR point is misleading because operating points trade off. Reporting the full Detection Error Tradeoff (DET) curve — FRR vs FAR across all thresholds — enables honest comparison of different methods.
**Description:** For every experiment, generate a DET curve (FRR vs FAR on log-log axes) and report: (a) EER (equal error rate), (b) FRR at FAR=1%, 5%, 10%, (c) partial AUC at low-FAR region (FAR ≤ 5%). Standardize the DET curve as the primary report format.
**Expected outcome:** DET curves reveal that method A beats method B at some operating points but loses at others — the full curve prevents cherry-picking a single operating point.
**Win condition:** DET curve reporting standard adopted across all experiments.
**How to run:** Extend EvalReport to generate DET curve data + plot.
**Status:** [ ] planned

## E10-02: Cross-corpus generalization (TORGO → UASpeech → EasyCall)
**Hypothesis:** Methods that win on TORGO may not generalize to other dysarthric corpora (different etiologies, recording conditions, languages). Cross-corpus validation is the gate for claiming a technique "works on dysarthric speech" rather than "works on TORGO."
**Description:** Once UASpeech and EasyCall are acquired (CP-0), run the same pipeline on each corpus. Report the rank-1 and FRR correlation across corpora. Identify techniques that generalize vs those that are TORGO-specific.
**Expected outcome:** Rank-1 across corpora correlates at ρ=0.6-0.8. Some front-end techniques (e.g., longer frames for dysarthric) generalize; others (e.g., TORGO-specific formant tracking) may not. Cross-corpus variance quantifies the technique's generalizability.
**Win condition:** Quantified cross-corpus generalizability for each major technique.
**How to run:** Multi-corpus eval harness, per-technique cross-corpus variance.
**Status:** [ ] planned — blocked on UASpeech + EasyCall acquisition (CP-0)

## E10-03: Confidence interval reporting (bootstrap CI for FRR/FAR)
**Hypothesis:** The small sample sizes in dysarthric eval (3-4 speakers, ~20-30 commands each) mean FRR/FAR point estimates have wide confidence intervals. Reporting 95% bootstrap CIs will prevent over-interpretation of small differences.
**Description:** For each experiment, compute 95% percentile bootstrap CIs on FRR, FAR, and rank-1 (resample utterances with replacement within speaker, 1000 iterations). Report CIs alongside point estimates. Flag when CIs overlap between compared methods.
**Expected outcome:** Typical CI width: ±8-12pp on FRR for a 4-speaker evaluation. Any method claiming a "win" must have non-overlapping CIs (or significant McNemar). Most small differences will be within CI.
**Win condition:** Bootstrap CI standard adopted. Prevents false claims from underpowered experiments.
**How to run:** Bootstrap CI computation in EvalReport.
**Status:** [ ] planned

## E10-04: Stratified evaluation (per-condition, per-severity, per-vocabulary-size)
**Hypothesis:** Aggregate metrics hide important subgroup effects. A technique that improves FRR overall may help mild speakers but hurt severe ones (or vice versa). Stratified reporting reveals these interactions.
**Description:** Always report metrics disaggregated by: (a) severity (mild/moderate/severe), (b) noise condition (quiet/SNR 10dB/SNR 5dB), (c) vocabulary size (≤10 / 11-25 / 26+), (d) command duration (short ≤500ms / long >500ms). Flag techniques with subgroup-disproportionate effects.
**Expected outcome:** Some techniques show severity-by-effectiveness interactions (e.g., formant features help severe more than mild). Stratified reporting prevents deploying a technique that hurts the most vulnerable subgroup.
**Win condition:** Stratified breakdown standard in all experiment reports.
**How to run:** Stratification by metadata in EvalReport.
**Status:** [ ] planned

## E10-05: Statistical power analysis (minimum sample size for detectable effect)
**Hypothesis:** Many experiments are underpowered — with 3-4 dysarthric speakers, only large effects (≥10pp) are statistically detectable. A power analysis determines the minimum sample size needed to detect an effect of a given size, informing corpus acquisition (CP-0).
**Description:** For typical within-speaker variance in TORGO, compute: (a) minimum detectable effect size at 80% power for N=3/4/7/15 speakers, (b) required speaker count to detect 5pp/10pp/15pp effects. Use this to justify corpus acquisition targets.
**Expected outcome:** ≥7 speakers needed for 80% power to detect a 10pp effect. ≥15 needed for a 5pp effect. Current 3-speaker dysarthric set is underpowered for small effects — explains why many baselines are "directionally but not significantly" different.
**Win condition:** Quantified power analysis. Drives realistic experiment design and corpus acquisition urgency.
**How to run:** Power analysis on TORGO within-speaker variance distributions.
**Status:** [ ] planned

## E10-06: McNemar paired testing as standard significance test
**Hypothesis:** McNemar's test on per-utterance correct/incorrect outcomes is the right significance test for paired comparisons, because it accounts for utterance-level correlation (the same utterances are tested under both methods). It should be the standard for all method comparisons.
**Description:** Standardize McNemar's test: for each pair of methods (A vs B), create a 2×2 table of per-utterance outcomes (both correct / A only / B only / both wrong). Report χ² statistic and p-value. Require p<0.05 to claim "significant" and p<0.01 for "banked" improvements.
**Expected outcome:** McNemar catches confounded comparisons (e.g., method A wins because it solves different utterances, not because it's better). Prevents the best-of-N selection trap (EVAL-003).
**Win condition:** McNemar standard adopted; p<0.01 required for claiming a lever.
**How to run:** McNemar in RejectionScore (already implemented), extend to all comparisons.
**Status:** [ ] planned

## E10-07: Open-set evaluation (OOV rejection scoring)
**Hypothesis:** The current eval tests closed-set (every query is one of the enrolled commands). Real deployment has open-set queries (background speech, unrelated sounds, partial commands). OOV rejection — correctly rejecting non-command audio — should be a standard metric alongside FRR/FAR.
**Description:** Mix TORGO queries with OOV utterances (from speakers saying other words, or background speech from MUSAN). Measure: (a) rejection rate for OOV (true negative rate), (b) FAR due to OOV being accepted as a command. Report the open-set DET curve.
**Expected outcome:** MFCC-DTW rejects 60-80% of OOV at thresholds calibrated for 5% in-vocab FAR. OOV from same speaker (saying other words) is harder to reject than from different speakers.
**Win condition:** Open-set rejection at ≥70% for same-speaker OOV at ≤5% FAR.
**How to run:** OOV mixing (EasyCall or TORGO cross-command as OOV), open-set eval.
**Status:** [ ] planned

## E10-08: Realistic simulation fidelity (how close is sim to real device?)
**Hypothesis:** The condition-simulation harness (RIR convolution + MUSAN mixing) may not accurately replicate real-device audio characteristics (phone mic frequency response, AGC, noise suppression, codec compression). Comparing sim-eval vs real-device-eval on a few conditions quantifies the simulation fidelity.
**Description:** Record a few TORGO-like commands on a physical Android device in real conditions (quiet room, TV noise, kitchen noise at various distances). Run the same pipeline on real recordings and on sim-equivalents (simulate those same conditions). Compare FRR/FAR. Measure sim-vs-real gap.
**Expected outcome:** Sim over-optimizes by 5-15% rel FRR vs real (sim doesn't model phone AGC/codec artifacts). The gap is a correction factor — divide sim-claimed gains by 1.1-1.2 to estimate real gain.
**Win condition:** Quantified sim-vs-real fidelity gap.
**How to run:** Physical device recordings + matching sim conditions, paired comparison.
**Status:** [ ] planned

## E10-09: Longitudinal evaluation (session drift over time)
**Hypothesis:** Accuracy degrades over weeks-to-months as the user's voice changes (progressive condition, aging, seasonal). A "time-to-re-enrollment" metric — how many days until FRR degrades by 20% rel — is the key deployment metric for the re-enrollment feature.
**Description:** TORGO has multiple sessions per speaker spanning weeks. Measure FRR between session-1 enrollment and session-N queries, for N=2,3,4... Fit a degradation curve. Report "FRR-doubling time" and the recommended re-enrollment interval.
**Expected outcome:** FRR degrades ~2-5% rel per week of session separation for dysarthric speakers (more for progressive conditions). Recommended re-enrollment: every 2-4 weeks or when the user notices degradation.
**Win condition:** Quantified temporal degradation curve → evidence-based re-enrollment UX prompts.
**How to run:** Session-separated TORGO eval, temporal degradation modeling.
**Status:** [ ] planned

## E10-10: SOTA leaderboard (automated benchmark runner)
**Hypothesis:** An automated benchmark runner that executes a standardized pipeline against a fixed held-out test set, producing a leaderboard of technique-vs-accuracy, will accelerate the SOTA pursuit by making comparisons fast, reproducible, and honest (preventing cherry-picking and best-of-N selection).
**Description:** Build a "SpeechAngel Leaderboard" — a fixed held-out split of TORGO (+ future corpora), a standardized pipeline interface (front-end → matcher → threshold calibrator), and an automated runner that: (a) runs all registered techniques, (b) computes bootstrapped CIs, (c) runs McNemar vs baseline, (d) updates a results table. Run nightly or on-demand.
**Expected outcome:** Automated leaderboard eliminates "forgot a detail" errors, prevents cherry-picked operating points, and makes it trivial to test a new idea against the committed baseline.
**Win condition:** Leaderboard running; any new technique must clear the leaderboard to be claimed.
**How to run:** Leaderboard runner script + standardized pipeline interface + committed held-out split.
**Status:** [ ] planned
