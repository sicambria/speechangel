# Incident: wake gate requires utterance-length input, not per-frame input

- **Date:** 2026-06-28
- **Area:** MATCH
- **Trigger:** Initial two-stage loop plan fed 150ms frames to `WakeWordGate.evaluate()`; advisor challenged the assumption; `WakeWordGateTest` confirmed full-utterance inputs are required.
- **Status:** resolved (design corrected before any code was written)
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (MATCH-002)
- **Automation Links:** core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/WakeWordGateTest.kt

## Summary

The first draft of the `ListeningService` streaming loop plan called `wakeWordGate.evaluate(frame, wakeTemplates)` with a single 150ms frame per iteration. `WakeWordGate.evaluate()` runs `mfcc.extract(input)` then length-normalized DTW against the enrolled template. The enrolled template is a VAD-trimmed full utterance (~400ms of speech). Length-normalized DTW handles *tempo variation of the same content* — it does **not** make a 150ms fragment match a 400ms template. The gate would have returned `BELOW_THRESHOLD` on every frame, silently blocking all command recognition for any user who enrolled a wake word, while the no-wake-enrolled passthrough continued working. Tests would have stayed green (the existing tests use full utterances).

## Root Cause

Treating `WakeWordGate.evaluate(frame, …)` as a "feed-one-frame-at-a-time" API based on the parameter name `frame` without reading the test or the underlying DTW contract. Length-normalized DTW compares content at different tempos, not fragments of content.

## Rerun Analysis

- **Caught by:** advisor review of the plan draft + one-liner confirmation: `WakeWordGateTest.kt` passes `vad.trim(TestSignals.utterance(...))` ≈ 400ms to `evaluate()`.
- **Failed phase:** plan design (no code was written with the wrong approach).
- **Still unknown:** n/a — the fix is in production and all tests pass.
- **Failure class:** API-contract-misread (parameter name ≠ interface contract).
- **Smallest next probe:** read the gate's tests before designing the streaming driver.
- **Stop condition:** rolling-window design confirmed green by `make test`.

## Prevention

Changed the design to a rolling 750ms window (`wakeBuf`) that is VAD-trimmed before each `evaluate()` call — matching the test's proven usage pattern. The fix is in `ListeningService.listenLoop()`.

## Guardrail Updates

- docs/ai/ACTIVE_DEV_RULES.md — rule MATCH-002 added: "Read the test before streaming into a DTW-based gate."
- core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/WakeWordGateTest.kt — existing test is the API-contract source-of-truth (no new test needed; the error was in the caller's design, not the gate).

## Planning Integration

ACTIVE_DEV_RULES MATCH-002 captures the rule. The rolling-window pattern in `ListeningService` is the reference implementation for any future streaming driver of a DTW-based gate.

## Shift-Left Decision

- **Tests:** skip — the existing `WakeWordGateTest` already proves the correct contract; no additional test adds coverage.
- **Guardrail/automation:** update — promoted ACTIVE_DEV_RULES MATCH-002 (advisory). A static gate that verifies streaming callers pass a minimum-length buffer is possible but low-value given the advisory rule; deferred.

## Automation Follow-Up

No further static gate added. Advisory rule MATCH-002 covers future cases. If a second instance of this class occurs, promote to a lint check or test helper that asserts minimum input duration before DTW matching.
