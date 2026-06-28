# Audit Finding: dtw length normalization convention

- **Date:** 2026-06-28
- **Area:** core:matching
- **Severity:** low
- **Disposition:** fixed

## Summary

`Dtw.distance` normalizes the accumulated cost by `(n + m)` rather than by the true warping-path
length. This is a valid, standard convention (Rabiner) and is consistent across every match, so it
does not affect ranking — but it means the acceptance thresholds in `MatcherConfig` and
`ThresholdCalibrator` are *coupled to this normalization choice*. A future change to the normalizer
would silently shift the scale of every threshold. This is a documentation/traceability gap, not a
correctness bug.

## Evidence

- `core/matching/src/main/kotlin/com/speechangel/core/matching/Dtw.kt:70` — `accumulated / (n + m)`.
- `core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt:19` —
  `defaultAcceptanceThreshold` is expressed on this normalized scale.

## Recommendation

Document the `(n + m)` normalization at the divisor site and cross-reference it from the threshold
config, so the scale coupling is explicit and any future change to the normalizer is understood to
require threshold re-calibration.

## Disposition Decision

- **Decision:** fix — added an explanatory comment at the divisor and a note on
  `MatcherConfig.defaultAcceptanceThreshold` that thresholds live on the `(n+m)`-normalized scale.
  Documentation only; no behavioural change.
- **Follow-up:** none.
