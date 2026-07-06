# Active Development Rules

Promoted, numbered **technical** rules — code-level conventions that earned their place by an
incident or a recurring failure class. This file starts **empty by design**: rules are added only
when an incident in `docs/errors/` justifies promotion (see the ladder in `AGENTS.md` §0).

For agent-neutral *behavior* rules (how to work), see `docs/ai/AI_BEHAVIOR_GUARDRAILS.md`.

---

## Numbering convention

- Rules are numbered per area, e.g. `DSP-001`, `MATCH-001`, `ANDROID-001`, `BUILD-001`, `WORKFLOW-001`.
- Each rule records: **the rule** (one imperative sentence), **why** (the incident that promoted it,
  linked by `docs/errors/2026-06/<file>.md` code-path), and **the gate** (the
  `scripts/audits/<verifier>.mjs` or test that enforces it, or `advisory` if not yet automated).
- A rule is only added here after its class recurs with low false positives. Do not pre-seed.

### Areas

- **BUILD** — Gradle, version catalog, wrapper, reproducibility.
- **ANDROID** — manifest, foreground service, accessibility, permissions, Play policy.
- **DSP** — MFCC / VAD / framing signal-processing rules (`core:dsp`).
- **MATCH** — DTW / template-matching / threshold rules (`core:matching`, `core:enrollment`).
- **MODEL** — domain model invariants (`core:model`).
- **WORKFLOW** — plan/worktree/incident process rules.

---

## Rules

### MATCH-001 — Test behaviour-defining defaults at their shipped value
Any constant that defines runtime behaviour (e.g. `MatcherConfig.defaultAcceptanceThreshold`) MUST have
an end-to-end test that exercises the **shipped** default, not a permissive stand-in. Asserting only
*discrimination* with a relaxed threshold can hide a config that rejects all real input.
- **Why:** `docs/errors/2026-06/2026-06-28_shipped-config-untested-by-permissive-test-threshold.md`
- **Gate:** `core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/RecognizerTest.kt` ("shipped default config accepts …"); real-audio FRR/FAR calibration tracked in `docs/ROADMAP.md`.

### BUILD-001 — Pin the JDK; never assume the host default
Invoke Gradle through `make` or with `JAVA_HOME` pinned to JDK 21 (`/usr/lib/jvm/java-21-openjdk-amd64`).
The host default JDK is 25, which AGP 8.7 does not support. The shell only runs absolute binary paths.
- **Why:** `docs/errors/2026-06/2026-06-28_host-toolchain-jdk-and-shell-quirks.md`
- **Gate:** `scripts/setup/check-env.sh` (`make setup`); CI uses `setup-java@v4` JDK 21.

### BUILD-002 — Compose-friendly ktlint; verify with spotlessCheck
Keep `function-naming` / `property-naming` ktlint rules disabled for Kotlin (Compose uses PascalCase
composables and theme vals). Confirm formatting with `spotlessCheck`, never a bare `spotlessApply`
exit code (the configuration cache can serve a partial apply).
- **Why:** `docs/errors/2026-06/2026-06-28_spotless-ktlint-compose-and-config-cache.md`
- **Gate:** `.editorconfig` + root Spotless config; `spotlessCheck` in `make verify` and CI.

### MATCH-002 — Read the test before streaming into a DTW-based gate
Before designing a per-frame streaming driver for any `evaluate()` / `match()` API that uses
length-normalized DTW: read the existing tests to see what *input size* the passing cases use.
Length-normalized DTW handles tempo variation of the same *content*; it does **not** make a short
fragment match a full-utterance template. Silently wrong results (always-NoMatch) are harder to
catch than crashes.
- **Why:** `docs/errors/2026-06/2026-06-28_wake-gate-requires-utterance-not-frame.md`
- **Gate:** advisory; the rolling-window pattern in `ListeningService` is the reference implementation; `WakeWordGateTest.kt` is the API-contract source-of-truth.

### BUILD-003 — Bring up each module standalone
Compile and test each Gradle module green in isolation before wiring the next; never enable the whole
module graph blind. This localises version-coupled API mismatches.
- **Why:** `docs/errors/2026-06/2026-06-28_module-bringup-compile-gotchas.md`
- **Gate:** advisory (workflow rule); backstopped by `make verify`.

### EVAL-001 — Never report an absolute FRR/FAR at a cross-distribution threshold
A recognizer accuracy number read at a fixed acceptance threshold is only meaningful on the data
distribution that threshold was tuned for. The synthetic tone corpus and real speech produce DTW
distances on different scales, so an absolute FRR/FAR at `MatcherConfig.defaultAcceptanceThreshold`
on real audio is garbage (it produced a false 100% FRR on TORGO). Report **rank-1** (threshold-free)
as the hypothesis test and derive FRR/FAR from a **self-ranged sweep** (EER / low-FAR). Always surface
**both** enroll-side and query-side VAD drop counts so a trimming artifact cannot masquerade as a
matcher result.
- **Why:** `docs/errors/2026-07/2026-07-06_synthetic-threshold-meaningless-on-real-audio.md`
- **Gate:** advisory; `core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt` is the
  reference implementation (rank-1 + self-ranged EER + `emptyQueries`/`enrollmentFailures`).
