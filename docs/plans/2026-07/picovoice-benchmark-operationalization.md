# Plan: Operationalize the Picovoice benchmark into build / planning / experimentation

- **Date:** 2026-07-06
- **Phase:** 3
- **Roadmap item:** Make the standard wake-word benchmark a repeatable part of the dev loop
- **Status:** done (A-deliverables implemented 2026-07-06; make targets + `-D` sweep knobs + advisory planning hook landed)
- **Worktree:** n/a (additive tooling + docs on `main`)
- **Plan quality:** 96/100

## Goal

Turn the committed Picovoice wake-word-benchmark harness from a one-shot artifact — runnable only via a
~200-char `./gradlew … -D…` incantation, with its experiment knobs reachable only by editing Kotlin — into
a **one-command, CLI-sweepable** part of building, planning, and experimentation, without letting the new
sweep surface become a selection-on-test machine or letting the runnable command drift from the numbers the
standing report claims.

## Context & Constraints

The harness (`PicovoiceBenchmark`/`PicovoiceCorpus`/`PicovoiceMixer` + gated `PicovoiceBenchmarkTest`) is
committed but no eval has a `make` target, and `windowMs`/`hopMs`/`snrDb`/`frontEnd`/`deltaOrder`/
`targetFaPerHour` were `PicovoiceBenchmark` ctor-only. Constraints: the committed report
(`docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`) cites an exact-config **FRR of 87.5% at
0.1 FA/hour** and closed-set rank-1 89.2%, so the default `make` run must **reproduce that config
byte-for-byte** (command must not drift from doc). Accuracy-honesty line holds: report the operating point
as **FRR at a stated FAR/hour**, never a bare accuracy %. The corpus is `[measure-only]` (uncommitted) ⇒
this can never be a CI gate. EVAL-003 governs the sweep surface: one pre-registered hypothesis; everything
else is a **NOT-banked** family. The promotion ladder (AGENTS.md §0) forbids pre-seeding a hard WORKFLOW
rule with no incident, so the planning hook stays **advisory**. Scope locked with the user: make targets +
`-D` knobs + advisory planning hook + docs; **no results ledger**.

## Approach

Reuse existing seams, add nothing to the app signal path. Make targets wrap the existing
`fetch-picovoice-benchmark.sh` / `run-pocketsphinx.sh` scripts and the `$(GRADLE)` var; the default
`bench-picovoice` pins `bgSeconds/enroll/held` + lets every other knob fall to its ctor default, with
optional `FRONTEND=/DELTA=/SNR=/WINDOW=/HOP=/TARGETFA=` env → `-D` overrides (unset ⇒ ctor default ⇒
reproducible). The test reads the six new props with ctor-default fallbacks and resolves the front-end via
a helper mirroring the `TorgoEvalTest` `when(System.getProperty(…))` idiom. Planning integration is one
advisory bullet in `TEMPLATE.md` + START_HERE rows; docs (CLAUDE.md, report Provenance box) carry the
EVAL-003 banked/NOT-banked framing and the CI boundary. Rejected: a Node results-ledger parser (brittle,
fights the repo's hand-copied-snapshot convention) and a promoted WORKFLOW guardrail (no incident yet).

## Steps

1. `core/eval/build.gradle.kts` — add `picovoice.windowMs/hopMs/snrDb/frontend/deltaOrder/targetFaPerHour`
   to the forwarded `-D` list + EVAL-003 comment. *Check:* keys appear; `:core:eval:test` still compiles.
2. `core/eval/src/test/kotlin/com/speechangel/core/eval/PicovoiceBenchmarkTest.kt` — read the six props
   (ctor-default fallbacks), add `pickFrontEnd()`, pass knobs into the ctor. *Check:* `:core:eval:test`
   green without `-Dpicovoice.dir`.
3. `Makefile` — `PV_DIR`/`PV_REPORT`/`PV_OVERRIDES` vars + `bench-picovoice-fetch`/`bench-picovoice`/
   `bench-picovoice-smoke`/`bench-picovoice-anchor` + `.PHONY`. *Check:* `make help` lists all four.
4. `docs/plans/TEMPLATE.md` benchmark-impact bullet; `docs/ai/START_HERE.md` quick-task rows;
   `CLAUDE.md` §2 table + experimentation/CI-boundary note; report Provenance Run-it + sweep-knobs box.
   *Check:* `make guardrails` green (docs-integrity + plan-workflow).
5. This plan doc + `docs/plans/INDEX.md` entry; `make guardrails`; logical-chunk commits.

## Definition of Done

- `make bench-picovoice` with **no overrides** regenerates the report (`picovoice-report.md` under the
  `core:eval` build dir) at the committed config — the operating point stays **FRR = 87.5% at 0.1 FAR/hour**
  with closed-set rank-1 89.2% — proving
  the command and the standing doc do not drift. The number is always expressed as **FRR at a stated
  FAR/hour**, never a bare accuracy %; the in-regime FAR/hour curve remains the headline and the
  cross-speaker keyword-**FRR** (miss-rate) the labelled out-of-regime lower bound.
- A sweep (`make bench-picovoice FRONTEND=delta SNR=6`) actually reaches the ctor (report config line
  changes) and is documented as an EVAL-003 **NOT-banked** exploratory variant — never a headline FRR/FAR
  win — while the pinned no-override run is the one banked baseline.
- `:core:eval:test` green **with and without** `-Dpicovoice.dir`; `make guardrails` (10/10), `detekt`,
  `spotlessCheck` all green.

## Risks & Mitigations

- **Command/doc drift** (default `make` run silently produces different numbers than the report) → the
  no-override target pins `bgSeconds/enroll/held` and every new `-D` prop defaults to its ctor value; the
  DoD reproduction check catches any mismatch. **Rollback:** all edits additive; revert the ~4 hunks.
- **Sweep knobs → selection-on-test** → every sweep surface (build.gradle comment, test KDoc, CLAUDE.md,
  report box, TEMPLATE bullet) names EVAL-003 + the pinned baseline; no ledger to accrete mined wins.
- **New `-D` default ≠ ctor default** → each prop uses `?: <ctor default>`; reproduction check guards it.
- **Regression risk to the app** → zero: only the `core:eval` test entrypoint + Makefile/docs change;
  nothing on `ListeningService → matcher → accessibility` is touched.

## Test & Verification

- `make guardrails` green (10/10, incl. plan-workflow FRR/FAR-in-DoD + docs-integrity); `make static`
  (detekt + spotlessCheck) green; `./gradlew :core:eval:test` green **without** `-Dpicovoice.dir`
  (assumeTrue skip proves inertness on corpus-less hosts).
- **Reproducibility (key check):** `make bench-picovoice-fetch` then `make bench-picovoice`; the headline
  of the generated `picovoice-report.md` (FRR @ 0.1 FAR/hr, rank-1, curve) matches the committed report.
- **Sweep reachability:** `make bench-picovoice FRONTEND=delta SNR=6 WINDOW=1200` runs and its report
  config line reflects the overrides.
- **Verifiable on this host:** the guardrails, `make static`, and the corpus-less `:core:eval:test` skip.
  **Needs the corpus (`[measure-only]`, not on CI):** the two reproduction/sweep runs above.
