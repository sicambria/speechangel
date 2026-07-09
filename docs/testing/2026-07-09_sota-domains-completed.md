<!-- Completion of the automated SOTA scorecard: the five previously-NOT_MEASURED domains (D7/D10/D11/
     D12/D13) now have fully-scripted measurement mechanisms. Measure-only tooling; no runtime change. -->
# Completing the automated SOTA scorecard — D7, D10, D11, D12, D13

**Date:** 2026-07-09 · **Status:** done · **Scope:** measure-only tooling (`core:eval` + `scripts/eval`);
no product-runtime / matcher / DSP / threshold code changed. Plan:
`docs/plans/2026-07/complete-sota-measurement.md`.

> **Honesty banner.** Every acoustic condition here is a **SIMULATED** channel or a **SYNTHETIC** proxy,
> never a field recording. Device metrics (latency/battery) are **host-measured then device-scaled** or
> **first-principles-derived** — displayed and banded but **excluded from the wall-dominated composite** so
> a modelled number can never set the reported wall. Language independence is **argued by construction**,
> not measured (single-read data yields no valid proxy). This is the same measurement discipline the repo
> enforces via `scripts/audits/verify-sota-measurement.mjs`.

## What changed

Before this, `make sota-score-full` left five domains `NOT_MEASURED` and one (D7) carried a **broken
mechanism reference** (`SotaScorecard.kt` named `in_regime.py mfcc --emit`, but `in_regime.py` had no
`--emit`). All five now have a real, fully-automated, scripted mechanism — no waiting for people or
devices. Result: **13/15 domains banded**, D10 first-principles-argued, D15 structural.

| Domain | Mechanism (new) | Route | Status / composite |
|---|---|---|---|
| **D7** Wake detection @ ≤0.5 FA/hr | `in_regime.py --emit` (mfcc arm, torch-free): detection at the ≤0.5 FA/hr operating point on LibriSpeech background, per-window VAD | Python `--emit` bridge | PROXY — **counts** |
| **D10** Language independence | `lang_indep_rank1.py` **diagnostic**: proves single-read Common Voice yields only chance-level cross-clip rank-1 → no valid proxy | diagnostic (no band-feeding emit) | **NOT_MEASURED** — argued by-construction |
| **D11** Latency P50 | `LatencyEval.kt`: times the shipped `EnergyVad`→`MfccExtractor`→`TemplateMatcher` decide path on the host JVM, scales to Pixel 6 | JVM (`core:eval`) | SIMULATED_DEVICE — **excluded** |
| **D12** Battery %/hr | `BatteryModel.kt`: first-principles power model consuming D11's decide cost + cited Pixel 6 constants | JVM (`core:eval`) | SIMULATED_DEVICE — **excluded** |
| **D13** Enrollment efficiency | `EnrollmentEfficiencyEval.kt`: Monte-Carlo template-count sweep (k=1..5) on real TORGO, `efficiency = rank1(1)/rank1(saturation)` | JVM (`core:eval`) | MEASURED — **counts** |

## Measured values (this host)

Generated scorecard: `core/eval/build/sota-scorecard.md` (a build output). Representative values:

- **D7:** in-regime MFCC-DTW detection at the ≤0.5 FA/hr operating point (F01, LibriSpeech bg,
  per-window VAD). On a short-background smoke run the harness reports ~93.8% detection; the committed
  run uses `SOTA_BG_MIN=60` (≈1 h background) for an honest, less optimistic FA/hr calibration. This is
  an **in-regime proxy, optimistically biased** (speaker's own words; real continuous household audio
  fires more) — EVAL-003 exploratory, **NOT banked** as an FRR/FAR win.
- **D11:** host P50 ≈ 1.3 ms (AMD Ryzen 7 8845HS) × `DEVICE_SCALE=2.6` → **≈3 ms** device P50 → band
  1000. `DEVICE_SCALE` = host GB6-ST (≈2650) / Pixel 6 Cortex-X1 GB6-ST (≈1050) ≈ 2.52, rounded up to
  bias the device slower. Excluded from the composite (host-scaled, not a device measurement).
- **D12:** first-principles model → **≈2.0 %/hr (±40%)** → band 1000. Constants (all cited `const val`s
  in `BatteryModel.kt`): battery 17.76 Wh (Pixel 6 4614 mAh × 3.85 V), P_baseline 0.35 W (always-on CPU
  capture+VAD), P_active 2.0 W (one Tensor big-core), speech-duty 0.15, avg-utterance 1200 ms. A
  derivation, not a measurement — excluded.
- **D13:** 1-shot rank-1 **53.7%** / saturation **59.2%** (saturates at **2** templates) → efficiency
  **90.7%** → band **950**. Real TORGO, shipped `none` front-end. Counts for the composite.
- **D10:** cross-clip identification rank-1 = **chance in every language** (English anchor **1.8% ≈
  1/40**); mean Δ ≈ 0 pp is a difference of two noise values — the **null**, not a signal. No valid
  rank-1 proxy exists on single-read Common Voice (DTW distance is informative only for same-content
  pairs, which CV lacks). Language independence is therefore argued **by construction** — the shipped
  path is 13 MFCC + DTW with no LM/lexicon/phoneme layer (`MfccExtractor.kt`), corroborated by Zhang
  (2014) language-independent DTW (PLOS ONE) and the same family's **89.2% cross-speaker English rank-1
  on the Picovoice benchmark, untuned** — see `docs/product/2026-07-08_sota-domain-bands.md` §10.

## Composite invariant (EVAL-002 discipline)

The wall-dominated composite is the **minimum band over measurement-backed domains only** — D1–D7 (where
data lands) plus D13. Host-scaled/derived (D11/D12) and confounded (D14) are displayed and banded but
**excluded** so a modelled number can never *set* the wall. The composite stays **`<600`**, bound by the
FRR (D2, 75.7%) and ambient-FA/hr (D3, ~82/hr) walls — unchanged by the new domains (they can only lower
or confirm a MIN, and none is lower). EVAL-004 fidelity: the scorer reproduces the committed shipped-static
floor (rank-1 **59.2%**, FRR **75.7% @ FAR 4.6%**) before its bands are trusted — asserted in
`SotaScorecardTest`.

## Labels (EVAL-003 / EVAL-005)

All new numbers are **exploratory / NOT banked**: D7 is an optimistically-biased in-regime proxy; D11/D12
are simulated/derived device estimates; D13 is a real but single-corpus (TORGO speaker-dependent)
measurement; D10 is a null. None is a pre-registered, FAR-matched, replicated headline win. Per-speaker
breakdown and replication (EVAL-005) for D13 come from the Monte-Carlo sweep's seeded iterations over all
TORGO speakers/folds.

## Reproduce

```sh
make sota-score-full SOTA_PY=$HOME/torch-venv/bin/python   # 13/15 banded; D7/D8/D9 via the bridge
make sota-score                                            # JVM-only: D11/D12/D13 land; D7/D8/D9 NOT_MEASURED
./gradlew :core:eval:test --tests "*SotaScorecardTest*"    # band-mapper + battery-model unit tests (no corpus)
```
