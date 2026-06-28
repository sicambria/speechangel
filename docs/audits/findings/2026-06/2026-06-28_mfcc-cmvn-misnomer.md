# Audit Finding: mfcc cmvn misnomer

- **Date:** 2026-06-28
- **Area:** core:dsp
- **Severity:** low
- **Disposition:** fixed

## Summary

The `MfccExtractor` config flag `applyCmvn` and the helper `cmvn(...)` are named for *Cepstral Mean
and Variance Normalization*, but the implementation only subtracts the per-coefficient mean — it
performs Cepstral Mean Normalization (CMN), with no variance normalization. The behaviour is correct
and intentional (true variance normalization would rescale DTW distances and invalidate the
calibrated acceptance threshold), but the name over-promises. This is a naming/honesty defect, not a
numerical bug.

## Evidence

- `core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt:30` — `val applyCmvn: Boolean`.
- `core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt:123` — `fun cmvn(...)` computes
  and subtracts `mean[]` only; no variance term.

## Recommendation

Rename to reflect the actual operation (CMN) rather than implementing variance normalization, since
changing the feature scale would break the per-deployment threshold calibration. Update the symbol,
the config flag, and the doc comment to state explicitly that variance is *intentionally* not
normalized and why.

## Disposition Decision

- **Decision:** fix — renamed `applyCmvn` → `applyCmn` and `cmvn` → `cmn`; comment now states
  variance is deliberately left un-normalized to keep DTW distances on a stable, calibratable scale.
  Flag is internal to `MfccExtractor` (no app/data callers), so the rename is contained.
- **Resolution:** fixed in f12c861 (`MfccExtractor.kt`).
- **Follow-up:** none.
