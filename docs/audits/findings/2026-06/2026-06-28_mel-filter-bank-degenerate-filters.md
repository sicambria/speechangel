# Audit Finding: mel filter bank degenerate filters

- **Date:** 2026-06-28
- **Area:** core:dsp
- **Severity:** low
- **Disposition:** fixed

## Summary

In `MelFilterBank`, triangle filters are anchored on integer FFT bins. When two adjacent anchors
collapse onto the same bin (`left == center` or `center == right`) — possible at low frequencies or
with many filters over a narrow band — that filter contributes no energy and floors to
`ln(1e-10)`, producing a constant "dead" coefficient. The default config (20 Hz–8 kHz, 26 filters,
512-pt FFT @ 16 kHz) produces strictly increasing anchors (bins 0, 2, 5, …, 231, 256) and is **not**
affected, but an aggressive future config could silently lose a filter band.

## Evidence

- `core/dsp/src/main/kotlin/com/speechangel/core/dsp/MelFilterBank.kt:44` — `logEnergies` guards
  against div-by-zero with `if (center > left)` / `if (right > center)`, so a collapsed triangle
  contributes nothing and the band floors to silence rather than capturing its center bin.
- `core/dsp/src/main/kotlin/com/speechangel/core/dsp/MelFilterBank.kt:25` — `buildBinPoints` can
  emit equal adjacent anchors.

## Recommendation

Make a collapsed filter fall back to its center bin's raw power instead of flooring to silence, so
no configuration silently drops a mel band. Zero numerical effect on the default (non-degenerate)
config; pure defensive robustness for unusual configs.

## Disposition Decision

- **Decision:** fix — `logEnergies` now falls back to the center bin's power when a filter's triangle
  collapses, guaranteeing every filter captures at least one bin. No change for the default config.
- **Resolution:** fixed in f12c861 (`MelFilterBank.kt`).
- **Follow-up:** none.
