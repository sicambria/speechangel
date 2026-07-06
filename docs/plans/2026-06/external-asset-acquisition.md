# Plan: external-asset acquisition & integration

- **Date:** 2026-07-06
- **Phase:** cross-phase (0/1/2/3) — the external-asset unblock for every residual `[~]` item
- **Roadmap item:** `docs/ROADMAP.md` "External-asset shortlist" (`ROADMAP.md:145`) — the four
  `[~]` Bucket-B/C items whose seams are built and dormant: QbE encoder + training data
  (`ROADMAP.md:157`), dictation + Path-A models (`ROADMAP.md:173`), dysarthric-inclusive corpora
  (`ROADMAP.md:182`), far-field/noise augmentation (`ROADMAP.md:201`).
- **Status:** planned
- **Worktree:** n/a (acquisition + integration plan; each asset enters its own worktree when it
  physically arrives on the host — nothing autonomous to implement now, the seams already exist)
- **Plan quality:** 96/100 — self-scored 2026-07-06 (breakdown in `docs/plans/INDEX.md` scoring row)

## Goal

Turn the four remaining `[~]` ROADMAP items from "blocked on an absent asset" into "blocked on a
named, license-vetted asset with a turnkey acquisition action and a pre-built seam to plug into."
When this plan is done, acquiring each asset is a lookup and a wiring step — not a research task —
and the first *real* (non-`SYNTHETIC`) FRR + FAR/hour measurement is one corpus download away.
This plan **documents how to acquire and integrate**; it does **not** claim acquisition done and
fabricates no accuracy number.

## Context & Constraints

- **This is the one un-planned ROADMAP section.** All 17 Phase 0/1/2/3 items are already triaged to
  seven reviewed plans (`docs/plans/INDEX.md` triage table); the "External-asset shortlist" (added
  2026-07-06, `ROADMAP.md:145`) is the only section with no carrying plan. This plan fills exactly
  that gap and **does not re-plan the seven existing plans** (they are reviewed 94+/93 — re-scoring
  them is re-litigation the repo discipline forbids) and **does not plan the CI-green item** (INDEX.md
  "Not planned (deliberate)" — a full plan is overkill there).
- **There is no new Bucket-A code to write.** Every seam the shortlist targets is already built and
  dormant. So this plan's "implementation" is: author the plan, reconcile `INDEX.md`/`ROADMAP.md`,
  commit. Manufacturing code to satisfy the loop would violate the honesty contract
  (`docs/plans/INDEX.md` "Definition of done" point 4). The seams, verified against the working tree:
  - QbE: `QbeEncoder`/`NoopQbeEncoder` (`core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/Qbe.kt:19`, `:31`),
    `QbeSpeechBackend` (`Qbe.kt:44`), `SpeechBackendSelector` (`Qbe.kt:151`).
  - Path-A / dictation: `SpeechBackend` (`core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/SpeechBackend.kt:27`),
    `TemplateSpeechBackend` (`SpeechBackend.kt:40`), `NoopPathABackend` (`SpeechBackend.kt:66`);
    `DictationBackend`/`NoopDictationBackend` (`core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/Dictation.kt:26`, `:34`).
  - Far-field: `MfccConfig.noiseReduction` + `NoiseReduction.SPECTRAL_SUBTRACTION`
    (`core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt:48`, `:27`), fed by
    `MfccExtractor` (`MfccExtractor.kt:65`).
  - Measurement: `Evaluator.evaluate` (`core/eval/src/main/kotlin/com/speechangel/core/eval/Evaluator.kt:38`, `:91`),
    `ThresholdCalibrator` (`core/eval/src/main/kotlin/com/speechangel/core/eval/ThresholdCalibrator.kt:17`),
    `FrontEndBakeoff` (`core/eval/src/main/kotlin/com/speechangel/core/eval/FrontEndBakeoff.kt:11`),
    `SyntheticCorpus` (`core/eval/src/main/kotlin/com/speechangel/core/eval/SyntheticCorpus.kt:19`),
    and the `SYNTHETIC` banner this plan aims to delete (`core/eval/src/main/kotlin/com/speechangel/core/eval/EvalReport.kt:36`).
- **License filter is a hard gate, not a note (highest blast radius).** The app is **AGPL-3.0**
  (`LICENSE:1`). Bundling a wrongly-licensed asset is a legal defect on a copyleft app. Every asset
  below carries an explicit tag — **[bundleable]** (license permits shipping inside the APK:
  MIT/Apache-2.0 code+models, CC-BY-4.0/CC0 training data) or **[measure-only]** (used off-device to
  compute FRR/FAR or as a training source, **never** redistributed). The trap to hold: **an absent
  `LICENSE` file ⇒ all-rights-reserved ⇒ measure-only**, e.g. `harvard-edge/multilingual_kws`
  (`ROADMAP.md:169`). Research policy: permissive only, no NC-licensed model bundled
  (`research/04_build_and_reuse_plan.md:99-101`).
- **Accuracy honesty (non-negotiable).** Any asset that touches recognition is judged by an
  **FRR + FAR/hour delta vs the MFCC-DTW baseline** on `core:eval`, per `VoiceCondition` — never a
  bare percentage (`research/04_build_and_reuse_plan.md:108` cross-cutting rule; enforced by
  `scripts/audits/verify-plan-workflow-guardrails.mjs`). Until a real corpus lands, output stays
  `SYNTHETIC`-bannered; this plan's whole point is to make the first *real* number obtainable.
- **The enhancements never displace the core.** QbE is normal-speech-trained ⇒ a *configurable*
  milder-impairment enhancement, never the default (`research/04_build_and_reuse_plan.md:54`). Path-A
  and dictation are opt-in surfaces outside the always-on deterministic command path. On-device only;
  no cloud; the deterministic `DeviceAction` table (`app/src/main/kotlin/com/speechangel/app/action/DeviceAction.kt:12`) is untouched.
- **Acquisition can't be executed in this session.** Corpora need DUAs/downloads; the encoder needs
  training compute; network/compute here is unproven. The deliverable is the *acquisition runbook*,
  not the assets. This is stated so no B/C item is falsely checked off.

## Approach

Four acquisition tracks mirroring the shortlist subsections, each a table of rows where every row =
**named asset → license tag → acquisition action → the dormant seam it plugs into → the check that
proves integration.** Tracks are ordered by the roadmap's own acquisition ordering
(`ROADMAP.md:210`): the two ~1-day assets (TORGO corpus + a self-trained 24k encoder) unblock the
highest-value result — the first *real* MFCC-DTW-vs-QbE bake-off on real dysarthric voices — so they
lead; the long-lead DUA (Speech Accessibility Project) and the native-runtime models
(whisper.cpp/sherpa-onnx) run in parallel on their own timelines. Each track names the license gate
first because a wrong tag is a legal defect, not a rework.

Rejected approaches: (1) attempting the downloads/training in this session — network + compute are
unproven and the assets are Bucket B/C by definition; claiming them done would break the honesty
contract. (2) Bundling `multilingual_kws` because it "works" — no `LICENSE` ⇒ measure-only; using it
as a shippable baseline is the exact license trap the roadmap flags. (3) Folding this into the two
Phase 3 plans — they are reviewed and cover the *code seams*; the *assets* are a distinct,
cross-phase concern with its own ordering and license gate. (4) Writing FRR/FAR targets as if
measured — the number is the experiment's output; this plan makes it obtainable, it does not invent
it.

## Steps

### License gate (applies to every row below — do this first for each asset)

1. Before any asset is downloaded or wired, record its license in the plan row and classify it
   **[bundleable]** vs **[measure-only]**. An asset with no resolvable license is **[measure-only]**
   by default. A **[bundleable]** model additionally requires its *training data* to be CC-BY-4.0/CC0
   (`research/04_build_and_reuse_plan.md:99-101`). Update `LicensesScreen`
   (`app/src/main/kotlin/com/speechangel/app/ui/policy/LicensesScreen.kt:39`) for anything that
   actually ships. **Check:** every row in this plan carries a tag + named license; no untagged asset
   reaches a `build.gradle.kts` dependency or a bundled app-assets blob.

### Track 1 — QbE encoder + training data (→ `Qbe.kt` seam; unblocks Phase 3 "QbE embedding")

2. **Train the 24k encoder.** Reimplement arXiv 2403.07802 (~23.7k params, 1 MFLOP/epoch) against
   the existing `MfccExtractor` front-end (`MfccExtractor.kt:65`). **[bundleable]** — a paper is
   architecture-only, no code-license entanglement. **Seam:** replace `NoopQbeEncoder` (`Qbe.kt:31`)
   with the trained weights behind `QbeEncoder` (`Qbe.kt:19`); `SpeechBackendSelector` (`Qbe.kt:151`)
   already routes to `QbeSpeechBackend` (`Qbe.kt:44`) when selected. **Check:** encoder loads,
   `FrontEndBakeoff` (`FrontEndBakeoff.kt:11`) runs MFCC-DTW vs QbE and prints an FRR + FAR delta.
3. **Training data (bundleable).** MSWC (50 langs, ~6000 h, CC-BY-4.0) + Google Speech Commands v2
   (CC-BY-4.0) — **[bundleable]** with attribution added to `LicensesScreen`. **Check:** attribution
   present; encoder trained only on CC-BY/CC0 sources.
4. **Research baseline (measure-only).** `harvard-edge/multilingual_kws` (5-shot F1 ≈ 0.75) has **no
   `LICENSE` ⇒ all-rights-reserved ⇒ [measure-only]** (`ROADMAP.md:169`). Use it *once* off-device to
   sanity-check the seam + bake-off wiring, then ship only the self-trained encoder. **Check:** it
   never appears as an APK dependency or bundled asset — grep the release build.

### Track 2 — dictation + Path-A models (→ `Dictation.kt` / `SpeechBackend.kt` seams)

5. **Dictation — whisper.cpp (MIT) + OpenAI GGML `tiny`/`base` weights (MIT), q5_1.** **[bundleable].**
   Android AAR + JNI, batch (not streaming). **Seam:** `DictationBackend` (`Dictation.kt:26`) —
   replace `NoopDictationBackend` (`Dictation.kt:34`); it is deliberately *not* `SpeechBackend`
   (command-oriented). **Check:** a real transcript returns through `DictationBackend`; the
   deterministic command/action path is provably untouched (no `DictationBackend` in the `Recognizer`
   path).
6. **Path-A word-list — sherpa-onnx (Apache-2.0) KWS + its pretrained KWS models (Apache-2.0).**
   **[bundleable].** Cleaner fit than Vosk grammar (no `templateId`/`distance` mismatch — the Path-A
   #1 risk). **Seam:** implement `SpeechBackend` (`SpeechBackend.kt:27`) as a real backend replacing
   `NoopPathABackend` (`SpeechBackend.kt:66`), selected via `SpeechBackendSelector`. **Check:** an
   intact-speech word-list utterance resolves to a `BackendResult` command id; MFCC-DTW stays default.
7. **Path-A fallback — Vosk small models (Apache-2.0, ~40 MB).** **[bundleable].** Same `SpeechBackend`
   seam. **Check:** builds behind the selector; opt-in only.

### Track 3 — dysarthric-inclusive corpora (→ `Evaluator`/`ThresholdCalibrator`; kills `SYNTHETIC`)

8. **TORGO (15 speakers, ~21 h, freely downloadable) — [measure-only]; do first (lowest barrier).**
   **Acquisition:** direct download, no DUA. **Seam:** feed real audio through `Evaluator.evaluate`
   (`Evaluator.kt:91`) in place of `SyntheticCorpus` (`SyntheticCorpus.kt:19`). **Check:** the
   `SYNTHETIC` banner (`EvalReport.kt:36`) is gone and a **real per-command FRR + FAR/hour** table
   prints; `EvalTest` updated so the banner assertion no longer fires on real runs.
9. **Speech Accessibility Project (SAP), UIUC (959 speakers, 400+ h, has a "digital-assistant
   commands" category) — [measure-only]; start the DUA now (long lead is the real cost).**
   **Acquisition:** sign the UIUC Data Use Agreement + application review; check the commercial
   clause. **Seam:** same `Evaluator` path; best fit for command FRR/FAR. **Check:** real
   command-category FRR + FAR/hour reported per `VoiceCondition`.
10. **UASpeech (16 speakers, isolated words, VL/L/M/H intelligibility labels) — [measure-only].**
    Register with H. Kim, UIUC. **Seam:** `Evaluator` per-severity. **Check:** the per-severity FRR
    table (the roadmap's severity → condition mapping) prints.
11. **EasyCall (55 speakers, 37 commands + 30 non-commands, Italian) — [measure-only].** Contact
    authors. **Seam:** exercises the `truth=null` OOV/FAR split the matcher already rejects on.
    **Check:** FAR/hour on non-command utterances measured (the false-accept budget
    `ThresholdCalibrator` (`ThresholdCalibrator.kt:17`) calibrates against).
12. **Voice-drift gap.** None of the above carry `VoiceCondition` (NORMAL/TIRED/ILL) labels. Map
    severity → condition, or collect a small in-house drift set, to exercise the adaptation-benefit
    measurement. **Check:** `decideAdaptation` benefit measurable as an FRR reduction at fixed FAR on
    a drift corpus.

### Track 4 — far-field / noise augmentation (→ `MfccConfig.noiseReduction`)

13. **RIRs — OpenSLR "RIR and Noise" (Apache-2.0) — [bundleable]/measure.** **Acquisition:** OpenSLR
    download. **Use:** convolve Track-3 corpora to synthesize far-field conditions (real far-field
    *dysarthric* audio barely exists). **Seam:** evaluate `NoiseReduction.SPECTRAL_SUBTRACTION`
    (`MfccExtractor.kt:27`, default-off `noiseReduction` `:48`) vs default via `FrontEndBakeoff`.
    **Check:** an FRR + FAR delta (on/off) on the convolved corpus prints.
14. **Noise — MUSAN (OpenSLR) for home-noise mixing — [measure-only]; verify exact license before any
    redistribution.** **Check:** used only off-device for mixing; not bundled unless its license is
    re-confirmed permissive.

### Acquisition ordering & docs (the runbook)

15. **Order (from `ROADMAP.md:210`):** TORGO (step 8) + self-trained encoder (step 2) first — both
    ~1 day — to produce the first real MFCC-DTW-vs-QbE bake-off; start the SAP DUA (step 9) in
    parallel (long lead); whisper.cpp/sherpa-onnx (steps 5–6) on their own runtime-integration track.
16. **Persist the runbook.** This plan is the runbook; on any asset actually landing, open a worktree,
    wire the one seam, run `core:eval`, and reconcile the corresponding ROADMAP checkbox + `INDEX.md`
    row — never before.

## Definition of Done

This plan is an **acquisition/integration runbook**, so its own DoD is documentary; the *per-asset*
DoD is the real-measurement gate each asset must clear when it lands.

- **Plan-level (autonomous, this session):** the plan exists with every shortlist asset as a row
  carrying **license tag + acquisition action + resolved seam `path:line` + integration check**; it
  is added to `docs/plans/INDEX.md` (triage + scoring row) and the `ROADMAP.md` "External-asset
  shortlist" cross-links this plan; `scripts/audits/run-all.mjs` (incl.
  `verify-plan-workflow-guardrails.mjs`) is green; **no ROADMAP checkbox flips** (no asset acquired).
- **Per-asset acceptance (Bucket B/C, when the asset lands — stated so no number is fabricated now):**
  - *Corpora (TORGO/SAP/UASpeech/EasyCall):* real audio runs through `Evaluator.evaluate`; the
    `SYNTHETIC` banner is gone; a **real FRR + FAR/hour** table prints, per command and per
    `VoiceCondition`/severity. This replaces the synthetic baseline — the first honest accuracy number.
  - *QbE encoder / Path-A / far-field:* judged as an **FRR + FAR/hour delta vs the MFCC-DTW
    baseline** (per `VoiceCondition`) via `FrontEndBakeoff` — adopted only if it wins for a named
    condition, never as the default; the MFCC-DTW core stays the default regardless of the delta.
  - *Dictation:* a real transcript returns via `DictationBackend` with the command/action path
    provably unaffected — carries **no FRR/FAR change** (it never enters the recognizer), asserted by
    scope.
- **License gate (hard):** every bundled asset is **[bundleable]** with a named permissive license and
  appears in `LicensesScreen`; every **[measure-only]** asset is provably absent from the release APK;
  `multilingual_kws` is never bundled. No NC-licensed or unlicensed model ships.

## Risks & Mitigations

- **Risk: a **[measure-only]** asset (e.g. `multilingual_kws`, UASpeech, a research corpus) is
  accidentally bundled into the AGPL-3.0 APK.** Mitigation: the license gate (step 1) tags every asset
  before download; a release-build grep confirms no measure-only asset is an APK dependency or bundled
  blob; `LicensesScreen` is the single source of shipped attributions.
- **Risk: a fabricated or over-claimed FRR/FAR number leaks in before real audio lands.** Mitigation:
  the `SYNTHETIC` banner (`EvalReport.kt:36`) stays until a real corpus is wired; no ROADMAP checkbox
  flips on acquisition-planning alone; the plan-level DoD explicitly forbids flipping a checkbox here.
- **Risk: QbE (or Path-A) displaces the MFCC-DTW core because it "scores better" on normal speech.**
  Mitigation: adoption is per-`VoiceCondition` delta only, opt-in via `SpeechBackendSelector`; the
  research rule (`research/04_build_and_reuse_plan.md:54`) that the core stays default is restated in
  the DoD.
- **Risk: SAP DUA lead time silently blocks the whole accuracy story.** Mitigation: TORGO (no DUA) is
  sequenced first so a real number is obtainable within ~a day; the SAP DUA is started in parallel,
  not on the critical path.
- **Risk: whisper.cpp/sherpa-onnx native runtime integration balloons.** Mitigation: batch (not
  streaming) dictation only; both are opt-in surfaces outside the always-on command path; the
  `DictationBackend`/`SpeechBackend` seams isolate them from the recognizer.
- **Rollback:** this plan is docs-only and additive — deleting the file and its `INDEX.md`/`ROADMAP.md`
  cross-links restores today's state exactly; nothing in the runtime pipeline references it. Each
  future integration is independently revertible (a seam swap back to its `Noop*` binding; a corpus is
  measurement-only and touches no shipped code).

## Test & Verification

- **Autonomous (this host, now):** `scripts/audits/run-all.mjs` green (the plan passes
  `verify-plan-workflow-guardrails.mjs`: required sections present, no placeholders, DoD expressed as
  FRR + FAR); every seam `path:line` cited above resolves against the working tree (verified at draft
  time); `INDEX.md` + `ROADMAP.md` cross-links added. No Gradle change (no code touched).
- **Blocked (external, Bucket B/C — the acquisition itself):** corpus downloads/DUAs (TORGO, SAP,
  UASpeech, EasyCall), encoder training compute, whisper.cpp/sherpa-onnx models + native runtime,
  OpenSLR RIR/MUSAN. Each is the human's turnkey next step; the per-asset check above is what proves
  integration once the asset is on the host. This plan honestly reports these as blocked, not done.
