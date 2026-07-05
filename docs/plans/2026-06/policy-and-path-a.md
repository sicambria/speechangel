# Plan: policy and path a

- **Date:** 2026-06-28
- **Phase:** 2
- **Roadmap item:** Phase 2 "Play Permission Declaration Form + prominent mic disclosure"; Phase 2
  "Optional Path-A intact-speech mode (Vosk grammar / sherpa-onnx KWS)"
- **Status:** done (A-deliverables implemented 2026-06-28; C-items — Play Permission Declaration Form — pending external input)
- **Worktree:** n/a (single-session, on `main`)
- **Plan quality:** 95/100 — independently confirmed over two review rounds (63 → 86 → 95)

## Goal

Cover the two Phase-2 items whose true completion lives outside an autonomous coding session — Play
policy compliance and an optional intact-speech backend — by shipping the buildable parts (an in-app
prominent mic-disclosure dialog + a licenses screen, and a **backend-neutral** `SpeechBackend`
abstraction + scaffold) and documenting the external blockers precisely.

## Context & Constraints

- **Play policy (2026):** a `microphone` always-on app needs a prominent in-app disclosure *before*
  permission prompts and a completed Permission Declaration Form in the Play Console. The form is
  account-bound (Bucket C); the in-app disclosure is Bucket A.
- **Licensing (precise):** Vosk + sherpa-onnx are **Apache-2.0**; whisper.cpp is **MIT**; **Silero VAD
  is MIT** but **Silero STT is CC-BY-NC and is on the explicit AVOID list**
  (`research/04_build_and_reuse_plan.md` §6). Ship a third-party-licenses screen.
- **Core stays language-independent + primary:** Path-A is an *optional, additive* mode for users with
  intact speech; it must never replace the speaker-dependent template core. The abstraction seam may
  live in `core:enrollment` only as an **interface** — no language-dependent backend may depend back
  into the core.
- **Interface honesty (the #1 review finding):** `RecognitionResult.Match` requires a non-null
  `templateId` and a DTW `distance`; `RejectionReason` is template-centric. A Vosk backend has neither.
  And `Recognizer.recognize(audio, templates, thresholds)` is a *pure, batch* call taking a template
  list per invocation — a Vosk backend takes a grammar/word-list and is typically streaming. So the
  abstraction must be **backend-neutral**, not the current template-centric shape.
- **Path-A is Bucket C:** a real backend pulls in a large native model + runtime; the deliverable is a
  neutral interface + a `Noop` scaffold + an integration guide.

## Approach

Two independent pieces. (1) **Disclosure + licenses:** a `MicDisclosureDialog` gated by a flag persisted
in **`:data` (DataStore)** and exposed via a ViewModel (so the "shown once" logic is plain-JUnit
testable without Compose), shown before mic permission / service start; a `LicensesScreen` listing
third-party components from a single declared source. (2) **Backend-neutral abstraction:** define a
`SpeechBackend` whose result type is fully neutral — `BackendResult(commandId: CommandId?,
confidence: Float, reason: BackendRejection?)`, where `BackendRejection` is a **new neutral enum**
(`NO_SPEECH`, `LOW_CONFIDENCE`, `BACKEND_UNAVAILABLE`) — *not* the template-centric Domain
`RejectionReason` (whose `NO_TEMPLATES`/`BELOW_CONFIDENCE` are meaningless for a Vosk grammar backend).
Each backend maps its native reasons into `BackendRejection`. DTW-specific fields (`templateId`,
`distance`) stay in a template-engine-only subtype/extension. The interface method is `fun recognize(audio): BackendResult`
with the backend configured at construction (the template adapter captures templates + thresholds →
becoming **stateful**, a deliberate change from today's pure function; a Vosk backend would capture its
grammar). A `NoopPathABackend` + an integration guide complete the scaffold; no native model is bundled.

Rejected: reusing `RecognitionResult`/`recognize(audio, templates, thresholds)` as the cross-backend
shape (forces Vosk to fabricate `templateId`/`distance` and accept an irrelevant template list — the
core defect); bundling a Vosk model now (size, license vetting, native build); writing Play-form text as
if submitted (account-bound — a checklist instead); unqualified "Silero is MIT" (STT is CC-BY-NC).

## Steps

1. **Disclosure flag in `:data`.** Add the persisted "mic disclosed" flag to the DataStore-backed
   preferences in `:data` (the module that owns `datastore-preferences`), exposed through a ViewModel —
   not persisted from the UI layer.
2. **Disclosure dialog.** `app/src/main/kotlin/com/speechangel/app/ui/policy/MicDisclosureDialog.kt`
   shown before first mic use / service start; plain-language, accessible; acknowledgement sets the flag.
3. **Licenses screen.** `app/src/main/kotlin/com/speechangel/app/ui/policy/LicensesScreen.kt` listing
   current third-party components + licenses from a single declared source (manual list now; note a
   licenses-plugin as the future source so it stays accurate). Route from settings/Home.
4. **Play checklist doc.** `docs/` note with concrete, ready-to-submit Permission Declaration answers
   (foreground-service-type rationale, prominent-disclosure pointers, data-safety entries) — a checklist
   the human submits in the Console.
5. **Backend-neutral interface.**
   `core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/SpeechBackend.kt`: `BackendResult` +
   the neutral `BackendRejection` enum + `BackendCapabilities` (needsEnrollment, languageDependent;
   streaming backends are adapted behind the one-shot `recognize` for now — no decorative flag without a
   method) + `SpeechBackend` with `recognize(audio): BackendResult`. A `TemplateSpeechBackend` adapter
   wraps the existing `Recognizer` (stateful — captures templates + thresholds at construction) and maps
   `RecognitionResult` → `BackendResult`: `Match`→`commandId`+`confidence`; `NoMatch`→ `reason` mapped
   (`SILENCE`/`EMPTY_INPUT`→`NO_SPEECH`, `BELOW_CONFIDENCE`→`LOW_CONFIDENCE`, `NO_TEMPLATES`→
   `BACKEND_UNAVAILABLE`), with `nearestCommandId`/`bestDistance` preserved only via a template-engine
   extension.
6. **Path-A placeholder + guide.** `NoopPathABackend` (capabilities = languageDependent, returns
   "unavailable") + a `docs/` integration guide: Apache-2.0 backend choice, model/license vetting,
   native wiring, the no-back-dependency-into-core rule, and that any such backend's acceptance is
   measured via the `core:eval` harness (a **pending prerequisite** — that module is created by
   `docs/plans/2026-06/recognizer-eval-and-calibration.md`) and reported as **FRR + FAR/hour**.
7. **Tests.** Plain-JUnit: disclosure-flag gating (not shown twice once acknowledged) via the ViewModel;
   the `TemplateSpeechBackend` adapter round-trips a Match/NoMatch into the neutral `BackendResult`.

## Definition of Done

- `MicDisclosureDialog` + the `:data`-persisted, ViewModel-exposed acknowledgement implemented and shown
  before mic use; `LicensesScreen` lists current licenses (Silero VAD MIT / Silero STT CC-BY-NC excluded
  / Vosk+sherpa Apache-2.0 / whisper.cpp MIT stated correctly); both build green.
- A Play Permission Declaration **checklist** doc exists with concrete answers.
- `SpeechBackend` is **backend-neutral** (`BackendResult` with the neutral `BackendRejection` enum — no
  forced `templateId`/`distance` and no template-centric `RejectionReason`); `TemplateSpeechBackend`
  adapter implements it and is unit-tested (Match + each NoMatch reason mapping); `NoopPathABackend` +
  integration guide exist; the seam introduces no language-dependent dependency back into the core.
- Any future Path-A backend's acceptance is defined as measured via the `core:eval` harness and reported
  as **FRR + FAR/hour** (recorded in the guide; the harness is a pending prerequisite).
- Disclosure-gating + adapter logic unit-tested; the `SpeechBackend` adapter runs in the reliable
  autonomous gate (`:core:enrollment:test`); the disclosure ViewModel test runs under whole-project
  `make verify`. **These A-deliverables landed 2026-06-28** (`MicDisclosureDialog.kt`, `LicensesScreen.kt`,
  `SpeechBackend.kt`/`TemplateSpeechBackend`/`NoopPathABackend`) with `make verify` + 9/9 guardrails
  green then (see `docs/plans/INDEX.md`); re-run `make verify` after any further change.
- **Bucket-C honesty:** the Play form submission (account) and a working Vosk/sherpa backend (large
  external model + native runtime + license vetting) are out of autonomous scope, documented as the
  human's next step; nothing pretends they are done.

## Risks & Mitigations

- **Risk (the #1 finding): interface over-fits the template engine** (forces Vosk to fake template
  fields). Mitigation: neutral `BackendResult`; DTW fields confined to the template subtype; capability
  flags. **Closing action (owned by Step 6's guide):** the integration guide includes a concrete
  Vosk/sherpa-onnx API mapping table (their streaming result → `BackendResult`) that must be filled in
  and reviewed *before* any real backend is wired — the seam is not considered "locked" until that table
  exists in the guide.
- **Risk: stateful adapter regresses the pure recognizer.** Mitigation: the adapter wraps, it does not
  replace; `Recognizer` stays pure; only the adapter holds state.
- **Risk: license drift / wrong claim.** Mitigation: single declared license source; explicit Silero
  STT exclusion; reviewed against research §6.
- **Risk: disclosure copy insufficient for Play.** Mitigation: follow current prominent-disclosure
  guidance in the checklist; easy to update.
- **Risk: scaffolding implies Path-A is done.** Mitigation: `Noop` naming + Bucket-C DoD + ROADMAP item
  stays `[ ]` "scaffold only".
- **Rollback:** both pieces are additive. The disclosure dialog is gated on a `:data` flag — reverting
  its wiring leaves the mic flow as it was; `SpeechBackend`/`NoopPathABackend` are a new interface with
  no caller bound in DI yet (no backend selector exists — confirmed), so removing them touches nothing
  in the live template path.

## Test & Verification

- Autonomous: plain-JUnit for disclosure gating + the `SpeechBackend` adapter (`:core:enrollment:test`);
  guardrail bundle green (plan passes `verify-plan-workflow-guardrails.mjs`); whole-project `make verify`
  re-run after implementation (green on the current tree this session).
- Blocked (external): the Play Console form submission (account) + a real Vosk/sherpa Path-A backend
  (model + native runtime + license vetting) — human-driven follow-ups; this plan delivers the in-app
  disclosure, the neutral interface/scaffold, and the docs that make those follow-ups turnkey.
