# Incident: pre-registered common-mode rejection hypothesis (H1) refuted on real TORGO

- **Date:** 2026-07-06
- **Area:** EVAL / MATCH (accuracy hypothesis, not a code defect)
- **Trigger:** the pre-registered flagship accuracy lever of
  `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md` — common-mode (cohort)
  normalization of the accept/reject score — was McNemar-tested held-out and lost.
- **Severity:** low (no shipped behaviour was wrong; the *bet* lost, and the process caught it before any
  runtime adoption — the intended outcome of pre-registration).
- **Status:** resolved (hypothesis recorded as refuted; no runtime change; `margin` deferred as a future
  pre-registered test).
- **Guardrail Links:** `docs/ai/ACTIVE_DEV_RULES.md` (EVAL-003).
- **Automation Links:** `core/eval/src/main/kotlin/com/speechangel/core/eval/RejectionEval.kt`
  (McNemar + exploratory-family renderer that emits the "NOT banked" framing on every report).

## Summary

The always-on product number is the open-set rejection FRR (75.7% @ FAR≤5% held-out on the shipped
static front-end). First principles said the ~34-point gap between rank-1 error and FRR@FAR is threshold
cost — correct-argmin positives thrown away because raw min-DTW distance `d1` of a true match overlaps
the `d1` of OOV. The pre-registered fix, **H1 = common-mode normalization** `s = d1 − median{d_c : c ≠
winner}`, was meant to subtract the per-trial "far-from-everything" offset. Measured held-out
(leave-one-fold-out, matched FAR) it **did not help**: dysarthric FRR 75.7%→79.4% (χ²=1.93, p=0.165);
control FRR 61.9%→73.5% (**χ²=39.7, p<0.001 — a significant regression**). H1 is refuted; no runtime
change was made.

## Root Cause

**This is a hypothesis-about-reality failure, not a code bug.** The implementation is correct: the unit
test `RejectionScoreTest."common-mode separates far-from-everything positives that raw distance cannot"`
shows common-mode wins exactly when its idealizing assumption holds (positives far-but-distinctive; OOV
close-but-ambiguous). Real TORGO violates that assumption. **Candidate mechanism (NOT established):**
`median(other-command distances)` is small precisely when the true command has acoustically-close
neighbours, so subtracting it *penalizes correct-but-confusable matches* rather than removing a
common-mode offset — the per-speaker pattern is mixed (FC01 barely moved, F01/FC02 moved a lot), so this
is a hypothesis about the failure, not a proven cause.

## Rerun Analysis

Caught by design: the plan pre-registered ONE hypothesis and adjudicated it with a paired McNemar vs the
baseline, reporting every other scorer as an explicitly-not-banked exploratory family. The exploratory
table shows `margin(λ=1)` directionally better than raw on both sets (71.2%/60.0% vs 75.7%/61.9%) — but
it was not pre-registered, and on control its apparent gain rides a higher FAR (5.4% vs 4.9%), so it is a
FAR-confounded in-sample winner. Had the family been run without pre-registration, `margin` would have
been reported as "the improvement" — a manufactured, selection-biased, partly-FAR-artifact gain. The
discipline did its job.

## Prevention

- **Pre-registration + not-banked family is the prevention**, now proven on a live case. It is codified
  as EVAL-003 so the next accuracy hypothesis is adjudicated the same way rather than mined from a table.
- `margin` is recorded as a **future pre-registered, FAR-matched test on fresh data**, never adopted from
  this run (the exact treatment D3 gave the static-MFCC direction).

## Guardrail Updates

`core/eval/src/main/kotlin/com/speechangel/core/eval/RejectionEval.kt` is the source of truth: its
`render(...)` emits the "**exploratory, not banked**" label and the McNemar verdict on every regenerated
report, and its `mcNemar(...)` is the paired adjudication a future hypothesis must pass. The refuted H1
lives on only as `RejectionScore.CommonMode` behind the (default-`raw`) scorer seam — never wired into
`TemplateMatcher`.

## Planning Integration

`docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md` §9 (conditional runtime adoption)
does **not** fire — H1 did not clear significance, so the matcher decision rule is unchanged, exactly as
the plan's "adopt iff it wins the McNemar" gate specified. The plan's honest-negative branch is the
realized path.

## Shift-Left Decision

- **Rule:** add — **EVAL-003** ("pre-register one accuracy hypothesis; adjudicate it with a paired test
  vs baseline at matched FAR; report any other variants as an explicitly-not-banked exploratory family;
  never adopt a lever mined from that family without its own pre-registered, FAR-matched confirmation").
- **Docs:** the consolidated finding is `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`.
- **Guardrail/automation:** skip a new script — the not-banked framing is emitted in-report by
  `RejectionEval.render`, and pre-registration is a planning habit (planmax), higher-value as a rule than
  as a lint. Revisit only if a second "mined from the family" gain is proposed.

## Automation Follow-Up

None scheduled. A future `margin` confirmation needs *fresh* labeled audio (a second corpus) — a
Bucket-B input, not an automatable step on the corpus we have.
</content>
