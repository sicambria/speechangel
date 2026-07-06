# Real FRR/FAR — TORGO (torgo), speaker-dependent

Produced by `TorgoEval` (`core:eval`) over the TORGO corpus — the first **real,
non-synthetic** SpeechAngel recognizer measurement.

> **Provenance:** generated 2026-07-06 by `./gradlew :core:eval:test --tests "*TorgoEvalTest*"
> -Dtorgo.dir=<TORGO F root> -Dtorgo.report=<this file>` (TORGO dysarthric-female speakers
> F01/F03/F04, ~1.14 GB, direct download, `[measure-only]` — not committed). Reproducible on any host
> with the corpus; the harness (`WavFile`, `TorgoCorpus`, `TorgoEval`) is committed. This retires the
> `SYNTHETIC` banner for the Phase-0 "Measure FRR/FAR" item — the **FRR half only**; the always-on
> ambient FAR/hour budget is not measured here (see the last section).

## Verdict — GO (the core hypothesis holds; the baseline is not yet deployable)

**The existential question — "does MFCC-DTW template matching extract usable signal from real
dysarthric speech?" — is answered YES.** Speaker-dependent rank-1 (nearest-template) accuracy is
**10–40× chance** (F01: 68.8% on a 15-word vocabulary vs 6.7% chance; F03: 53.5% on 77 words vs 1.3%
chance). The signal is unambiguously real, so the rest of the roadmap is **worth executing**.

**But the raw single-template, un-calibrated baseline is not deployable.** At the always-on-relevant
low-FAR operating point (OOV FAR ≤ 5%) FRR is **60–79%** — most commands are missed. The gap between
"real signal" and "usable product" is precisely what the enhancement roadmap targets: multi-template
voting (`Recognizer` already votes — this eval is single-/few-template per fold, a **lower bound**),
per-command threshold calibration (`ThresholdCalibrator`, already built), the QbE embedding
enhancement, and a realistic ~10–20-command vocabulary (the **top** of the rank-1-vs-vocabulary curve,
not the 77-word tail). None of those has been applied here — this is the un-enhanced floor.

**Re-score trigger:** this moves the product from "accuracy entirely unmeasured" (the pre-alpha gating
risk) to "measured floor, with a quantified improvement path." It does **not** claim a deployable
number.

## Control contrast — dysarthria is a real degrader

The same harness run over TORGO **control** speakers (typical speech, `FCX` set) isolates what
dysarthria costs (run: `-Dtorgo.dir=<TORGO FC root>`; the auto-report labels every set "dysarthric" —
that string is hard-coded in the renderer, so the control figures are transcribed here by hand):

| Group | Speakers | Rank-1 (aggregate) | Matched small-vocabulary rank-1 |
|---|---|---:|---|
| **Dysarthric** (F) | F01 / F03 / F04 | **55.4%** | F01 (15 cmds): **68.8%** |
| **Control** (FC) | FC01 / FC02 / FC03 | **74.6%** | FC01 (16 cmds): **91.2%** |

Per control speaker: FC01 (16 cmds) 91.2%, FC02 (121) 78.9%, FC03 (136) 69.5% — the controls clear
~70–91% rank-1 even at 5–8× the vocabulary size of the dysarthric speakers. At **matched** small
vocabularies the gap is ~22 points (91.2% control vs 68.8% dysarthric). **Conclusion:** dysarthria
specifically degrades the MFCC-DTW matcher, so the roadmap's dysarthria-focused enhancements (QbE,
far-field front-end, adaptation) are aimed at a real effect — **and** even control speech at FRR ≈ 75%
@ FAR ≤ 5% is not deployable on the un-tuned single-template baseline, so the calibration/multi-template
work is needed regardless of impairment.

## Methodology
- **Speaker-dependent:** enrollment + test are always the same speaker (the product's
  "teach it your voice" model). No cross-speaker matching.
- **Front-end:** `delta_delta` (MFCC, deltaOrder=DELTA_DELTA); mic: `wav_headMic` (clean head-mic).
- **Split:** 5-fold within speaker — each utterance is a test query exactly once and an
  enrollment template in the other folds (never trained on the utterance it is tested on).
  Chosen over a fixed enroll/test split because real per-speaker repetition depth is thin
  (most words repeat 2–3×), so k-fold uses every repetition.
- **Honesty on the split:** folds are index-round-robin, **not** session-stratified, so
  same-session enroll/test pairs occur (and F01 has a single session, so it is entirely
  same-session). Same-session pairing makes FRR **optimistic** vs enroll-once/use-later
  product reality — the real-deployment number is if anything worse, not better, than below.
- **Vocabulary:** command = a ≤2-token lexical prompt (brackets stripped) with ≥2
  utterances for that speaker; TORGO `xxx` markers, picture prompts, and reading-passage
  sentences excluded. Every remaining single-instance word → OOV negative (`truth=null`).
- **Metrics are threshold-free where possible.** The synthetic default acceptance
  threshold (8.0) is meaningless on real MFCC-DTW
  distances, so the headline is **rank-1 closed-set accuracy** (is the nearest enrolled
  template the correct command?) plus the **equal-error operating point** from a
  self-ranged threshold sweep (FRR balanced against OOV false-accept rate).

## Aggregate (3 dysarthric speakers)
- Positives: 267 · OOV negatives: 415 · Enrollment failures: 0 · Empty-query (VAD-eaten): 0
- **Rank-1 accuracy: 55.4%** (nearest template is the correct command)
- **At the equal-error operating point** (threshold 24.21): **FRR 49.4%**, **OOV FAR 49.4%** over 841.7 s of OOV audio.
- **At a low-FAR operating point** (OOV FAR ≤ 5.0%, the always-on regime): **FRR 77.9%**.
- Distance-to-true-command: median 23.0, p90 34.3.

Note: the aggregate blends different vocabulary sizes (chance rank-1 differs ~5× across
speakers) — read the per-speaker rank-1-vs-vocabulary column, not the blended figure.

## Per speaker (rank-1 vs vocabulary size)

| Speaker | Commands | Positives | Empty-Q | Rank-1 | Chance | FRR@EER | FAR@EER | FRR@FAR≤5% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F01 | 15 | 32 | 0 | 68.8% | 6.7% | 37.5% | 37.9% | 78.1% |
| F03 | 77 | 185 | 0 | 53.5% | 1.3% | 53.5% | 53.4% | 78.9% |
| F04 | 21 | 50 | 0 | 54.0% | 4.8% | 48.0% | 47.6% | 60.0% |

Rank-1 falls as the command vocabulary grows (fewest commands = highest rank-1). A realistic
SpeechAngel deployment is ~10–20 commands, i.e. the **top** of this curve, not the 77-word tail.

## What this does and does not measure
- **Measures:** speaker-dependent discrimination (rank-1) on real dysarthric speech, and
  the FRR/OOV-FAR trade-off at a calibrated operating point.
- **Rank-1 is the hypothesis test.** It ignores the acceptance threshold entirely, so it
  is not confounded by the un-tuned synthetic default. A near-chance rank-1
  (≈ 1/commands) would refute the matcher; a high rank-1 means the discrimination is
  real and the deployment problem is threshold calibration (`ThresholdCalibrator`).
- **Does NOT measure:** the Phase-0 exit's always-on **ambient** FAR/hour budget
  (≤0.5 false accepts/hr on continuous audio). TORGO has no continuous ambient stream,
  so the OOV FAR here is a per-utterance rate, not per-hour-of-listening.
- **VAD is clean on both sides.** Enrollment failures = utterances the energy-VAD /
  `minSpeechFrames` gate dropped at enroll; empty-query positives = queries trimmed to
  nothing at test. Both are 0 here, so neither the misses nor the earlier
  100%-FRR-at-default-threshold are trimming artifacts — the miss rate is the matcher, and
  the earlier 100% was purely the un-tuned synthetic threshold.
