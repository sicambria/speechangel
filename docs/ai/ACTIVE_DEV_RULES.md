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

### EVAL-002 — Select thresholds held-out; compare methods only at matched FAR
An FRR/FAR "improvement" is real only if (a) the threshold was chosen on data **disjoint** from the
trial it is scored on, and (b) competing methods are read at the **same** FAR. Fitting a threshold on
the very rows you report — `ThresholdCalibrator.calibrate(corpus)` sets each per-command threshold just
below that corpus's own negatives (`ThresholdCalibrator.kt:59`) — makes FAR at-budget *by construction*
and FRR optimistic; it is EVAL-001 pointed the other way (a rosy number instead of a pessimistic one).
Do threshold selection **leave-one-fold-out** (calibrate on the train folds, score the held-out fold),
and when comparing a per-command method to a global one, sweep each method's own knob to a common FAR
target and read every FRR at the **realized held-out FAR** — never compare FRRs at different FAR.
On real TORGO this exposed per-command calibration as a **non-improvement**: train-fit to FAR≤5%, its
held-out FAR ballooned to 24–34% (accept-all fallback commands), so its lower FRR was just a looser
operating point, not a gain.
- **Runtime clause:** the shipped `ThresholdCalibrator.calibrate(corpus)` has this same in-sample
  property — it calibrates on the user's own enrollment set, so its FAR budget will be **optimistic in
  the field**. Treat its budget as a training-set bound, not a deployment guarantee.
- **Why:** `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md`,
  `docs/testing/2026-07-06_frr-far-torgo.md` (held-out vs in-sample columns).
- **Gate:** advisory; `core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoEval.kt` `heldOut`/`fitGlobal`/`fitPerCmd` are the reference
  implementation; `TorgoEvalHeldOutTest` pins the no-self-calibration + accept-all-fallback properties.

### EVAL-003 — Pre-register one accuracy hypothesis; report the rest as a not-banked family
When testing accuracy levers (feature front-ends, matchers, rejection rules), **pre-register a single
a-priori hypothesis** and adjudicate it with a paired test vs the baseline at **matched FAR** (McNemar on
the per-utterance outcomes). Any other variants you try are an **exploratory family**: report them in
full (losing cells included) with a "**NOT banked**" label, and never adopt a lever *mined* from that
family without its own pre-registered, FAR-matched confirmation on **fresh** data. Reporting the best of
N variants is selection-on-test — the same best-of-grid optimism EVAL-002 and the D3 caveat exist to
prevent, one meta-level up. A hypothesis that *loses* is a valid, valuable result (it stops you building
the wrong thing), and the process is validated by producing a **trustworthy negative**, not by winning.
On real TORGO this refuted **common-mode rejection normalization** (H1): significant *regression* on
control (χ²=39.7, p<0.001), directionally worse on dysarthric — while a `margin` variant that looked
better in the family table rode a higher FAR on control and was therefore *not* banked.
- **Why:** `docs/errors/2026-07/2026-07-06_common-mode-rejection-refuted.md`,
  `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`.
- **Gate:** advisory; `core/eval/src/main/kotlin/com/speechangel/core/eval/RejectionEval.kt` (`mcNemar` +
  the "NOT banked" family renderer) is the reference implementation; `RejectionScoreTest` pins the
  scorer/McNemar mechanics.

### EVAL-004 — Reproduce the whole pipeline before trusting deltas; decompose confounded comparisons
Two rules for any **off-device / cross-implementation** accuracy comparison:
1. **Fidelity gate first.** When you re-implement an in-repo metric elsewhere (e.g. a Python harness vs
   the JVM `TorgoEval`), reproduce the **committed number within a few points before trusting any delta**,
   and reproduce the **whole** pipeline — not just the named stage. Silence handling is the trap: the
   committed pipeline **VAD-trims** (`EnergyVad.trim`) before MFCC; a harness that runs MFCC on the full
   wav scored **37.5% vs the committed 68.8%** with *inverted* separability (AUC<0.5). **AUC<0.5 is a
   trimming/endpointing smell, not a weak-feature result.** DCT-scaling/delta fixes changed distance
   *scale* but not ranking; only replicating the VAD trim reproduced the report to the decimal.
2. **Change one variable per comparison; close the 2×2 before assigning cause.** A win that moves **both**
   representation *and* matcher is confounded. The SSL spike's naive headline (MFCC-**DTW** vs WavLM-
   **pooled-cosine**) mis-assigned the cause to the front-end; the representation×matcher **2×2** showed
   the lever is the **embedding+cosine** interaction (WavLM-under-DTW *ties* MFCC; MFCC-under-pooling
   *drops* to 39.3%) — a QbE-embedding finding, not a front-end swap. Run the missing factorial corner
   before writing the causal claim.
- **Why:** `docs/errors/2026-07/2026-07-06_ssl-spike-fidelity-and-confound.md`.
- **Gate:** advisory; `scripts/eval/ssl_frontend_spike/harness.py` (`energy_vad_trim` + the decimal
  fidelity reproduction) and `matcher2x2.py` (the decomposition) are the reference implementations.
