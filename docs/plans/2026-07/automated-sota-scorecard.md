# Plan: Automated SOTA Scorecard (measured performance → 0–1000 band map)

- **Date:** 2026-07-08
- **Phase:** n/a (measurement tooling)
- **Roadmap item:** Automate the `SOTA=1000` domain-band scoring — turn the hand-typed "Current band"
  column of `docs/product/2026-07-08_sota-domain-bands.md` into a reproducible measured pipeline.
- **Status:** done (A-deliverables implemented 2026-07-08)
- **Worktree:** n/a (measure-only tooling on main; no product-runtime change)
- **Plan quality:** 94/100 (advisor-gated design; two recon agents mapped the building blocks)

## Goal

Provide **one command** that measures real recognizer performance and reports where SpeechAngel sits on
the 15-domain `SOTA=1000` ladder — replacing the hand-assembled band map. Before this, the measurement
harnesses existed but nothing ran them, mapped values to bands, or composited a score; the doc's bands
were typed by hand.

## Context & Constraints

- **Wall-dominated composite, never a mean** — the headline is the *minimum* band over shipped-system
  domains; one `<600` wall (FRR / ambient FA/hr) blocks deployability regardless of strong domains. A
  mean would launder `<600` walls into a mid-600s vanity score.
- **No fabrication** — a domain with no real measurement on this host is `NOT_MEASURED` with the exact
  reason/command, never a guessed band. Coverage (measured/15) is reported.
- **Fidelity (EVAL-004)** — the scorer must reproduce the committed shipped-static numbers before its
  bands are trusted: dysarthric rank-1 **59.2%**, held-out **FRR 75.7% @ FAR 4.6%** (static MFCC `none`,
  TORGO speaker-dependent, EVAL-002). Config-explicit provenance on every value.
- **Fidelity-of-measurement is first-class** — simulated-channel (noise/reverb/bandwidth), proxy
  (ambient FA/hr), and low-fidelity/confounded (vocab, enrollment) measurements are tagged; low-fidelity
  ones are excluded from the authoritative composite, not laundered into a clean band.
- **Honesty banner** — the generated report carries the SYNTHETIC-proxy + SIMULATED-channel caveats
  (`verify-sota-measurement.mjs` discipline).
- **SSL domains via a structured bridge** — D7/8/9 are read from a key=value metrics file the Python
  spikes emit (`--emit`), never parsed from prose stdout. Torch lives in an isolated venv
  (`$(HOME)/torch-venv`, Python 3.11; system Python 3.14 has no torch wheels), SSL weights already cached.

## Approach

1. **Thresholds-as-data** — `DomainBands` (Kotlin object) encodes the 15 domains × band cutoffs +
   direction, the single source of truth; the doc's hand-typed table should agree (a consistency-check
   guardrail is a fast-follow). A pure `bandFor()` maps a measured value → band.
2. **`SotaScorecard` (`core:eval`)** — runs the JVM-measurable domains via the real entry points
   (`TorgoEval.run`, `ConditionEval.run`, `AmbientFar.measure`) on the shipped static-MFCC front-end,
   reads the optional SSL metrics bridge, assembles per-domain bands + the wall-dominated headline, and
   emits `sota-scorecard.md` + `sota-score.json`.
3. **Python `--emit`** on `sweep_ssl.py` (D9 ceiling) + `dual_cascade_verify.py` (D8) → structured
   metrics the scorer folds in.
4. **`make sota-score`** (JVM-only) / **`make sota-score-full`** (adds torch-backed D8/D9 via
   `SOTA_PY=<venv python>`).

Rejected: a Node orchestrator parsing prose reports (fragile); a single mean composite (dishonest —
inflates past the walls).

## Steps

1. `core/eval/src/main/kotlin/com/speechangel/core/eval/DomainBands.kt` — thresholds + `bandFor` (done).
2. `core/eval/src/main/kotlin/com/speechangel/core/eval/SotaScorecard.kt` — measure + composite + render (done).
3. `core/eval/src/test/kotlin/com/speechangel/core/eval/SotaScorecardTest.kt` — band-mapper fidelity unit test + gated integration test (done).
4. `core/eval/build.gradle.kts` — forward `-Dsota.ssl/report/json` (done).
5. `scripts/eval/ssl_frontend_spike/{sweep_ssl,dual_cascade_verify}.py` — `--emit` (done).
6. `Makefile` — `sota-score` / `sota-score-ssl` / `sota-score-full` (done).

## Definition of Done

- `make sota-score` runs against TORGO and emits the band map + JSON with a **wall-dominated composite of
  `<600`**, bound by the FRR and ambient-FA/hr walls.
- The scorer **reproduces the committed shipped-static floor**: rank-1 **59.2%** (band 600) and held-out
  **FRR 75.7% @ FAR 4.6%** (band `<600`) — the fidelity gate; asserted in `SotaScorecardTest`.
- The band-mapper unit test reproduces the committed table on unambiguous values (rank-1 59.2%→600,
  FRR 75.7%→`<600`, FRR 5%→900, ambient ~82/hr→`<600`).
- Every measured value is config-explicit; unmeasurable domains are `NOT_MEASURED` with a reason; the
  report carries the SYNTHETIC/SIMULATED honesty banner.
- `make sota-score-full` folds in the torch-backed research-tier domains (D8 dual-cascade rel FRR
  reduction, D9 SSL rank-1 ceiling), flagged off-device/not-shipped and excluded from the shipped
  composite.
- `node scripts/audits/run-all.mjs` = 11/11 PASS; `:core:eval:test` green.

## Risks & Mitigations

- **Risk:** the scorer laundized a weak/simulated measurement into an authoritative band. **Mitigation:**
  fidelity is a first-class field; low-fidelity (vocab, enrollment) domains are excluded from the
  composite; simulated/proxy are tagged; the composite is over shipped-system domains only and flagged
  optimistically biased.
- **Risk:** the strict band-mapper disagrees with the hand-typed doc. **Mitigation:** intended — the
  scorer is ground truth; it surfaced that the doc's D5 reverb `700` was a rounding fudge (64.6% is
  `<600` against the ≥65% cut). Recorded as a finding, not silently reconciled.
- **Risk:** torch install / SSL model-load hang (host history). **Mitigation:** isolated CPU venv, cached
  weights, timeout-guarded runs; `sota-score` (JVM-only) needs no torch and always works. **Rollback:**
  `git revert` (measure-only; no product-runtime code touched).

## Test & Verification

- `./gradlew :core:eval:test --tests "*SotaScorecardTest*"` (no corpus) → band-mapper fidelity unit test
  green (verified 2026-07-08).
- `make sota-score` (TORGO present at `$(HOME)/torgo`) → integration test green; reproduces rank-1 59.2%
  / FRR 75.7% @ FAR 4.6%; wall-dominated composite `<600`; report written to build/sota-scorecard.md
  (a generated build output — verified 2026-07-08).
- `make sota-score-full SOTA_PY=$(HOME)/torch-venv/bin/python` → adds D8/D9 (reproducing the banked
  references: dual-cascade ~49.5% rel FRR reduction on F03 → band 900; WavLM ceiling ~71.9% rank-1 →
  band 800).
- **No product-runtime / matcher / DSP / threshold code changed** → no `make bench-picovoice` re-run
  needed; this is measure-only tooling that consumes the existing harnesses.
