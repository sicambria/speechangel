# Plan: recognizer eval and calibration

- **Date:** 2026-06-28
- **Phase:** 0 (with Phase 2 threshold tuning)
- **Roadmap item:** Phase 0 "Measure FRR/FAR", Phase 0 "Feature front-end bake-off", Phase 0
  `core:dsp` ΔΔ gap, Phase 2 "FAR-budget threshold tuning per command"
- **Status:** active (harness A-deliverables — `core:eval` — landed 2026-06-28; Phase-2 per-command threshold *app-persistence* into `ListeningService` landed 2026-07-05; real-corpus FRR/FAR numbers remain Bucket B)
- **Worktree:** n/a (single-session, on `main`)
- **Plan quality:** 95/100 — independently confirmed over two review rounds (66 → 93 → 95)

## Goal

Stand up the measurement and tuning machinery the project's honesty rule demands: a pure-Kotlin,
JVM-testable evaluation harness that computes **FRR + FAR** (as counts over a *named, timed* corpus,
overall / per-command / per `VoiceCondition`) for enrolled templates against a labeled utterance
corpus, a per-command **threshold calibrator** against an explicit FAR budget, and a **feature
front-end bake-off** (static MFCC vs +Δ vs +Δ+ΔΔ). The `core:dsp` ΔΔ gap is **already closed** (see
Steps); this plan consumes it.

## Context & Constraints

- **Accuracy honesty (non-negotiable):** results are **FRR + FAR**, reported as counts with the
  negative-audio duration that produced them (a rate like "/hour" is only quoted with its duration and
  a caveat on resolvability) — never a bare percentage. Enforced by
  `scripts/audits/verify-plan-workflow-guardrails.mjs`.
- **Corpus must be RAW audio, not pre-extracted templates.** `TemplateMatcher.match`
  (`core/matching/src/main/kotlin/com/speechangel/core/matching/TemplateMatcher.kt`) skips any template
  whose `coefficientCount != query.coefficientCount`. If the corpus stored 13-dim `Template`s, a +Δ+ΔΔ
  (39-dim) query would match nothing → 100% FRR. So the corpus holds raw `AudioSamples`; each
  `FeatureFrontEnd` under test extracts *both* the enrolled templates and the query with the *same*
  config, guaranteeing equal widths.
- **Real `EnergyVad` needs surrounding silence.** `Recognizer.recognize` runs `vad.trim` first;
  `EnergyVad` thresholds at `percentile(energy,0.10) * config.energyRatioOverNoise` (the ratio is an
  `EnergyVadConfig` field, default 3 — `core/dsp/src/main/kotlin/com/speechangel/core/dsp/Vad.kt:30`). A bare steady tone has
  uniform RMS → nothing clears the gate → empty → SILENCE for every positive (confirmed empirically by
  review). Synthetic utterances must therefore be **silence-padded bursts** with **time-varying**
  content (frequency sweeps / multi-tone with temporal structure) so VAD passes *and* Δ/ΔΔ carry
  information.
- **On-device core stays language-independent:** measure/tune only the existing template/DTW matcher;
  no STT/phoneme model. The matcher already accepts `perCommandThresholds` — calibration produces that
  map; no matcher API change.
- **Real audio is the external blocker (Bucket B):** measured numbers on real, incl. dysarthric, voices
  need a corpus we cannot synthesize. The harness, a deterministic synthetic corpus, and the report are
  the autonomous (Bucket A) deliverables; synthetic numbers carry a hard "SYNTHETIC — not the real
  measurement" banner and are never presented as the Phase-0 exit measurement.
- **Pure Kotlin/JVM** (`speechangel.kotlin.library`) so it runs in the fast `:core:*` test gate, no
  device. `MfccConfig` gaining `DeltaOrder` is a public-API change to `core:dsp` (no external callers
  set the old `includeDeltas`, confirmed).

## Approach

Add a `core:eval` module depending on `core:model` + `core:dsp` (as `api`, since `FeatureFrontEnd`
exposes `MfccConfig`) + `core:matching` + `core:enrollment`. It owns: raw-audio corpus types, a
`FeatureFrontEnd` abstraction (a named `MfccConfig`), an `Evaluator` (enrolls templates and scores
queries through one front-end), a `ThresholdCalibrator`, the bake-off runner, a deterministic synthetic
corpus, and a markdown report renderer.

Rejected: storing `Template`s in the corpus (width-locks the bake-off — the core defect); steady-tone
synthetics (fail VAD + carry no delta info); asserting "more features win" as a test (that ranking is
the experiment's *output*, not an invariant); editing `:app`'s `ListeningService` as a core deliverable
(pulls in the `:app`/`:data` build — Bucket B).

## Steps

1. **`core:dsp` ΔΔ — DONE.** `MfccConfig.includeDeltas: Boolean` was replaced by
   `deltaOrder: DeltaOrder { NONE, DELTA, DELTA_DELTA }` (default NONE = unchanged behavior);
   `withDeltas` now concatenates static | Δ | ΔΔ (widths 13/26/39), invariant preserved. Tests added in
   `core/dsp/src/test/kotlin/com/speechangel/core/dsp/MfccExtractorTest.kt` (widths; static block
   preserved verbatim; ΔΔ of a constant-velocity ramp ≈ 0). `:core:dsp:test` green. (Public-API change
   to `MfccConfig` — noted.)
2. **Module skeleton.** `core/eval/build.gradle.kts` (`alias(libs.plugins.speechangel.kotlin.library)`;
   `api(projects.core.model)`, `api(projects.core.dsp)`, `implementation(projects.core.matching)`,
   `implementation(projects.core.enrollment)`); `include(":core:eval")` in `settings.gradle.kts`;
   `kover(project(":core:eval"))` in root `build.gradle.kts`. Test deps (junit/truth/coroutines-test)
   come from the convention plugin — do not re-declare.
3. **Corpus model (raw audio).** `core/eval/src/main/kotlin/com/speechangel/core/eval/Corpus.kt`:
   `EnrollmentSample(commandId, audio, condition)`; `LabeledUtterance(audio, truth: CommandId?,
   condition, source)` (`truth == null` ⇒ negative/OOV); `Corpus(enrollment: List<EnrollmentSample>,
   utterances: List<LabeledUtterance>)`. No `Template`s stored.
4. **FeatureFrontEnd + Evaluator.** `FeatureFrontEnd(name, config: MfccConfig)`. `Evaluator` enrolls
   templates from `corpus.enrollment` via `Enroller` *under the front-end's config*, builds a
   `Recognizer` with the *same* config, runs each utterance, and tallies `EvalReport`:
   positives/negatives, **FRR** = (rejected ∪ substituted positives)/positives (substitutions named via
   a confusion map — convention stated), **false-accept count** + negative-audio seconds (→ an
   *annotated* FAR/hour), per-command FRR, per-`VoiceCondition` FRR.
5. **Calibrator.** `ThresholdCalibrator.kt`. **Budget (stated concretely):** aggregate target of
   **≤ 1 false-accept per 1800 s (30 min) of negative audio** — this is the synthetic operating target;
   the real Phase-0 goal is ≤ 0.5 FA/hr, which is *not* resolvable from short synthetic negatives.
   **Allotment:** `budgetFA = max(1, round(negativeSeconds / 1800))`. **Split policy:** equal —
   each of N commands gets `perCmd = budgetFA / N` (a real number; fractional allotments are handled by
   rounding the *cumulative* allowance so the total never exceeds `budgetFA`). **Per-command threshold:**
   set `threshold[c]` just below the `(perCmd + 1)`-th smallest distance among negatives whose argmin
   command is `c` (or the max observed distance if there are fewer such negatives), bounding `c`'s
   false-accepts to its allotment. Because a higher per-command threshold *monotonically* lowers that
   command's FRR and raises its false-accepts, "highest threshold within budget" already minimizes FRR
   (so the sweep is a search, not a full scan). Return `Map<CommandId, Float>` + the achieved
   FRR/FA-count. The report derives the **minimum negative-audio duration** quantitatively (the duration
   at which the budget corresponds to ≥ 1 expected false-accept).
6. **Bake-off.** `FrontEndBakeoff.kt`: run the Evaluator for {static, +Δ, +Δ+ΔΔ} over the same raw
   corpus (each extracts its own templates+queries) and **compute** a comparison table (FRR + FA-count
   per front-end). It computes the table; it does not assert which front-end wins.
7. **Synthetic corpus + report.** `SyntheticCorpus.kt`: deterministic, **silence-padded, time-varying**
   command-like signals (distinct sweeps/multi-tone envelopes per command) + garbage negatives — so VAD
   passes and deltas carry signal. `EvalReport.render()` → markdown with the SYNTHETIC banner. A
   committed `docs/testing/frr-far-report-template.md` documents the corpus format + how to drop in real
   recordings. (Report-writing tests write to the module `build/` dir, not the repo tree.)
8. **Tests.** `core/eval/src/test/...`: evaluator math on a hand-built tiny corpus (known inputs → known
   FRR/FA-count); calibrator returns a map that lowers FA-count vs the default on the synthetic set; the
   bake-off *produces a populated table for all three front-ends* (not a winner assertion); a sanity test
   that the synthetic positives survive VAD (guards against the steady-tone trap); and an assertion that
   every synthetic enrollment sample returns `EnrollmentResult.Success` under each front-end config (a
   500 ms burst gives 48 frames ≥ the `minSpeechFrames = 8` bar) — so a corpus tweak can't silently turn
   enrollment failure into apparent matcher FRR. PLP is **deliberately descoped** (MFCC variants only).
9. **App wiring (Bucket B / documentation).** Document the wiring point: `ListeningService` currently
   calls `recognizer.recognize(audio, templates)` with no thresholds; consuming a persisted
   `perCommandThresholds` map from calibration is an `:app`/`:data` change verified with the full
   toolchain, not the `:core:*` gate. The testable deliverable here is the calibrator's
   `Map<CommandId, Float>` exercised in a `:core:eval` test.

## Definition of Done

- `core:eval` builds; `:core:eval:test` green; the four `:core:*` tests stay green; guardrail bundle
  green. The `:core:*:test` set is the honest autonomous gate for this pure-Kotlin module; whole-project
  `make verify` is green on the *current* tree (this session) and is re-run after implementation.
- The harness computes **FRR** and **false-accept counts with negative-audio duration** (overall,
  per-command, per `VoiceCondition`) against a named corpus; the report template documents the format.
- The calibrator returns per-command thresholds and reports achieved FRR + FA-count at an explicit,
  documented **aggregate FAR budget**; it states the min negative-audio duration for meaningfulness.
- The bake-off emits a populated FRR + FA-count comparison across static / +Δ / +Δ+ΔΔ.
- `core:dsp` ΔΔ supports width 13/26/39 with the concatenation invariant tested (done).
- **Honesty gate:** the only autonomous corpus is synthetic; its output carries a hard SYNTHETIC banner.
  The Phase-0 exit (real-voice FRR/FAR beating the FAR budget) remains **blocked on a real labeled
  corpus incl. dysarthric voices** — recorded as blocked; no real numbers fabricated.

## Risks & Mitigations

- **Risk: the harness runs green while measuring nothing** (the top review risk — steady tones / width
  mismatch). Mitigation: raw-audio corpus + same-front-end extraction; silence-padded time-varying
  synthetics; an explicit "positives survive VAD" test.
- **Risk: synthetic numbers mistaken for real measurement.** Mitigation: hard banner + DoD honesty gate
  + ROADMAP item stays `[ ]` until real recordings exist.
- **Risk: FAR budget misinterpreted (per-command vs aggregate; unmeasurable sub-1/hr).** Mitigation:
  aggregate budget defined + split policy; FAR reported as count + duration; min-duration stated.
- **Risk: leaked-type compile error** from `FeatureFrontEnd` exposing `MfccConfig`. Mitigation:
  `core:dsp` declared as `api` in `core:eval`.
- **Rollback:** `core:eval` is a new, leaf module — nothing in the runtime pipeline depends on it, so
  dropping `include(":core:eval")` reverts cleanly. The one non-additive change is `MfccConfig`'s
  `includeDeltas: Boolean` → `deltaOrder: DeltaOrder` (default `NONE` preserves prior behavior, no
  external callers set the old field — confirmed); to back it out, restore the boolean and the
  `withDeltas` concatenation. The per-command threshold map is consumed only if the app opts in.

## Test & Verification

- Autonomous (this host): `:core:dsp:test` (ΔΔ — done), `:core:eval:test` (evaluator/calibrator/bake-off
  + VAD-survival), the full `:core:*` test set, guardrail bundle. Whole-project `make verify` is green on
  the current tree this session and re-run after this module lands.
- Blocked (needs the world): real FRR/FAR on recorded, incl. dysarthric, voices in quiet + home noise —
  a labeled corpus dropped into the documented format and the harness re-run. This plan delivers
  everything up to that point.
