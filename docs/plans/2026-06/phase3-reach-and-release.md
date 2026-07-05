# Plan: phase 3 reach and release

- **Date:** 2026-07-05
- **Phase:** 3 (Delight & reach)
- **Roadmap item:** Phase 3 "Shareable command packs"; Phase 3 "F-Droid + Play release"; Phase 3
  "whisper.cpp batch dictation (optional)"
- **Status:** active (all three Bucket-A slices implemented + tested 2026-07-05: command packs, F-Droid/Play scaffold + R8, DictationBackend; C walls — accounts, signing key, whisper.cpp model — remain external)
- **Worktree:** n/a (docs-only plan; each item enters its own worktree when scheduled to build)
- **Plan quality:** 93/100 — self-scored 2026-07-05 (see `docs/plans/INDEX.md` scoring row)

## Goal

Take SpeechAngel from a single-device build to something shareable and shippable, and add the one
optional productivity surface the research names — batch dictation — without compromising the core
promise. Concretely: (1) a **shareable command-pack** export/import format so a caregiver can distribute
a curated vocabulary + action mapping that each user then re-enrolls in *their own* voice; (2) the
**release scaffolding** for F-Droid + Play (signing, R8, store/F-Droid metadata) up to the account-bound
submission wall; (3) an **optional whisper.cpp batch-dictation** backend behind a new, correctly-shaped
interface. Each item ships its maximal autonomous slice with the external blocker named precisely.

## Context & Constraints

- **Templates are speaker-dependent — a "command pack" is not a bundle of someone else's audio.** The
  matcher is speaker-dependent template matching; another person's enrolled `Template`s
  (`core/model/.../Domain.kt:75`) do not transfer usefully. So a shareable pack is the **vocabulary +
  action mapping** — `VoiceCommand(id, label, action: ActionId)` (`Domain.kt:72`) — which the recipient
  **re-enrolls in their own voice**. The sharer's templates may optionally be included only for
  same-speaker device-to-device transfer / backup, clearly labelled as such.
- **The command→action link is a plain string id resolved in the app layer.** `CommandEntity.action`
  is a `String` (`data/.../db/Entities.kt:9`) resolved to `DeviceAction` via `DeviceAction.fromId`
  (`app/.../action/DeviceAction.kt:25`). A pack must serialize that string id and **validate it against
  `DeviceAction.fromId` on import** — an unknown action id is rejected, never silently dropped (the
  deterministic action layer must stay sound).
- **Feature blobs have an existing codec.** `data/src/main/kotlin/com/speechangel/data/FeatureCodec.kt`
  encodes template features to
  `ByteArray` (`TemplateEntity.features`, `Entities.kt:23`) — reuse it for optional same-speaker template
  export; do not invent a second serialization.
- **Release is greenfield and account-bound (Bucket C).** `app/build.gradle.kts` has
  `applicationId = "com.speechangel.app"` (:13), `versionCode = 1` / `versionName = "0.1.0"` (:14-15),
  `isMinifyEnabled = false` (:32, R8 deferred), **no `signingConfigs` block anywhere**, and there is
  **no `fastlane` / `fdroid` / `metadata` directory**. Signing keys, the Play Console account, and the
  F-Droid RFP are external; the build wiring + metadata + reproducibility notes are autonomous.
- **whisper.cpp dictation needs a NEW interface — the `SpeechBackend` seam does not fit.**
  `SpeechBackend.recognize` returns a **command-oriented** `BackendResult(commandId, confidence, reason)`
  (`core/enrollment/.../SpeechBackend.kt:14`), not free text. Dictation returns a transcript string, so
  it needs its own `DictationBackend` type — reusing `SpeechBackend` would force a fake `commandId`.
  whisper.cpp is **MIT** (`research/04_build_and_reuse_plan.md:71`), but the model + native runtime are a
  large external dependency (Bucket C).
- **Non-negotiables carry through:** on-device only (dictation runs whisper.cpp locally, no cloud);
  deterministic action layer unchanged; licensing stays MIT/Apache-2.0 with a third-party-licenses
  screen (`app/.../ui/policy/LicensesScreen.kt:39`, currently a hand-maintained list).
- **None of these items touches the recognizer/matcher, so none changes measured FRR/FAR** — stated in
  the DoD so the accuracy-honesty gate is satisfied by *scope*, not by a fabricated metric.

## Approach

Three independent items, ordered by autonomy. Command packs are fully Bucket A (a versioned JSON format
+ import validation + round-trip tests) and land first. Release scaffolding is Bucket A up to the
signing/submission wall (Bucket C). Dictation is a Bucket-A interface + `Noop` + guide with the real
whisper.cpp integration as Bucket C. The design rule throughout: **pack = re-enrollable definition, not
foreign audio; dictation = its own interface, not a bent `SpeechBackend`; release scaffold = everything
short of an account.**

Rejected approaches: bundling the sharer's audio templates as the primary pack payload (speaker-
dependent — useless to another voice, and privacy-hostile); resolving a pack's action id lazily at
action time (an unknown id must fail loudly at import, not at button-press); making dictation implement
`SpeechBackend` (forces a fabricated `commandId` — the same over-fitting the policy plan rejected for
Path-A); enabling R8/`minifyEnabled` blind for release without a tested keep-rule set (silent reflection
breakage); writing Play/F-Droid submission text as if submitted (account-bound — a checklist instead).

## Steps

### Item A — Shareable command packs (Bucket A, lands first)

1. **Pack format.** A new `CommandPack.kt` in a `data/pack` package: a versioned
   `CommandPack(schemaVersion, name, author, commands: List<PackCommand>)` where
   `PackCommand(label, actionId: String, optionalTemplates: List<ByteArray>? = null)`. JSON via the
   existing serialization stack; `optionalTemplates` uses `FeatureCodec` and is **omitted by default**
   (re-enroll model).
2. **Export.** `CommandPackExporter` reads `CommandRepository` (`RoomCommandRepository`,
   `data/.../repository/RoomRepositories.kt:16`), emits a pack (definitions only unless the user opts
   into same-speaker template inclusion). No audio leaves the device unless explicitly chosen.
3. **Import with validation.** `CommandPackImporter`: for each `PackCommand`, **validate `actionId`
   against `DeviceAction.fromId`** (`DeviceAction.kt:25`) — unknown ⇒ collected into a rejection report,
   never imported; valid ⇒ upsert a `VoiceCommand` (recipient then enrolls their own templates via the
   existing `Enroller`). Schema-version mismatch is handled explicitly (accept known, reject future).
4. **App surface.** A share/import entry point (SAF file or share-sheet) in settings/Home; the import
   screen shows what was imported vs rejected and prompts the user to record each command.
5. **Tests (`:data` Robolectric + pure JUnit).** Round-trip: export → import reproduces the command set;
   an unknown `actionId` is rejected and reported (not imported); definitions-only pack imports commands
   with zero templates and flags them "needs enrollment"; a future `schemaVersion` is refused cleanly.

### Item B — F-Droid + Play release scaffolding (Bucket A scaffold / C submission)

6. **Signing config.** Add a `signingConfigs { release { … } }` block to `app/build.gradle.kts` sourced
   from `keystore.properties` / env (never a committed secret); wire `buildTypes.release.signingConfig`.
   The keystore itself is generated by the human (Bucket C) — document the exact `keytool` command.
7. **R8 / shrink for release.** Flip `isMinifyEnabled`/`shrinkResources` on for `release` only, add a
   `proguard-rules.pro` with keep rules for reflection-touched types (Room, Hilt, kotlinx-serialization,
   the pack format), and verify `:app:assembleRelease` builds. `debug` stays unshrunk. (Currently
   `isMinifyEnabled = false`, `app/build.gradle.kts:32`.)
8. **Fastlane / Play metadata.** Create the `fastlane/metadata/android/en-US` tree (title, short + full
   description, changelogs/`<versionCode>.txt`, feature graphic placeholders) — the Play listing as
   version-controlled files. Document the data-safety + permission-declaration answers by pointer to the
   policy plan's checklist (`docs/plans/2026-06/policy-and-path-a.md`, mic FGS rationale).
9. **F-Droid metadata + reproducibility.** Add the F-Droid metadata file `com.speechangel.app.yml`
   (Categories, License, RepoType, Builds, AutoUpdateMode) and a reproducible-build note: no proprietary
   deps, deterministic build, versionCode bump policy. The RFP submission to fdroiddata is Bucket C.
10. **Licenses screen accuracy.** Reconcile `LicensesScreen`'s hand-maintained `THIRD_PARTY` list
    (`LicensesScreen.kt:27`) with the actual dependency graph before release; note a licenses-plugin as
    the durable source so the list can't drift.

### Item C — whisper.cpp batch dictation (Bucket A interface / C model)

11. **Dictation interface (new, not `SpeechBackend`).**
    a new `DictationBackend.kt` under `core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/`
    (or a small new module):
    `interface DictationBackend { fun transcribe(audio: AudioSamples): DictationResult }` returning a
    transcript string + confidence + an availability/`reason`. Deliberately separate from
    `SpeechBackend` (which is command-oriented — `SpeechBackend.kt:14`).
12. **Noop + guide (Bucket C blocker).** `NoopDictationBackend` (returns "unavailable") + a `docs/`
    integration guide: whisper.cpp (MIT), model size/quantization choice, native/JNI wiring, on-device
    batch (not streaming) operation, and that it is an **optional, opt-in** surface that never sits in
    the always-on command path. No model bundled.
13. **Optional text-entry surface (stub).** A minimal "dictate to a text field" screen wired to the
    `DictationBackend` (Noop until the real backend lands) — kept out of the deterministic command flow.
14. **Tests (`:core:enrollment:test`).** A fake `DictationBackend` round-trips audio → transcript; the
    Noop returns unavailable; the command pipeline is provably unaffected (no `DictationBackend` in the
    `Recognizer`/action path).

## Definition of Done

- **Item A (autonomous):** the versioned `CommandPack` format, exporter, and importer exist; import
  **validates every `actionId` against `DeviceAction.fromId`** and reports (never silently drops)
  unknowns; definitions-only is the default (re-enroll model), optional same-speaker templates via
  `FeatureCodec`; round-trip + rejection + schema-version tests green in `:data`. No audio leaves the
  device unless the user explicitly opts in.
- **Item B (autonomous scaffold / C submission):** `signingConfigs` wired from an uncommitted secret;
  `:app:assembleRelease` builds shrunk+signed with tested keep rules; `fastlane` Play metadata and the
  F-Droid `metadata/*.yml` + reproducibility note exist; the `LicensesScreen` list reconciled with the
  dependency graph. **Bucket-C wall documented:** keystore generation, the Play Console account +
  Permission Declaration submission, and the F-Droid RFP are the human's next steps — nothing pretends
  they are done.
- **Item C (autonomous interface / C model):** a correctly-shaped `DictationBackend` (transcript-
  returning, *not* `SpeechBackend`), `NoopDictationBackend`, an optional text-entry stub, and the
  whisper.cpp integration guide exist and are unit-tested; the command/action path is provably
  unaffected. **Bucket-C wall:** the real whisper.cpp model + native runtime is the human's next step.
- **Accuracy-honesty (by scope):** none of these three items touches the recognizer/matcher or the DSP
  front-end, so each carries **no change to measured FRR or FAR/hour** — there is no accuracy delta to
  report or fabricate, and this is asserted rather than left implicit. Licensing stays MIT/Apache-2.0
  (whisper.cpp MIT); the third-party-licenses screen is kept accurate.
- Guardrail bundle green (`scripts/audits/run-all.mjs`), incl.
  `verify-plan-workflow-guardrails.mjs`; `:core:*` / `:data` tests green for any item implemented; the
  ROADMAP items stay `[ ]` until each autonomous slice actually lands.

## Risks & Mitigations

- **Risk: a command pack imports an action the build can't perform** (drift between pack and
  `DeviceAction`). Mitigation: hard `DeviceAction.fromId` validation at import with a rejection report;
  unknown ids never reach the deterministic action layer.
- **Risk: sharing leaks a user's voice audio.** Mitigation: definitions-only by default; templates are
  opt-in, labelled same-speaker-only, and never included silently.
- **Risk: R8 breaks reflection at runtime (Room/Hilt/serialization).** Mitigation: `minifyEnabled`
  release-only with an explicit tested keep-rule set; `:app:assembleRelease` + a smoke test before any
  store push; `debug` stays unshrunk.
- **Risk: committed signing secret.** Mitigation: keystore + credentials sourced from
  `keystore.properties`/env, git-ignored; only the *wiring* is committed.
- **Risk: dictation interface over-fits the command engine** (the policy-plan lesson). Mitigation: a
  separate `DictationBackend` returning free text; it never implements `SpeechBackend` and never enters
  the always-on command path.
- **Risk: licenses screen drifts from actual deps at release.** Mitigation: reconcile against the
  dependency graph as a release-gate step; note a licenses-plugin as the durable source.
- **Rollback:** all three items are additive. Command packs are a new `data/pack` package + UI entry
  (delete → app unchanged; nothing in the runtime pipeline depends on them). Release scaffolding is
  build config + metadata files gated to `release`; reverting the `signingConfigs`/`minifyEnabled`
  changes restores today's debug-only build. Dictation is a new interface + `Noop` + an isolated screen
  with no hook into the command/action path (delete → recognition untouched).

## Test & Verification

- **Autonomous (this host):** `:data` round-trip/validation tests (packs), `:app:assembleRelease` builds
  shrunk+signed with a signing config sourced from an uncommitted secret (release scaffold),
  `:core:enrollment:test` (dictation interface + Noop + isolation) for whichever items are built;
  guardrail bundle green; whole-project `make verify` re-run after any implementation. Docs-only until an
  item is scheduled — no code claimed built.
- **Blocked (external, Bucket C):** the Play Console account + Permission Declaration submission, the
  F-Droid RFP to fdroiddata, human keystore generation, and the real whisper.cpp model + native runtime.
  This plan delivers everything up to those account/model walls and documents each as the human's turnkey
  next step.
