# Audit Finding: streaming energy gate stuck floor

- **Date:** 2026-06-28
- **Area:** core:dsp
- **Severity:** low
- **Disposition:** fixed

## Summary

`StreamingEnergyGate` adapts its running noise-floor estimate *only on frames it classifies as
non-speech* (`if (!speech) noiseFloor = …`). If ambient noise rises within a session to a level
above the current gate threshold, every subsequent frame is classified as "speech", so the floor
never tracks the new noise level — the gate latches open and admits everything for the rest of the
session. The failure direction is benign (over-admission, which Stage-2 DTW rejects), but the gate
cannot re-baseline to a louder environment once it has ratcheted open.

## Evidence

- `core/dsp/src/main/kotlin/com/speechangel/core/dsp/StreamingEnergyGate.kt:26` — `if (!speech)`
  guards the only floor update, so a sustained above-threshold input freezes `noiseFloor`.
- `core/dsp/src/test/kotlin/com/speechangel/core/dsp/StreamingEnergyGateTest.kt` — covers the
  quiet-adapt and all-speech-passes paths, but not a rising-ambient re-baseline.

## Recommendation

Add a heavily-damped upward "leak": adapt the floor toward the input on speech frames too, at a rate
small enough that a ~1–2 s command cannot materially move it, but large enough that tens of seconds
of sustained loud ambient noise re-baselines the floor. Preserves the original intent (a brief
command never drags the floor up to itself) while removing the permanent latch.

## Disposition Decision

- **Decision:** fix — added an asymmetric `speechLeak` term (rate ≪ `adaptation`) so the floor
  creeps toward sustained loud input without a short utterance moving it; doc comment updated to
  describe the refined invariant.
- **Follow-up:** none. Component is currently referenced only by its own unit test; wired into the
  always-on Stage-1 path per `CLAUDE.md` §4 architecture.
