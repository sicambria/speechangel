# FRR / FAR report template

The honest accuracy contract for SpeechAngel: recognizer accuracy is **always** reported as
**FRR (false reject rate)** plus a **false-accept count over a stated negative-audio duration**
(from which a FAR/hour is derived *with* its duration and a resolvability caveat) — **never** a bare
percentage like "99 %". This file documents the corpus format the `core:eval` harness consumes so real
recordings can be dropped in and measured.

## How to produce a real measurement

1. Record a labeled corpus (see format below) including **real, varied voices — explicitly including
   dysarthric / atypical speech**, in **quiet** and **home-noise** conditions.
2. Load it into a `com.speechangel.core.eval.Corpus` (raw `AudioSamples`, not pre-extracted templates).
3. Calibrate per-command thresholds: `ThresholdCalibrator(frontEnd).calibrate(corpus)`.
4. Evaluate: `Evaluator(frontEnd).evaluate(corpus, calibration.thresholds)` → `EvalReport.render()`.
5. Compare front-ends: `FrontEndBakeoff(frontEnds).run(corpus).render()`.

## Corpus format

| Field | Meaning |
|---|---|
| `EnrollmentSample(commandId, audio, condition)` | A raw enrollment recording. Several per command, across `VoiceCondition`s (NORMAL/TIRED/ILL/OTHER), is the voice-drift defense. |
| `LabeledUtterance(audio, truth, condition, source)` | A test utterance. `truth = CommandId` for a positive; `truth = null` for a **negative/OOV** sample (used for FAR). |

## Reported metrics (per front-end, per operating point)

- **FRR** overall, **per command**, and **per `VoiceCondition`** (a substitution counts as a false
  reject; the confusion map preserves the detail).
- **False-accept count** with the **negative-audio duration** that produced it. A FAR/hour is derived
  but is only meaningful with enough negative audio — sub-1/hr rates are *not* resolvable from a few
  minutes of negatives.
- The **minimum negative-audio duration** for the FAR budget to be meaningful (the duration at which
  the budget corresponds to ≥ 1 expected false-accept).

## FAR budget (calibration)

Aggregate target: **≤ 1 false-accept per 30 min of negative audio** as the working operating point;
the Phase-0 **exit** goal is **≤ 0.5 false accepts/hr** in quiet for distinct commands. The calibrator
splits the budget equally across commands (cumulative rounding) and sets each per-command threshold
just below the constraining negative distance.

## Honesty note

The harness ships with a **synthetic** corpus (`SyntheticCorpus`) for self-test only; its output is
banner-marked `SYNTHETIC` and is **not** a real measurement. The Phase-0 exit criterion in
`docs/ROADMAP.md` stays open until a real labeled corpus (incl. dysarthric voices) has been measured
through this harness.
