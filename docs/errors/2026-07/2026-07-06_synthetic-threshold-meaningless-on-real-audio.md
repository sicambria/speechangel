# Incident: the synthetic acceptance threshold produced a garbage 100% FRR on real audio

- **Date:** 2026-07-06
- **Area:** EVAL
- **Trigger:** First real TORGO run through `core:eval` reported **FRR 100.0%, false accepts 0,
  enrollment failures 0** — everything rejected. A fixed-threshold FRR was about to be recorded as the
  first real accuracy number.
- **Status:** resolved (diagnosed to a threshold-scale artifact; metrics reworked to threshold-free)
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (EVAL-001)
- **Automation Links:** core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt (rank-1 +
  self-ranged EER + both-side VAD instrumentation)

## Summary

The first TORGO evaluation, run through `Evaluator.evaluate` at the harness's default acceptance
threshold (`MatcherConfig.defaultAcceptanceThreshold = 8.0`), reported **FRR = 100.0%** with **0 false
accepts** and **0 enrollment failures**. Read naively, "100% FRR on dysarthric speech" would have been
a catastrophic **false negative on the entire product hypothesis** — the number the whole critical path
gates on — and it is exactly the shape (a clean, confident, wrong headline) that survives review by
looking authoritative. The real cause was benign: `8.0` was tuned on the synthetic tone corpus, and
real MFCC-DTW distances live on a completely different scale (median distance-to-true-command ≈ 23), so
*nothing* cleared the threshold — neither positives nor negatives (hence FRR 100% **and** FA 0
together, the tell).

## Root Cause

Reporting a threshold-gated FRR using a threshold calibrated for a different data distribution. The
synthetic corpus's silence-padded tones yield small DTW distances; real speech yields large ones. A
fixed acceptance threshold is not portable across those distributions, so any absolute FRR/FAR read at
`8.0` on real audio is meaningless. The 0/0/100 signature (all rejected, including OOV negatives) is
diagnostic of a threshold far below the data, not of a matcher or endpointing failure.

## Rerun Analysis

- **Caught by:** the advisor's pre-write warning ("validate the pipeline before trusting the
  aggregate") + the impossible 0-false-accept-with-100%-FRR signature.
- **Failed phase:** metric design (the harness ran correctly; the *reported statistic* was wrong).
- **Failure class:** distribution-shift on a hard-coded constant (threshold portability).
- **Smallest next probe:** compute **rank-1** (argmin == truth, threshold-free) — it was 55.4%, i.e.
  10–40× chance, proving the matcher discriminates and the 100% was purely the threshold.
- **Stop condition:** headline metrics no longer depend on the synthetic default — rank-1 + a
  self-ranged EER/low-FAR sweep, plus enroll-side **and** query-side VAD counts (both 0) ruling out
  trimming artifacts.

## Prevention

`TorgoEval` reports **rank-1 closed-set accuracy** (threshold-free) as the headline hypothesis test,
and derives FRR/FAR only from a **self-ranged threshold sweep** (EER + a low-FAR operating point) — no
absolute number is ever read at a fixed cross-distribution threshold. The report states the synthetic
default is meaningless on real distances and shows both-side VAD instrumentation so a future reader
cannot mistake a trimming artifact for a matcher result.

## Guardrail Updates

`core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt` — `analyze()` computes rank-1 +
self-ranged EER/low-FAR + `emptyQueries` (query-side VAD) + `enrollmentFailures` (enroll-side), and the
rendered report (`docs/testing/2026-07-06_frr-far-torgo.md`) explicitly documents that the fixed
threshold is not used for the headline. New rule EVAL-001 in `docs/ai/ACTIVE_DEV_RULES.md`.

## Planning Integration

The carrying plan (`docs/plans/2026-06/first-real-frr-far-torgo.md`) already mandated a one-speaker VAD
sanity pass before trusting any aggregate (advisor gate #4). That step surfaced the artifact; this
incident extends it: a real-audio accuracy number must be **threshold-free or swept**, never read at a
synthetic-tuned constant.

## Shift-Left Decision

- **Tests:** add — `EvalTest` now asserts the `SYNTHETIC` banner is present on synthetic runs and
  absent on `synthetic=false` runs; `TorgoEvalTest` runs the real corpus when present.
- **Metric design:** update — the headline is left-shifted into the harness itself: rank-1/EER are
  computed directly from the distance table, so a cross-distribution absolute FRR can no longer be
  emitted as the headline. The failure is now structurally hard to reproduce.
- **Guardrail/automation:** skip — a bespoke static gate is not worth it; rule EVAL-001 plus the
  reference implementation in `TorgoEval` cover the class. (Optional divergence-warning noted below.)

## Automation Follow-Up

Optional future: a `TorgoEval` assertion that warns when the fixed-threshold FRR and the rank-1
substitution rate diverge by more than a wide margin (the exact divergence that flagged this artifact),
so a regression to fixed-threshold reporting self-announces.
