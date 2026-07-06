# Real FRR/FAR — TORGO, speaker-dependent, **held-out** (EVAL-002)

Produced by `TorgoEval` (`core:eval`) over the TORGO corpus. This supersedes the first-pass version of
this report: it (1) corrects the "multi-template voting" framing (the matcher is 1-NN min-distance, not
a vote — `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md`), and (2) replaces the
in-sample threshold sweep with **leave-one-fold-out** threshold selection, so the FRR/FAR operating
points are honest held-out numbers, not fit on the rows they are reported at (rule **EVAL-002**).

> **Provenance:** generated 2026-07-06 by `./gradlew :core:eval:test --tests "*TorgoEvalTest*"
> -Dtorgo.dir=<root> -Dtorgo.report=<file> [-Dtorgo.grid=true]`. Dysarthric set = `~/torgo`
> (F01/F03/F04); control set = `~/torgo/FCX` (FC01/FC02/FC03). TORGO is `[measure-only]`, direct
> download, never committed; the harness (`WavFile`/`TorgoCorpus`/`TorgoEval`) is committed and
> `:core:eval:test` stays green with the corpus absent.

## Verdict — GO (hypothesis holds; baseline not deployable; one real front-end lever found)

1. **The core hypothesis still holds.** Held-out rank-1 (nearest-template, threshold-free) is **10–40×
   chance** on real dysarthric speech (55.4% aggregate; F01 68.8% on 15 words vs 6.7% chance). The
   MFCC-DTW matcher extracts real signal.
2. **The single-template baseline is still not deployable, and the held-out number confirms it
   honestly.** Held-out global-threshold FRR at the always-on FAR≤5% operating point is **78.3%** —
   essentially equal to the old in-sample 77.9% (held-out ≈ in-sample here, so the baseline was not an
   artifact of in-sample optimism).
3. **Per-command threshold calibration does NOT improve this** — an important negative result (below).
4. **The front-end bake-off surfaced a directional hypothesis:** static MFCC is best (or tied-best) in
   all three speakers and noise reduction is consistently worse — but the aggregate margin (59.2% vs
   55.4%) is within sampling error, so this is a hypothesis to power-test, not an established gain (D3).

## D1 — Held-out per-command calibration is a non-improvement (EVAL-002)

The product's `ThresholdCalibrator` sets each per-command threshold from the negatives in the **same**
data it scores. Measured that way it looks like a large FRR win — but that win is in-sample fitting. Fit
the per-command budget on the **train** folds and score the **held-out** fold instead (leave-one-fold-
out; both methods target FAR≤5% on train and are read at their **realized held-out FAR**, so the
comparison is matched-FAR):

| Speaker | Commands | Rank-1 (HO) | FRR@FAR≤5% (global, HO) | realized FAR | FRR (per-cmd, HO) | realized FAR | FRR (in-sample ref) |
|---|---:|---:|---:|---:|---:|---:|---:|
| F01 | 15 | 68.8% | 81.3% | 4.5% | 40.6% | **24.2%** | 78.1% |
| F03 | 77 | 53.5% | 80.5% | 4.5% | 55.1% | **34.1%** | 78.9% |
| F04 | 21 | 54.0% | 62.0% | 5.6% | 58.0% | **27.0%** | 60.0% |
| **ALL** | — | **55.4%** | **78.3%** | 5.1% | (per-speaker only) | — | 77.9% |

The per-command FRR looks lower (40–58%) **only because its held-out FAR blew the budget to 24–34%** —
5–7× the FAR≤5% target. Train-fit thresholds don't generalize: commands with no (or few) training
negatives fall back to "accept everything" (`ThresholdCalibrator.kt:63`) and accept arbitrary OOV audio
on the held-out fold. At **matched** FAR the global threshold wins. So per-command calibration, as
built, is not a deployable improvement — and the shipped `calibrate(corpus)` will likewise over-promise
its FA budget in the field (it calibrates on the user's own enrollment set). This is rule EVAL-002.

*Future work:* the held-out FAR blows up specifically through commands with **no** training negative,
which fall back to accept-all (`maxObserved+1`). Falling those back to the **global** held-out threshold
instead of accept-all is the natural next lever that might make per-command competitive — deferred here
(rescuing it invites its own selection bias and needs its own held-out check).

## D2 — Deployment-relevant slice (≤ 25 commands)

A real SpeechAngel deployment is ~10–25 commands (F01=15, F04=21), not the 77-word F03 reading-passage
tail. Restricting to that a-priori slice (stated before looking at results, not tuned):

- **Held-out global-threshold FRR 70.7%** at realized FAR 6.3%; held-out rank-1 **59.8%**.
- In-sample reference: FRR 72.0%.

Better than the tail-blended 78.3%, and the honest number to quote for the product's actual vocabulary
regime — still not deployable on the single-template baseline, which is the point of the roadmap's
multi-template / QbE bets.

## D3 — Front-end bake-off on real dysarthric voices (held-out rank-1)

Full {static, +Δ, +Δ+ΔΔ} × {noiseReduction off/on} grid, metric = held-out rank-1 (threshold-free, no
operating-point fitting). Full grid shown — losing cells included:

| Front-end | Aggregate rank-1 | F01 | F03 | F04 |
|---|---:|---:|---:|---:|
| **`none`** (static MFCC) | **59.2%** | 71.9% | 56.8% | 60.0% |
| `delta` | 57.3% | 71.9% | 54.6% | 58.0% |
| `delta_delta` (current default) | 55.4% | 68.8% | 53.5% | 54.0% |
| `none+nr` | 55.1% | 71.9% | 51.4% | 58.0% |
| `delta+nr` | 52.4% | 65.6% | 49.2% | 56.0% |
| `delta_delta+nr` | 52.4% | 65.6% | 49.7% | 54.0% |

**Winner by stated prior** (highest aggregate held-out rank-1; ties → simpler front-end): **`none`
(static MFCC) at 59.2%**, nominally ~4 points above the hardcoded `delta_delta` (55.4%).

**Read this as a direction, not an established gain.** `none` is the max of 6 correlated cells, and the
margins are within what this sample resolves: 55.4→59.2 aggregate is ≈1.3 SE (n=267, and the aggregate
blends speakers this report otherwise warns against); per-speaker the static-vs-delta_delta deltas are
F01 68.8→71.9 (n=32), F03 53.5→56.8 (n=185), F04 54.0→60.0 (n=50) — all inside sampling error. What *is*
robust is the **direction**: static is best (or tied-best) in all three speakers, and noise reduction is
worse in all three dry/NR pairs. So the honest claim is "static-MFCC-and-no-NR is a real hypothesis
worth a powered test," not "a 4-point win." Establishing it needs a paired test (McNemar on per-utterance
static-vs-delta_delta outcomes), not a best-of-grid max. Accordingly this is **not** applied to the
runtime matcher (out of `core:eval` scope); adoption is gated on that paired test + a control-grid
replication (not run — ~6× DTW cost) + an on-device check.

## Control contrast — dysarthria is a real degrader, and the front-end lever generalizes

The same harness (same held-out method) over TORGO **control** speakers (typical speech, `FCX` =
FC01/FC02/FC03) isolates what dysarthria costs:

| Speaker | Commands | Rank-1 (HO) | FRR@FAR≤5% (global, HO) | realized FAR | FRR (per-cmd, HO) | realized FAR |
|---|---:|---:|---:|---:|---:|---:|
| FC01 | 16 | **91.2%** | 50.0% | 4.4% | 11.8% | **23.1%** |
| FC02 | 121 | 78.9% | 67.5% | 5.2% | 35.6% | **34.3%** |
| FC03 | 136 | 69.5% | 71.0% | 5.0% | 38.9% | **40.8%** |
| **ALL** | — | **74.6%** | **75.1%** | 4.9% | — | — |

Three findings, all confirming the dysarthric story:
- **Dysarthria is a real degrader.** Aggregate held-out rank-1 is **74.6% control vs 55.4% dysarthric**;
  at *matched* small vocabulary the gap is ~22 points (FC01 91.2% on 16 cmds vs F01 68.8% on 15). So
  the roadmap's dysarthria-focused bets (QbE, adaptation) aim at a real effect.
- **The held-out global baseline is honest on control too:** FRR 75.1% @ FAR 4.9% ≈ in-sample 75.4%
  (held-out ≈ in-sample, so neither number is an in-sample artifact).
- **Per-command calibration overfits on control too** — realized held-out FAR 23–41% (again the
  accept-all fallback), so D1's non-improvement is not dysarthria-specific; it is the calibrator.
- **Control deployment slice (FC01, ≤25 cmds):** held-out global FRR **50.0%** @ FAR 4.4%, rank-1 91.2%
  — the best case (typical speech, small vocab). Notably its *in-sample* reference (38.2%) is 12 points
  rosier than held-out — exactly the in-sample optimism EVAL-002 exists to strip out.

**Front-end grid on control: not run.** The 6-cell grid over the 121/136-command control speakers is
~6× the DTW cost and did not complete in a practical window; the static-MFCC-beats-delta-delta finding
(D3) is therefore **dysarthric-corpus evidence only**. Confirming it generalizes to control is the
remaining gate before adopting a front-end default change.

## What this does and does not measure

- **Measures:** held-out speaker-dependent discrimination (rank-1) on real speech, and the held-out
  FRR/OOV-FAR trade-off at a matched, train-calibrated operating point.
- **Does NOT measure:** the Phase-0 exit's always-on **ambient** FAR/hour budget (≤0.5 FA/hr on
  continuous audio). TORGO has no continuous ambient stream, so the OOV FAR here is per-utterance, not
  per-hour-of-listening. This retires the **FRR half** of Phase-0 "Measure FRR/FAR" only.
- **The matcher is 1-NN (min DTW), not a vote.** More enrolled templates per command (nearest-
  neighbour), and the QbE embedding, remain the improvement path — per-command threshold calibration
  does not (D1).
- **Residual leak (disclosed):** k-fold shares *enrollment* audio across folds, so calibration
  distances are not fully independent of the test fold's audio — second-order (enrollment overlap, not
  test-label overlap), standard in k-fold threshold transfer, and makes held-out FRR if anything
  optimistic, never pessimistic.
