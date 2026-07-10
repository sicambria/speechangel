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
- **Gate:** **hard (substance)** — `scripts/audits/verify-sota-measurement.mjs` **check 4 (Banked-verdict
  gate)** blocks any testing/experiment doc that reports an adjudicated result (a McNemar test or a
  rel-reduction delta) without an explicit `banked` / `NOT banked` verdict — the rule's required output
  artifact, not merely the topic word "exploratory". (Check 1 additionally enforces the EVAL-003 *citation*.)
  Reference impl: `core/eval/src/main/kotlin/com/speechangel/core/eval/RejectionEval.kt` (`mcNemar` + the
  "NOT banked" family renderer); `RejectionScoreTest` pins the scorer/McNemar mechanics. **Promoted
  2026-07-09** (SOTA domain 15 — guardrail coverage; see the promotion ladder below).

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
- **Gate:** **hard (substance)** — `scripts/audits/verify-sota-measurement.mjs` **check 3
  (Fidelity-reproduction gate)** blocks any delta-vs-baseline claim doc whose fidelity statement lacks a
  reproduced baseline **number** (within tolerance) — a fidelity claim without a number is unverifiable.
  Reference impls: `scripts/eval/ssl_frontend_spike/harness.py` (`energy_vad_trim` + the decimal fidelity
  reproduction) and `matcher2x2.py` (the 2×2 decomposition). **Promoted 2026-07-09** (SOTA domain 15 —
  guardrail coverage; see the promotion ladder below).

---

### EVAL guardrail promotion ladder (SOTA domain 15)

**Domain 15 metric** (`docs/product/2026-07-08_sota-domain-bands.md`): the count of EVAL-001..005 rules with
a **hard substance gate**. **Promotion criterion (fixed before looking at the band):** a rule counts iff a
blocking verifier check enforces a **rule-specific substance artifact** — a required concrete token or number
that goes *beyond* keyword citation — and its `**Gate:**` line here says `hard` naming that check. A
citation-only check (keyword presence) does not count: the verifier's own comment notes the citation regex
cannot distinguish "we used held-out" from "no held-out". `SotaScorecard.guardrailCoverage()` counts the
`**Gate:** hard` EVAL lines (`-Dsota.rules=<path to this file>`); band ladder 600→0, 700→1, **800→2**,
900→3, 950→4, 1000→5.

Applying that criterion to all five rules — **the count is simply how many substance gates have been
BUILT**, not an argument that the others are ungateable:

| Rule | Substance artifact the rule needs | Substance gate built? | Gate | Counts? |
|------|-----------------------------------|:---------------------:|------|:-------:|
| EVAL-001 | no absolute FRR at a cross-distribution threshold | none (no check) | advisory | no |
| EVAL-002 | threshold chosen on **disjoint** data | not yet — future (E15-06) | advisory | no |
| **EVAL-003** | an explicit **banked / NOT-banked verdict** on each result | **yes → check 4** | **hard** | **yes** |
| **EVAL-004** | a **reproduced baseline number** on each delta claim | **yes → check 3** | **hard** | **yes** |
| EVAL-005 | **≥2 speakers agree** in direction | not yet — future (E15-07) | advisory | no |

**Count: 2/5 → band 800** = the two substance gates **built and verified to bite this session** (check 4:
McNemar-without-verdict blocked; check 3: delta-without-number blocked — both while check 1 stayed silent,
so they gate substance, not citation). This is **not** reverse-engineered: an earlier draft tried to count
the pre-existing *citation* checks and hit an internal contradiction (check 1 tests EVAL-002∧003∧005 as one
atomic condition, so no consistent rule yields exactly 2 — see the incident doc). The honest claim is narrow
and provable: *two substance gates exist and block today.* EVAL-002/005 are **gateable** (e.g. require a
leave-one-fold-out token / a per-speaker-breakdown table) — that is real future work (E15-06/07), not a
reason they "can't" count; EVAL-001 has no check. See `docs/plans/2026-07/sota-800-push.md` Domain 15 and
`docs/errors/2026-07/` for the path to 900+ and the wrong-turn write-up.

### EVAL-005 — Operating-point metrics at a curve extreme are high-variance; replicate before headlining
A metric read at a **single threshold at the extreme of a detection/FA curve** — detection at ~0 FA/hr, or
the FA/hr required to reach a high target detection — is pinned by the **1–2 hardest positives** and the
**single nearest background window**, so it is **high-variance, not low-variance** (the intuition that "a
tail metric averages over many events" is wrong — the *tail* is exactly where one sample moves it). A
one-speaker read, even a significant one, is **not** sufficient to headline such a point: require **≥2
speakers/folds that agree in direction**, and prefer a **curve-area / partial-AUC** summary as the primary
number, reporting extreme single-threshold points only *with* their replication status. Non-significant at
small n means **underpowered / not demonstrated**, never "no effect." This caught a phantom win: the CP-2
in-regime spike's F01 "≈5× tail compression" (FA/hr for 95% det 24→5) looked robust on one speaker but the
control (FC01) showed a **tail regression** (3.0→6.0; det@5FA/hr 100%→70.6%) — retracted before banking;
the ~0-FA/hr lift was likewise underpowered (F01 b=1/c=3, p=0.62).
- **Why:** `docs/errors/2026-07/2026-07-06_cp2-tail-metric-knife-edge.md`.
- **Gate:** advisory; `scripts/eval/ssl_frontend_spike/in_regime.py` (extreme operating points) and
  `inregime_paired.py` (paired McNemar + exact-binomial that quantified the fragility) are the references.

### EVAL-006 — Same-demographic control replication ≠ generalization; a personalization lever needs cross-demographic held-out before banking
A per-user/personalization lever that helps on a target sub-population **and** on a *control* drawn from the
**same demographic and same corpus** has **not** been shown to generalize — that second population gives
**false confidence**, because it shares the very axes (gender, channel, recording protocol, speaker pool)
that the lever may be exploiting. Before banking such a lever, confirm it on a **cross-demographic held-out**
population (here: cross-gender), adjudicated by a paired test at matched FAR. Non-transfer there refutes the
generalization claim even when the within-demographic result was significant. This caught the campaign's
lead lever: **G1** per-user within-word whitening was a Round-2 directional positive on n=3 **female** TORGO
(in-vocab D2 −10.6pp, p=0.004) that *also* replicated on female **control** (−8.7pp) — read at the time as a
confidence-boosting 2nd population. On real held-out **male** dysarthric speakers (M01–M05) it was **null**
(pooled −1.4pp, p=0.63; 1 up / 1 down / 3 flat). Had the female result been banked it would have been wrong;
near-identical within-word scatter gave opposite signs across genders, so no gating variable made it
deployable.
- **Why:** `docs/errors/2026-07/2026-07-10_g1-female-control-false-confidence.md`.
- **Gate:** advisory; `scripts/eval/ssl_frontend_spike/p7_male_g1_confirm.py` (frozen-config cross-gender
  held-out replication + paired McNemar) is the reference. Standing bar for dysarthric levers: **F↔M
  cross-gender held-out** before any bank.

### WORKFLOW-001 — Fix the measurement criterion before you look at the target
When banking any **count / coverage / score** metric (e.g. SOTA domain 15 guardrail coverage), state the
criterion **before** computing the value, apply it **uniformly to every item**, and report where it lands —
even if that is short of the target band. A value that cannot be **derived from its stated criterion without
knowing the desired result** is not a measurement; it is selection-on-target — EVAL-003's anti-pattern one
meta-level up. For coverage specifically: an item counts only if a blocking check enforces a **substance
artifact** proven to **bite on a fixture**, never a keyword/citation check and never a bare label.
- **Why:** `docs/errors/2026-07/2026-07-09_d15-guardrail-count-reverse-engineered-to-band.md` (the D15
  count was first set to 2 to clear band 800, then justified — caught by advisor review before commit).
- **Gate:** advisory; `scripts/audits/verify-sota-measurement.mjs` checks 3/4 (the substance gates) and
  `core/eval/src/main/kotlin/com/speechangel/core/eval/SotaScorecard.kt` (`countHardGatedEvalRules`) are the
  reference implementations.

### CONSTRAINT-001 — Audit a constraint's validity before it decides a feasibility verdict
Before reporting a target as "unreachable" because of a constraint, **check the constraint is real, not
artificial.** For each constraint ask: *is it meaningful and valid given an average sub-300 EUR smartphone
in 2026 (≈4–8 GB RAM, NPU/NNAPI)?* If it has **no real argument** and **no felt user downside**, relax it
(with the device/UX argument stated) rather than concluding impossibility. Classify: **REAL** = privacy /
on-device, Play-policy determinism, a product value (speaker-dependence, language-independence), or a
*measured physical property* (severe-dysarthric within-word variability, AUC~0.70). **ARTIFICIAL** = a
round-number size cap (the old **≤2 MB**), **1-shot** where few-shot has no UX cost, **no-GPU** where NNAPI
exists. Never relax a REAL constraint (breaks the admissibility filter / mission); always re-examine an
artificial one.
- **Why:** the ≤2 MB budget held the composite at `<600` for a whole feasibility study as if immovable;
  it had no device rationale. Relaxing it (SSL encoder) + few-shot enrollment lifted the typical-population
  composite from `<600` toward 800. `docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md` (§ constraint audit).
- **Gate:** advisory (judgment rule); pairs with the honesty contract — a *justified* relaxation with a
  stated argument is not goalpost-moving, but silently dropping a REAL constraint to pass a target is.
