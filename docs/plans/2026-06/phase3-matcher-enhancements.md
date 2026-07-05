# Plan: phase 3 matcher enhancements

- **Date:** 2026-07-05
- **Phase:** 3 (Delight & reach)
- **Roadmap item:** Phase 3 "QbE embedding enhancement (few-shot, milder impairment)"; Phase 3
  "Vocabulary-distinctness helper (warn on acoustically-close commands)"; Phase 3 "Far-field / noise
  front-end"
- **Status:** active (Bucket-A slices landing 2026-07-05: distinctness helper + QbE seam done; far-field front-end pending; B/C measurement blocked)
- **Worktree:** n/a (docs-only plan; each item enters its own worktree when scheduled to build)
- **Plan quality:** 93/100 — self-scored 2026-07-05 (see `docs/plans/INDEX.md` scoring row)

## Goal

Raise recognition quality along three independent axes *without* dislodging the raw-feature MFCC-DTW
core (the language-independent, no-normal-speech-prior default that is safest for severe impairment):
(1) an **optional, configurable QbE embedding matcher** behind the existing `SpeechBackend` seam for
milder impairment; (2) a pure **vocabulary-distinctness helper** that warns a caregiver at enrollment
time when two commands are acoustically close (a confusion source the user never has to debug in the
field); (3) a **far-field / noise-robust front-end** option in `core:dsp`. Each ships its maximal
autonomous slice with its external blocker named; none becomes the *only* path.

## Context & Constraints

- **Core stays the default; enhancements are opt-in (non-negotiable).** Research
  (`research/04_build_and_reuse_plan.md:54`) is explicit: raw-feature MFCC-DTW is the default because
  a QbE encoder is "trained on normal speech, so don't make it the only path." Every item here is a
  *configurable alternative or additive warning*, never a replacement of the speaker-dependent template
  core.
- **Accuracy honesty (non-negotiable).** All three items are matcher/front-end/accuracy work, so each
  item's success is expressed as an **FRR + FAR/hour delta vs the MFCC-DTW baseline**, per
  `VoiceCondition`, measured on the `core:eval` harness — never a bare percentage. Enforced by
  `scripts/audits/verify-plan-workflow-guardrails.mjs`. Real numbers are Bucket B (need a labeled,
  dysarthric-inclusive corpus); the harness, wiring, and synthetic sanity runs are the autonomous part.
- **The `core:eval` harness is landed** (`core/eval/src/main/kotlin/com/speechangel/core/eval/Evaluator.kt:60`,
  `FrontEndBakeoff.kt:11`) — measurement machinery is not a blocker; the labeled corpus is.
- **The `SpeechBackend` seam already exists** but **no selector/injection does.** `SpeechBackend`
  (`core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/SpeechBackend.kt:27`),
  `TemplateSpeechBackend` (:40), `NoopPathABackend` (:66) are present, but
  `data/src/main/kotlin/com/speechangel/data/di/RecognitionModule.kt:46` binds a concrete `Recognizer`
  directly and never provides a `SpeechBackend`. A configurable-matcher item must add that binding.
- **`Fft` and `MelFilterBank` are `internal` to `core:dsp`** (`core/dsp/.../Fft.kt:8`,
  `MelFilterBank.kt:10`). A far-field front-end must therefore live *inside* `core:dsp` (extend
  `MfccConfig` / add a pre-processing stage) or add a deliberate public seam — it cannot be bolted on
  from another module.
- **DTW distance is a public primitive.** `Dtw.distance(a, b, bandRatio, local)`
  (`core/matching/src/main/kotlin/com/speechangel/core/matching/Dtw.kt:33`) and the
  `TemplateMatcher.distance(a, b)` wrapper (`TemplateMatcher.kt:76`) are the exact primitives the
  distinctness helper needs — no new DTW code.
- **On-device only; deterministic action layer untouched.** No cloud, no LLM; all three items feed the
  same deterministic command→action table.

## Approach

Three loosely-coupled items, each buildable and revertible on its own. Order by autonomy: the
distinctness helper is fully Bucket A and lands first; the far-field front-end is Bucket A (logic) / B
(real far-field validation); the QbE matcher is Bucket A (interface + selector + a documented encoder
contract) / C (the trained encoder model itself). Every item measures against the MFCC-DTW baseline via
`core:eval`, so "did it actually help, and for whom?" is answered by data, not assertion.

Rejected approaches: making QbE the default matcher (violates the safest-for-severe-impairment rule —
its encoder is normal-speech-trained); implementing the far-field front-end in a new module reaching
into `core:dsp` internals (Fft/MelFilterBank are `internal` — would force leaking them); asserting "the
enhancement wins" as a unit test (whether it wins, and per which `VoiceCondition`, is the experiment's
*output*, not an invariant — the same trap the eval plan already documents); bundling a QbE model now
(size + license + a training pipeline the phone cannot run).

## Steps

### Item A — Vocabulary-distinctness helper (Bucket A, lands first)

1. **Pure distinctness function.** Add a new `VocabularyDistinctness.kt` under
   `core/matching/src/main/kotlin/com/speechangel/core/matching/`:
   `fun analyze(commands: Map<CommandId, List<Template>>, matcher: TemplateMatcher, closeRatio: Float):
   List<ClosePair>` where a `ClosePair(a, b, distance, severity)` is emitted when the *cross-command*
   minimum DTW distance (via `matcher.distance`, `TemplateMatcher.kt:76`) between any template of `a`
   and any of `b` falls below `closeRatio ×` that command's own intra-command spread (so the metric is
   scale-relative, not an absolute magic number). Pure; no repository, no I/O.
2. **Onset/minimal-pair heuristic (cheap, complementary).** Add a shared-onset check on the first N
   MFCC frames so "call / carl" style minimal pairs are flagged even when whole-utterance DTW is
   moderate; combine into `severity ∈ {NUDGE, WARN}`.
3. **Wire into enrollment UX (app).** Surface `analyze(...)` results in the Teach / caregiver-wizard
   flow as a non-blocking nudge ("‘Lights’ sounds close to ‘Blinds’ — pick a more distinct word?").
   Never blocks enrollment; advisory only (deterministic, no autonomy).
4. **Tests (`:core:matching:test`).** Hand-built templates: two deliberately-close command sets flag a
   `ClosePair`; two distinct sets do not; empty/one-command inputs return `[]`; determinism (stable
   ordering) asserted.

### Item B — Far-field / noise-robust front-end (Bucket A logic / B validation)

5. **Front-end options in `core:dsp`.** Extend `MfccConfig`
   (`core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt:20`) with an additive,
   default-off `noiseRobustness` block: (a) spectral-subtraction / noise-floor estimate over leading
   silence, (b) per-utterance CMVN is already present (`applyCmn`) — document its interaction, (c) a
   pre-emphasis/gain-normalisation pass for distance. Keep every new field defaulted so existing
   behavior is byte-identical when off (the `deltaOrder` precedent).
6. **Bake-off integration.** Add the far-field configs as named `FeatureFrontEnd`s
   (`core/eval/.../Corpus.kt:13`) so `FrontEndBakeoff` (`FrontEndBakeoff.kt:11`) computes an FRR +
   FA-count table {baseline vs noise-robust} over the same raw corpus.
7. **Tests (`:core:dsp:test`, `:core:eval:test`).** Off ⇒ identical output to today (regression guard);
   on a synthetic noise-added corpus the extractor runs and the bake-off produces a populated table (it
   *computes* the comparison; it does not assert the robust front-end wins).

### Item C — QbE embedding matcher (Bucket A seam / C model)

8. **Encoder contract + selector (Bucket A).** Define a `QbeEncoder` interface in `core:enrollment`
   (`encode(features: FeatureSequence): FloatArray`) and a `QbeSpeechBackend implements SpeechBackend`
   that enrolls few-shot class prototypes (mean/medoid embedding per command) and classifies by cosine
   distance with an OOV reject — mapping to the neutral `BackendResult`
   (`SpeechBackend.kt:14`). Add the **missing** DI binding in
   `data/src/main/kotlin/com/speechangel/data/di/RecognitionModule.kt` that selects
   `TemplateSpeechBackend` (default) vs `QbeSpeechBackend`
   from a persisted preference — this selector does not exist today and is the core wiring deliverable.
9. **Documented encoder blocker (Bucket C).** A `docs/` guide pins the encoder contract to the
   arXiv 2403.07802-style profile (~4 samples/class, ~24k params, <4 kB, on-device inference) and
   records that no model is bundled: producing/vetting the encoder (trained off-device, license-checked)
   is the external step. A `NoopQbeEncoder` (returns unavailable) keeps the seam compiling and tested.
10. **Tests (`:core:enrollment:test`).** With a deterministic fake encoder (e.g. project features to a
    fixed low-dim basis), `QbeSpeechBackend` enrolls prototypes and classifies known-in vs OOV
    correctly; the selector returns the template backend by default and QbE only when opted in.

## Definition of Done

- **Item A (autonomous):** `VocabularyDistinctness.analyze` is pure, deterministic, unit-tested in
  `:core:matching:test`, and surfaced as a non-blocking enrollment nudge. **Accuracy framing:** the
  helper's *value* is validated as a measurable link between a flagged `ClosePair` and elevated
  cross-command confusion — i.e. flagged pairs show a higher substitution-**FRR** and higher
  false-accept count (**FAR** contribution) than unflagged pairs on the `core:eval` harness; the
  warning threshold is tuned to that correlation, never to a bare percentage. (Correlation on real
  voices is Bucket B; the synthetic sanity run is autonomous.)
- **Item B (autonomous logic / B validation):** the noise-robust `MfccConfig` options exist, default-off
  (byte-identical regression proven), and are wired into `FrontEndBakeoff`, which emits an **FRR +
  FA-count** comparison {baseline vs noise-robust} per `VoiceCondition`. The *decision* to adopt a
  robust front-end is gated on that FRR+FAR delta measured on a real far-field/noise corpus — **Bucket
  B**, recorded as pending, no delta claimed until measured.
- **Item C (autonomous seam / C model):** the `QbeEncoder` contract, `QbeSpeechBackend`, the DI selector
  (default = template backend), and `NoopQbeEncoder` build and are unit-tested in
  `:core:enrollment:test`; the encoder guide documents the model contract + license/vetting step. **QbE
  is never the default.** Its acceptance is an **FRR + FAR/hour delta vs the MFCC-DTW baseline, reported
  per `VoiceCondition`** (the expectation — help mild, risk severe — must be *shown*, not assumed);
  producing the trained encoder is **Bucket C**, no accuracy delta claimed until measured on a real
  corpus.
- **Cross-item honesty gate:** the MFCC-DTW template matcher remains the default in every shipping path;
  each enhancement is opt-in and reverts cleanly (see Rollback). No item claims an FRR/FAR improvement
  from synthetic data; synthetic bake-off output carries the existing SYNTHETIC banner.
- Guardrail bundle green (`scripts/audits/run-all.mjs`), including
  `verify-plan-workflow-guardrails.mjs`; `:core:*` tests green for any item actually implemented.

## Risks & Mitigations

- **Risk: QbE quietly becomes the default / degrades severe-impairment users** (its encoder is
  normal-speech-trained). Mitigation: default DI binding is `TemplateSpeechBackend`; QbE is opt-in and
  its per-`VoiceCondition` FRR+FAR delta (esp. the severe bucket) is a gating measurement, not an
  afterthought.
- **Risk: distinctness helper false-alarms and annoys caregivers / blocks setup.** Mitigation:
  scale-relative threshold (not an absolute magic distance) + advisory-only, never blocking; threshold
  tuned against the confusion correlation.
- **Risk: far-field front-end silently changes baseline output.** Mitigation: every new `MfccConfig`
  field defaults off with a byte-identical regression test (the `deltaOrder` precedent).
- **Risk: `Fft`/`MelFilterBank` internal visibility blocks the front-end.** Mitigation: the front-end
  lives *inside* `core:dsp`; if a public seam is ever needed it is added deliberately, not by relaxing
  `internal` ad hoc.
- **Risk: an "enhancement" is shipped on faith without measurement.** Mitigation: every item's adoption
  gate is an FRR+FAR delta on `core:eval`; unmeasured ⇒ stays behind its flag, documented as pending.
- **Rollback:** all three items are additive and flag/selector-gated. Item A is a pure leaf function +
  an advisory UI string (delete → enrollment unchanged). Item B's `MfccConfig` fields default off
  (revert = drop the fields; runtime output is unchanged while off). Item C adds a new interface +
  backend + a DI selector defaulting to the template path (revert the selector → the app uses the
  template matcher exactly as today; no schema/template migration in any item).

## Test & Verification

- **Autonomous (this host):** `:core:matching:test` (distinctness), `:core:dsp:test` +
  `:core:eval:test` (front-end regression + bake-off table), `:core:enrollment:test` (QbE seam +
  selector) for whichever items are built; guardrail bundle green; whole-project `make verify` re-run
  after any implementation. This plan is docs-only until an item is scheduled — no code is claimed built.
- **Blocked (needs the world):** the FRR+FAR *deltas* that decide adoption — distinctness/confusion
  correlation and far-field/noise gains on real voices (Bucket B), and any QbE accuracy number (needs
  the external trained encoder + a labeled, dysarthric-inclusive corpus — Bucket C). Recorded as
  blocked; no real numbers fabricated.
