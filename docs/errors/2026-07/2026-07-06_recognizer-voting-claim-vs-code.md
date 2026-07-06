# Incident: "multi-template vote" claim contradicts the 1-NN matcher code

- **Date:** 2026-07-06
- **Area:** EVAL / MATCH (docs-vs-code)
- **Trigger:** while planning "improve the TORGO baseline", diffing `TemplateMatcher.match` against
  `Evaluator.distanceTable` showed the report's headline improvement lever ("multi-template voting")
  was a **no-op** — the matcher is 1-NN min-distance, which the eval already models exactly.
- **Severity:** low (documentation/roadmap correctness — no shipped behaviour was wrong; the *plan* to
  improve on it was aimed at a non-existent lever)
- **Status:** resolved (stale claims corrected; plan reshaped around the real levers)
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (EVAL-002)
- **Automation Links:** core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt
  (`renderCaveats` now states the true 1-NN rule on every regenerated report)

## Summary

The architecture line in `CLAUDE.md` §4 and the first TORGO report
(`docs/testing/2026-07-06_frr-far-torgo.md`) both described the recognizer as doing a **multi-template
vote** and named "multi-template voting" as the headline enhancement that would close the FRR gap. The
code does **not** vote. `TemplateMatcher.match` (`core/matching/src/main/kotlin/com/speechangel/core/
matching/TemplateMatcher.kt:42`) keeps, per command, the **minimum** DTW distance across that command's
templates (1-nearest-neighbour), takes the argmin command, and thresholds it. `Evaluator.distanceTable`
(`core/eval/src/main/kotlin/com/speechangel/core/eval/Evaluator.kt:76`) already computes the identical min-over-templates quantity. So
"apply the Recognizer's voting to the eval" would change **zero** numbers — the eval already models the
exact matcher. The improvement plan's headline lever was a no-op.

## Root Cause

The word "vote" entered the architecture description early (it is a natural way to describe
multi-template matching) and was never reconciled against the implementation, which took the simpler
and arguably better 1-NN-min route (`TemplateMatcher` KDoc even says "keeps the *best* (minimum) DTW
distance"). The roadmap and report then inherited the "voting" framing as if it were an unbuilt feature
with headroom, when in fact the aggregation rule was already shipped and already measured.

## Rerun Analysis

Caught while planning "improve the TORGO baseline" (planmax): diffing `TemplateMatcher.match` against
`Evaluator.distanceTable` before writing code showed both compute per-command-min → argmin → threshold.
The advisor independently confirmed the no-op. Had the diff not been done, effort would have gone into
"wiring the Recognizer's vote into the eval" and produced an identical report presented as an
improvement — a fabricated gain. The real improvement surface turned out to be *where the threshold is
chosen* (held-out vs in-sample) and *which front-end* (static MFCC beats delta-delta on TORGO).

## Prevention

- Correct the two stale claims (this session): `CLAUDE.md` §4 signal-flow line and the report's
  "multi-template voting" sentence → "1-NN min-distance across a command's templates; the improvement
  levers are more enrolled templates, threshold calibration, QbE."
- When a doc names a mechanism as a *lever*, cite the `path:line` that implements (or would implement)
  it, so a claimed-but-absent feature is visible at review time.

## Guardrail Updates

`core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt:42` is the source of
truth for the aggregation rule (per-command min, not vote). The new caveat block in
`core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt` (`renderCaveats`, "The matcher is
1-NN (min DTW), not a vote") makes every regenerated report state the true rule, so the discrepancy
cannot silently reappear in a future report.

## Planning Integration

The `docs/plans/2026-07/torgo-eval-honest-improvements.md` plan was reshaped around this finding: the
"multi-template voting" deliverable was dropped (no-op + corpus can't validate soft-voting at 1–2
templates/command/fold) and replaced with held-out calibration, the deployment slice, and the front-end
bake-off — the levers that actually move numbers on the corpus we have.

## Shift-Left Decision

- **Rule:** add — **EVAL-002** now codifies "select thresholds held-out; compare at matched FAR", the
  broader honesty lesson this incident surfaced alongside the voting no-op.
- **Docs:** update — the two stale "vote" claims (`CLAUDE.md` §4, the TORGO report) corrected to 1-NN
  min-distance, with the true rule now emitted by `TorgoEval.renderCaveats` on every report.
- **Guardrail/automation:** skip — a lint flagging "vote/voting" in matcher docs is higher-noise than
  value at a single occurrence; the shift-left is the planmax "diff the two loops before building on a
  claimed lever" habit, now recorded. Revisit only if a second aggregation-framing drift appears.

## Automation Follow-Up

None scheduled. A lint that flags "vote/voting" in matcher docs would be higher-noise than value given
the single occurrence. Revisit only if a second aggregation-framing drift appears.
