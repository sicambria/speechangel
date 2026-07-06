# Plan: honest improvements on the TORGO baseline (held-out calibration, deployment slice, front-end bake-off)

- **Date:** 2026-07-06
- **Phase:** 0 (Matcher spike) — the "Measure FRR/FAR" + "Feature front-end bake-off" items, taken
  from the first *real* baseline to a first *real, honestly-improved* number.
- **Roadmap item:** `docs/ROADMAP.md` "⭐ Critical path" item 1 (follow-through). Retires part of the
  Phase-0 "Feature front-end bake-off" and "Per-command FAR-budget threshold tuning" items on **real**
  voices (INDEX rows `docs/plans/INDEX.md:22-24`, `:24`).
- **Predecessor:** `docs/plans/2026-06/first-real-frr-far-torgo.md` (done) produced the baseline this
  plan improves: rank-1 55.4% dysarthric / 74.6% control; single-template FRR 60–79% @ FAR≤5%
  (`docs/testing/2026-07-06_frr-far-torgo.md`).
- **Status:** done (D1–D3 implemented + run on real TORGO 2026-07-06; held-out numbers below)
- **Worktree:** `torgo-eval-improve` (off `main`; substantive non-docs code lands here per AGENTS.md)
- **Plan quality:** 98/100 — self-scored, advisor-gated (this planmax loop); advisor's three blockers
  (matched-FAR comparison, folds()-negatives disjointness, F04=21>20 slice cutoff) fixed pre-implement.

## Outcome (2026-07-06 — real TORGO, held-out)

- **D1 — per-command calibration is an honest NON-improvement.** Leave-one-fold-out matched-FAR:
  the held-out global-threshold FRR is **78.3%** at realized FAR 5.1% (≈ the in-sample 77.9% — held-out
  validates the baseline, no optimism). Per-command calibration, train-fit to FAR≤5%, does **not** hold
  out: its realized held-out FAR balloons to **24–34%** (accept-all fallback commands), so its lower FRR
  (40–58%) is a looser operating point, not a gain. This confirms the advisor's overfitting prediction
  and is the empirical basis for rule **EVAL-002**.
- **D3 — a directional front-end hypothesis (not an established gain).** Static MFCC (`none`) is the
  best held-out rank-1 cell (59.2% vs `delta_delta` 55.4%), but that is the max of 6 correlated cells and
  the margin is within sampling error (≈1.3 SE; per-speaker deltas all inside noise). What's robust is
  the *direction*: static is best/tied in all 3 speakers and noise reduction is worse in all 3 dry/NR
  pairs. So it's a hypothesis worth a **paired (McNemar) test**, not a 4-point win — NOT applied to the
  runtime matcher (out of `core:eval` scope); gated on that test + a control-grid + on-device.
- **D2 — deployment slice (F01+F04, ≤25 cmds): held-out FRR 70.7%** at FAR 6.3% (rank-1 59.8%), better
  than the 77-word-tail-blended 78.3% — the honest "realistic vocabulary" operating point.
- **Items 2 & 3 (on-device e2e, always-on soak): no change** — device-gated, already at the documented
  emulator ceiling. No improvement manufactured.

## Goal

Take the TORGO baseline from "measured floor" to "measured floor **plus an honest, held-out
improvement delta**", using only enhancements that (a) are autonomously executable on the corpus in
`~/torgo` and (b) can be reported **without in-sample fitting**. Three deliverables, each a real
number the honesty contract (`docs/plans/INDEX.md:78`) allows us to headline:

1. **D1 — Held-out per-command threshold calibration.** Replace the current global, in-sample
   threshold sweep with **leave-one-fold-out** threshold selection (calibrate on the folds *not* under
   test, score the held-out fold). Report the honest FRR/FAR delta vs the single global-threshold
   baseline. This is the "Per-command FAR-budget threshold tuning" item, measured correctly.
2. **D2 — The deployment-relevant vocabulary slice.** Report the operating point restricted to the
   realistic ~10–20-command speakers (F01=15, F04=21), separately from the 77-word F03 tail. This is
   *honest reporting of the slice the product actually ships*, not tuning — the advisor's "cleanest
   real gain."
3. **D3 — Front-end bake-off on real voices.** Run the built `FrontEndBakeoff` grid
   ({static, +Δ, +Δ+ΔΔ} × {noiseReduction off/on}) over TORGO, report the **full** comparison
   (losing cells included), pick a winner by a **stated prior**, and mark the selected cell as
   optimistically chosen — never headline its max as "the improved result."

Non-goal (explicit descope, advisor-agreed): **soft/k-NN voting.** It changes the deterministic
`AccessibilityService` hot path (`TemplateMatcher.match`, `core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt:33`)
and, at 1–2 templates/command/fold, TORGO cannot validate it — low ROI on the wrong corpus.

## Context & Constraints

### The load-bearing correctness finding (why this plan exists)
- **The report's headline improvement lever is a no-op.** `docs/testing/2026-07-06_frr-far-torgo.md`
  and the architecture line in `CLAUDE.md` (§4, "multi-template **vote**") both say the `Recognizer`
  *votes* across templates. It does not. `TemplateMatcher.match` computes per-command **min** DTW,
  argmin over commands, then a threshold (`core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt:42-60`) — identical to
  what the eval already does (`Evaluator.distanceTable` min-over-templates, `Evaluator.kt:76-84`;
  `DistanceRow.decide` argmin+threshold, `Evaluator.kt:22-26`). "Apply the Recognizer's voting" would
  not move a single number. This docs-vs-code discrepancy is **incident-worthy** (§ Close-out).
- **The real improvement surface** is therefore: (a) *how the threshold is chosen* (D1), (b) *which
  slice is reported* (D2), (c) *which front-end* (D3) — not the aggregation rule.

### The honesty trap this plan must not fall into (EVAL-001 inverted)
- **`ThresholdCalibrator` as written fits in-sample.** `calibrate(corpus)` sets each per-command
  threshold just below the `(allow+1)`-th smallest **negative distance in that same corpus**
  (`dists[allow] - EPS`, `ThresholdCalibrator.kt:59-60`), with a `maxObserved + 1f` "accept
  everything" fallback for commands no negative constrains (`:63`). Report FRR/FAR on those same
  negatives and FAR is at-budget *by construction* while FRR is fit in-sample — a **circular**
  improvement, held-out FAR would blow the budget through the fallback commands. Reporting that as a
  gain is EVAL-001 pointed the other way (a rosy number instead of a pessimistic one).
- **The current global sweep is also mildly in-sample.** `TorgoEval.analyze` pools *all* folds' rows,
  then sweeps the acceptance threshold over those same rows to pick EER / FRR@FAR≤5%
  (`TorgoEval.kt:104-128`). At 1 DOF the optimism is small, but it is nonzero — so even the *baseline*
  FRR@FAR≤5% (77.9%) is a touch optimistic. D1 fixes both.
- **Rank-1 is already held-out** and needs no change: each utterance is scored only against
  *other-fold* templates (`TorgoEval.run`, `TorgoCorpus.folds`, `TorgoEval.kt:66-72`). rank-1 stays
  the threshold-free hypothesis headline (EVAL-001).

### Held-out design (the D1 mechanism, no inner CV needed)
- Each outer fold's rows `R_f` are **already** produced held-out (scored vs templates excluding fold
  `f`). Because every positive utterance is a test query in exactly **one** fold **and every OOV
  negative is assigned to exactly one fold** (`TorgoCorpus.folds` round-robins negatives `i % k`,
  `TorgoCorpus.kt:114-115`; docstring "tested exactly once across all folds", `:100-101` — **verified
  this session**, not assumed: the held-out FAR premise depends on it), `R_f` and `⋃_{g≠f} R_g` share
  **no test positive and no test negative**. So: **calibrate the threshold(s) on `⋃_{g≠f} R_g`, apply to
  `R_f`, accumulate the accept/reject decisions across all `f`.** No test-label leaks into its own
  threshold, and the held-out FAR is measured on negatives disjoint from the calibration set. This
  reuses the rows the harness already computes — a *relocation of where the threshold is chosen*, not a
  re-architecture.
- **Matched-FAR comparison is mandatory (EVAL-001 recurrence guard).** The global sweep targets a
  *threshold* and `ThresholdCalibrator` targets a *FA budget*; on held-out folds they land at
  **different FAR**, so a lower per-command FRR at a higher FAR is spending more budget, **not** a win.
  Every method must be compared at the **same held-out FAR**: for each method, sweep its own knob
  (acceptance threshold for global; `budgetSecondsPerFalseAccept` for per-command), calibrate on the
  train folds at each knob value, score the held-out fold, and **accumulate (accepts, false-accepts)
  across all folds into one aggregate held-out `(FRR, FAR)` point per knob value** — tracing a held-out
  DET curve per method. Read every method's FRR at the marked **FAR ≤ 5%** line. Comparing FRRs at
  unequal FAR is the exact cross-distribution garbage EVAL-001 forbids.
- **Residual leak, disclosed:** an utterance in `R_f` may have been an *enrollment template* when
  scoring some `R_g`, so the calibration set's distances are not fully independent of `R_f`'s audio.
  This is second-order (enrollment overlap, not test-label overlap) and standard in k-fold threshold
  transfer; it will be stated as a caveat in the report, not hidden.

### Invariants (do not cross)
- **Corpus never committed.** TORGO is `[measure-only]`, multi-GB, gitignored, lives in `~/torgo`; the
  real run is gated on `-Dtorgo.dir` so `:core:eval:test` stays green with the corpus absent
  (predecessor plan, `first-real-frr-far-torgo.md` Context). No new committed fixtures from real audio.
- **Deterministic action layer untouched.** No change to `SpeechAngelAccessibilityService`,
  `DeviceAction`, `Recognizer`, or `TemplateMatcher` (D3 only *reads* front-end configs; D1/D2 are pure
  eval-side reporting). On-device/no-cloud invariants unaffected — this is pure JVM measurement.
- **Accuracy honesty (`research/04_build_and_reuse_plan.md:108`).** Every number states its
  enroll/test split and threshold-selection rule *in the report*, or it is meaningless. No bare
  percentages; no headlining an in-sample or hand-picked cell.

## Approach

Pure `core:eval` work, staged D1 → D2 → D3, each independently committed and each keeping
`:core:eval:test` green corpus-absent. All three land in the `TorgoEval` harness + its report renderer;
`ThresholdCalibrator` gains a held-out entry point that operates on precomputed `DistanceRow`s
(the in-sample `calibrate(Corpus)` path stays for the synthetic tests but is **not** used for the
headline). Re-run against `~/torgo` (dysarthric F01/F03/F04 + control FCX) and regenerate
`docs/testing/2026-07-06_frr-far-torgo.md` with the held-out numbers + a clearly-labelled improvement
delta table.

## Steps

### D1 — Held-out per-command threshold calibration
1. Tag each `DistanceRow` with its originating fold index (thread it through
   `TorgoEval.run`'s fold loop, `TorgoEval.kt:66-72`; add `fold: Int` to `DistanceRow` or carry a
   parallel `List<Int>` — prefer the field for clarity). Keep `Evaluator.distanceTable` signature
   stable by setting the fold in `TorgoEval` after the call.
2. Add `ThresholdCalibrator.calibrateFromRows(rows, commands): Map<CommandId,Float>` — the same
   budget-split + "highest threshold within per-command FA allowance" logic as `calibrate`
   (`ThresholdCalibrator.kt:41-66`) but taking **precomputed held-out rows** instead of re-enrolling a
   corpus in-sample. Unit-test it against a hand-built row set (deterministic).
3. In `TorgoEval.analyze`, add a **leave-one-fold-out, matched-FAR** pass. For each **method**
   ∈ {global-threshold, per-command-budget} and each value of that method's knob: for each fold `f`,
   calibrate on `⋃_{g≠f} R_g` at that knob, apply to `R_f`, and accumulate `(accepts, false-accepts,
   positives, negatives)` across all `f` → one aggregate held-out `(FRR, FAR)` point. This yields a
   held-out DET curve per method; **read each method's held-out FRR at the marked FAR ≤ 5% line** (the
   same FAR for both — never compare across unequal FAR). Keep the existing pooled rank-1 (unchanged,
   already held-out) and relabel the old pooled EER "in-sample reference (optimistic)".
4. Unit-test the accounting on a synthetic multi-fold row set: (a) assert no fold is calibrated on its
   own rows; (b) assert both methods are read at the **same** FAR before their FRRs are compared;
   (c) assert per-command differs from global only where a command has ≥1 train negative.

### D2 — Deployment-relevant vocabulary slice
5. The per-speaker rank-1-vs-vocab table already exists (`TorgoEval.kt:217-232`). Add a new
   **"realistic-vocab" sub-aggregate** over speakers with `commandCount ≤ 25` — the a-priori
   realistic-vocabulary regime, which admits **F01 (15) and F04 (21)** and excludes the F03 (77)
   reading-passage tail. (The cutoff is stated *before* looking at results and rounds to the ~10–25-cmd
   product range; it is not fit to the numbers.) Compute the held-out D1 matched-FAR operating point on
   that subset only. Label it "deployment-relevant slice (≤25 commands) — reported, not tuned."
6. No new tuning knob — D2 is a *reporting partition*. Assert in a test that the slice aggregate admits
   F01+F04 and excludes F03 under the ≤25 predicate (guards against a cutoff that silently collapses the
   slice to one speaker).

### D3 — Front-end bake-off on real voices
7. Drive the built `FrontEndBakeoff` (`core/eval/src/main/kotlin/com/speechangel/core/eval/FrontEndBakeoff.kt`) over TORGO for the grid
   {`NONE`, `DELTA`, `DELTA_DELTA`} × {noiseReduction off, on} (`MfccConfig`,
   `MfccExtractor.kt:30-45`). Compute **held-out rank-1** per cell (the threshold-free metric — no
   fitting). Render the **full** grid.
8. Pick the winner by a **stated prior**: "highest mean held-out rank-1 across speakers; ties → the
   simpler front-end (fewer deltas, noiseReduction off)." Mark the selected cell "optimistically
   selected on this corpus — not an independent test set." Do **not** replace the headline rank-1 with
   the winner's number; report it as "best-of-grid, selection-biased."

### Close-out
9. **Incident doc** `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md` for the
   docs-vs-code discrepancy (report + `CLAUDE.md` §4 say "vote"; code is 1-NN min). Required sections
   per CLAUDE.md §8.3; `## Guardrail Updates` cites `core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt:42`.
10. **New rule `EVAL-002`** in `docs/ai/ACTIVE_DEV_RULES.md`: "Select acceptance thresholds on data
    held out from the trial you score, and compare competing methods only at a **matched** FAR — never
    report an FRR whose threshold was fit on the same rows or read at a different FAR than its
    comparator." Extends EVAL-001 (`ACTIVE_DEV_RULES.md:67`). Add a runtime clause: the **shipped**
    `ThresholdCalibrator.calibrate(corpus)` (`ThresholdCalibrator.kt:30`) has this same in-sample
    property — it calibrates on the user's own enrollment set, so its FAR budget will be optimistic in
    the field; note this as a known limitation, not just an eval concern.
11. **Fix the stale claims:** correct `CLAUDE.md` §4 ("vote" → "min-distance / nearest-template across
    a command's templates") and the `docs/testing/2026-07-06_frr-far-torgo.md` "multi-template voting"
    line to "more enrolled templates per command (nearest-neighbour), threshold calibration, QbE."
12. **Regenerate the report** with the held-out D1 numbers + a before/after delta table
    (in-sample-baseline vs held-out global vs held-out per-command vs deployment-slice) and the D3
    grid. Update `docs/ROADMAP.md` critical-path results note and `docs/plans/INDEX.md`.
13. **Items 2 & 3 (on-device e2e, always-on soak):** mark **no-change** — device-gated, already at the
    documented emulator ceiling (`docs/testing/2026-07-06_on-device-e2e.md`,
    `..._always-on-soak.md`). No manufactured improvement. State this explicitly in the close-out so the
    "all roadmap items" scope is honestly accounted, not silently dropped.

## Definition of Done
- `:core:eval:test` green **corpus-absent** (all new tests are synthetic-row / gated).
- `make guardrails` (9/9) + `make static` green; committed in logical chunks (CLAUDE.md §8.6).
- The TORGO run reproduced against `~/torgo`; report shows: unchanged held-out rank-1, and held-out
  global vs per-command FRR **read at a matched FAR ≤ 5%**, the ≤25-command deployment slice, and the D3
  grid — each labelled with its selection rule.
- The improvement delta is reported **honestly**: if held-out per-command calibration does **not** beat
  the global threshold (a real possible outcome on sparse per-command negatives), that is reported as
  the finding, not buried. A null or negative delta is a successful, publishable D1 outcome.
- Incident doc + EVAL-002 + the two stale-claim fixes landed.

## Risks & Mitigations
- **Held-out per-command calibration underperforms the global threshold** (sparse per-command
  negatives → the `maxObserved+1` fallback dominates and FAR is uncontrolled on held-out folds).
  *Mitigation:* this is a legitimate result — report it; the global held-out number is the fallback
  headline. Do not tune to force a win. **Rollback:** the global held-out sweep alone (D1 step 3(i)) is
  a self-contained, shippable improvement over the pooled in-sample baseline even if per-command adds
  nothing.
- **Fold-tagging touches `DistanceRow`, used by synthetic tests** (`EvalTest.kt`,
  `ThresholdCalibrator.calibrate`). *Mitigation:* add `fold` with a default value so existing
  constructions compile unchanged; run `:core:eval:test` after step 1.
- **Blast radius:** `core:eval` only (pure JVM, `[measure-only]`). No app/service/matcher runtime code
  changes; no APK surface. Fully reversible by reverting the worktree.
- **D3 grid cost:** 6 cells × speakers × k-fold DTW is CPU-heavy but bounded (predecessor run completed
  on this host). *Mitigation:* gate D3 behind its own system property so it is opt-in, not part of the
  default test run.

## Test & Verification
- **New unit tests (corpus-absent, deterministic):** `calibrateFromRows` on a hand-built row set;
  leave-one-fold-out no-self-calibration assertion; ≤20-command slice-membership assertion.
- **Existing gate:** `:core:eval:test` (+ the three other `:core:*:test`) green; `make static` +
  `make guardrails` green.
- **Real-audio verification (the point):** re-run `TorgoEval` against `~/torgo` F + FCX, regenerate the
  report. Sanity check: held-out FRR should be ≥ in-sample FRR *in expectation* — **investigate if
  held-out is *substantially* lower** (a sign the split leaks); a small noise-level dip on this small
  sample is not itself a blocker.

## Standards & Guardrails Evidence
- **Evidence grounding:** every mechanism cites a resolved `path:line` above (`TemplateMatcher.kt:42`,
  `Evaluator.kt:76`, `ThresholdCalibrator.kt:59`, `TorgoEval.kt:104`, `MfccExtractor.kt:30`,
  `ACTIVE_DEV_RULES.md:67`).
- **Honesty contract** (`docs/plans/INDEX.md:73-78`): no fabricated numbers; in-sample vs held-out
  clearly separated; a null improvement is reported as such; device-gated items marked no-change.
- **Session-close protocol** (CLAUDE.md §8): incident doc + rule + INDEX + ROADMAP + guardrails +
  chunked commits all enumerated in Close-out.
