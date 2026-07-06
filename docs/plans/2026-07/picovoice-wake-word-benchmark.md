# Plan — Integrate & run the Picovoice wake-word-benchmark

- **Status:** done (A-deliverables implemented 2026-07-06; harness + report + same-host anchor landed)

## Goal

Give SpeechAngel its first head-to-head placement on a **standard, public** benchmark — the
[Picovoice wake-word-benchmark](https://github.com/Picovoice/wake-word-benchmark) (miss-rate at 1 FA /
10 hr on keyword recordings woven into LibriSpeech + DEMAND noise @ 10 dB SNR) — wired permanently into
`core:eval` with a committed report, closing the SOTA scorecard's "no head-to-head on identical data" gap.

## Context & Constraints

The scorecard (`docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md`) has only *directional*
SOTA references. Constraints locked with the user: **no external accounts** (no Picovoice key, no Kaggle)
→ anchor is **PocketSphinx** (open-source, no key) not Porcupine; DEMAND from **Zenodo**; Kotlin mixer (no
numpy/soundfile). SpeechAngel is **speaker-dependent / few-shot**; the keyword takes are 50+ unlabeled
speakers and the benchmark's engines are speaker-independent — so the two benchmark metrics have opposite
validity and must be **decomposed by metric** (FA/hour in-regime; detection miss-rate out-of-regime).

## Approach

Reuse the existing eval seams rather than rebuild: `AmbientFar` (windowed FA/hr), `Enroller`/`Evaluator`
(enroll + min-DTW), `AudioAugment` (SNR mix), `WavFile`, and the `-D`-gated JUnit pattern. Build one
labelled LibriSpeech+DEMAND stream per keyword (`PicovoiceMixer`), compute the raw min-DTW distance once
per window, and sweep the acceptance threshold analytically → FA/hour curve (headline) + cross-speaker
miss-rate curve (lower bound). Dump the mixed WAV + labels so a same-host PocketSphinx run scores identical
bytes.

## Steps

1. `scripts/eval/fetch-picovoice-benchmark.sh` — open-download provisioning (Picovoice repo + LibriSpeech
   from OpenSLR + DEMAND 16 kHz from Zenodo), ffmpeg FLAC/WAV → 16 kHz mono.
2. `PicovoiceCorpus` (scan + enroll/held-out split) and `PicovoiceMixer` (JVM `mixer.py` reimpl).
3. `PicovoiceBenchmark` (per-window min-DTW, threshold sweep, AmbientFar cross-check, combined rank-1,
   WAV+label dump, markdown report) + gated `PicovoiceBenchmarkTest` + pure `PicovoiceMixerTest`; `-D`
   forwards in `build.gradle.kts`.
4. `scripts/eval/run-pocketsphinx.sh` — same-host anchor (best-effort; falls back to published numbers).
5. Report `docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`; scorecard factor-4 + DOC_TOC updates.

## Definition of Done

- Harness produces a committed report expressing the operating point as **FRR + FAR** (never a bare
  accuracy %): the **FAR/hour** curve (in-regime headline) and the cross-speaker keyword-**FRR**
  (miss-rate) curve on a single threshold axis, plus the clean closed-set rank-1. The honest measured
  result: at the benchmark's **0.1 FAR/hour** target the keyword **FRR is 87.5%** (no viable always-on
  point), while closed-set discrimination rank-1 is 89.2% — the number is always given as FRR at a stated
  FAR/hour, not a standalone success rate.
- `:core:eval:test` green with **and** without `-Dpicovoice.dir` (gated test skips absent the corpus);
  `make guardrails`, `detekt`, `spotlessCheck` all green.

## Risks & Mitigations

- **Overselling a cross-speaker number** → hard-labelled out-of-regime lower bound in code + report;
  never a "SpeechAngel vs engine" headline. **Rollback:** the harness is additive and `-D`-gated; deleting
  the new `core:eval` files + `build.gradle.kts` forwards fully reverts it with no runtime impact.
- **No 0.1 FA/hr operating point** → report the full curve + best-achievable point, not a forced number.
- **PocketSphinx wheel/perf on Python 3.14** → best-effort; single-threshold decode; documented fallback
  to Picovoice's published numbers. **Rollback:** anchor is a standalone script, safe to drop.
- **Small FA denominator** → `-Dpicovoice.bgSeconds` raises it; the finding is threshold-independent.

## Test & Verification

`make guardrails` green (10/10); `detekt` + `spotlessCheck` green; `:core:eval:test` green with and
without `-Dpicovoice.dir`. Dumped WAV verified 16 kHz mono s16 via `ffprobe`; mixer intervals + split
covered by pure `PicovoiceMixerTest`; curve monotonicity asserted in-harness. End-to-end run generates
`docs/testing/2026-07-06_picovoice-wake-word-benchmark.md` numbers on the real corpus.
