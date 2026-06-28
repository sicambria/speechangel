# SpeechAngel Roadmap

Derived from `research/04_build_and_reuse_plan.md` §5 (phased plan) and §7 (non-negotiables). The
trackable artifact: each item has a checkbox and a status. Update status as work lands; keep
acceptance criteria honest (FRR + FAR/hour, never a bare "99 %").

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done · status tags: `planned` /
`active` / `blocked` / `done`.

> **Last reconciled: 2026-06-28** against the actual codebase. Basis: `make verify` ran green on this
> host (`detekt spotlessCheck :app:lintDebug test :app:assembleDebug` → BUILD SUCCESSFUL, debug APK
> produced) and an evidence-based source inventory. Checkboxes below reflect *verified code state*,
> not aspiration. Per-item plans live under `docs/plans/2026-06/`.

---

## Phase 0 — Matcher spike (2–3 wks) · status: `active`

Prove the core no OSS app has: record N commands on-device → MFCC + VAD + DTW match → multi-template
+ per-command threshold + reject, on one phone, ugly UI. De-risk before any UX investment.

- [x] `core:model` — domain types (commands, templates, match results). _done — JVM-tested; `core/model/src/main/kotlin/com/speechangel/core/model/Domain.kt`._
- [x] `core:dsp` — MFCC extractor (concatenate static+Δ+ΔΔ, never sum — LIVE BUG #1), mel filterbank,
      FFT, Silero-style VAD endpointing. _done 2026-06-28 — FFT, mel filterbank, energy VAD, static MFCC,
      and now **ΔΔ acceleration** (`DeltaOrder { NONE, DELTA, DELTA_DELTA }`, widths 13/26/39, concatenated
      not summed; tested). Also added a streaming `StreamingEnergyGate` (running noise floor) for Stage-1._
- [x] `core:matching` — DTW distance, `argmin` over templates, per-command distance threshold,
      OOV/reject. _done — length-normalised DTW + Sakoe–Chiba band, per-command thresholds, OOV reject
      (`RejectionReason.BELOW_CONFIDENCE`); JVM-tested incl. command discrimination._
- [x] `core:enrollment` — multi-template enroll, recognizer, repositories. _done — `Enroller`,
      `Recognizer`, repository interfaces; JVM-tested._
- [~] Measure FRR / FAR on real (incl. dysarthric) voices, quiet + home noise. _harness DONE & tested —
      new `core:eval` module: `Evaluator` (FRR + false-accept count, per-command + per-`VoiceCondition`),
      deterministic silence-padded synthetic corpus, `EvalReport.render()`, `docs/testing/frr-far-report-template.md`.
      Still `[ ]` for the real numbers: BLOCKED on a labeled real-voice corpus (Bucket B). Synthetic output
      is banner-marked SYNTHETIC._
- [~] Feature front-end bake-off (plain MFCC vs PLP vs robust embedding). _harness DONE & tested —
      `FrontEndBakeoff` computes an FRR + FA comparison across static / +Δ / +Δ+ΔΔ. Winner-on-real-voices
      blocked on the corpus; PLP deliberately descoped (MFCC variants only)._

**Phase 0 exit:** measured FRR/FAR on a real ~few-dozen-command set; the matcher beats a documented
FAR budget (≤0.5 false accepts/hr) for at least the in-quiet, distinct-command case. _NOT yet met —
gated on real recordings; the measurement machinery is the autonomous part._

---

## Phase 1 — Hands-free MVP (6–8 wks) · status: `active`

Fork the GUI skeleton; ship the core promise for non-rooted phones with cooperative OEMs.

- [x] `:app` module scaffolded + re-enabled in `settings.gradle.kts`. _done — built green._
- [x] `:data` module (Room persistence for enrolled templates). _done — Room entities/DAO +
      `RoomCommandRepository`/`RoomTemplateRepository`; Robolectric round-trip tested._
- [x] Microphone foreground service (`foregroundServiceType="microphone"` +
      `FOREGROUND_SERVICE_MICROPHONE`) — gate: `verify-foreground-service-types.mjs`. _done —
      `ListeningService`; manifest declares both; gate green._
- [~] Stage-1 (24/7) Silero VAD gate → software wake word (enrolled DTW wake OR microWakeWord). _core logic
      DONE & tested — `WakeWordGate` (matches wake templates only, gates Stage-2), `StreamingEnergyGate`
      (running-floor energy gate for short frames), and `ReservedCommands.commandTemplates()` (excludes the
      `__wake__` template from Stage-2 so it can't suppress real commands). PENDING (app/Bucket-B):
      `AudioRecorder.stream()` + `ListeningService` wiring (same-stream drain), battery measurement._
- [x] Stage-2 command matcher wired to the `core:*` engine. _done — `Recognizer` injected into
      `ListeningService`; Match → in-process `CommandActionBus`._
- [x] AccessibilityService — deterministic command→action table (`isAccessibilityTool="true"`). _done —
      `SpeechAngelAccessibilityService` + `DeviceAction` fixed table; no LLM in the loop._
- [x] 4-screen enrollment UX (Teach / Name-Map / Try / Always-on) + caregiver setup wizard. _built &
      `make verify` green — `AlwaysOnScreen` + `CaregiverWizard` added and wired into navigation (Name-Map
      folded into Teach/wizard). On-device visual/UX QA + real-caregiver usability are Bucket B._
- [x] Battery-optimization exemption flow. _built — `BatteryOptimization` (Play-permitted settings
      intent) + an Always-on entry point. The system dialog only appears on a device (Bucket B)._

**Phase 1 exit:** a non-rooted phone runs the full Teach→Try→hands-free loop end to end. _Core loop
is wired and builds; the always-on/battery/wake-word robustness pieces remain._

---

## Phase 2 — Persistence & policy hardening (6–8 wks) · status: `planned`

- [x] Assistant role (`RoleManager.ROLE_ASSISTANT`) for reboot survival. _built — `BootReceiver`
      (exported, `goAsync`) posts a **legal tap-to-resume** notification on boot (a `microphone` FGS
      cannot be started from BOOT_COMPLETED on SDK 35), reading the persisted enable flag; `AssistantRole`
      offers the API-29-guarded role request as optional hardening. Real reboot survival is Bucket B._
- [x] Per-OEM autostart handling (DontKillMyApp guidance). _built — `OemAutostart.resolve` (pure,
      unit-tested for Xiaomi/Huawei/Oppo/Vivo/Samsung/generic) + the Always-on guidance UI with fail-soft
      deep links. Actual OEM settings screens vary per device (Bucket B)._
- [~] Play Permission Declaration Form + prominent mic disclosure. _in-app parts built —
      `MicDisclosureDialog` + `LicensesScreen` (correct license wording incl. Silero-STT exclusion). GAP:
      wiring the dialog into the first mic-permission flow; the Play Console form itself is external (Bucket C)._
- [~] FAR-budget threshold tuning per command. _calibration logic DONE & tested — `core:eval`
      `ThresholdCalibrator` (aggregate FA budget, equal split, per-command thresholds bounding false
      accepts) returns the `Map<CommandId, Float>` the matcher already accepts. PENDING (app): persisting
      + passing the map into `ListeningService`._
- [~] Multi-template re-enrollment polish + confirmation-gated adaptation. _pure decision logic DONE &
      tested — `decideAdaptation` (condition-aware pruning that never evicts a sole-condition example,
      DTW-redundancy selection, deterministic tiebreak). PENDING (app): the "remember this" UI + repository
      orchestration._
- [~] Optional Path-A intact-speech mode (Vosk grammar / sherpa-onnx KWS). _interface + scaffold DONE &
      tested — backend-neutral `SpeechBackend` + `BackendResult`/`BackendRejection`, `TemplateSpeechBackend`
      adapter, `NoopPathABackend`. A real Vosk/sherpa backend remains BLOCKED (large external model — Bucket C)._

---

## Phase 3 — Delight & reach (ongoing) · status: `planned`

- [ ] QbE embedding enhancement (few-shot, milder impairment). _status: planned_
- [ ] Vocabulary-distinctness helper (warn on acoustically-close commands). _status: planned_
- [ ] Far-field / noise front-end. _status: planned_
- [ ] whisper.cpp batch dictation (optional). _status: planned_
- [ ] Shareable command packs. _status: planned_
- [ ] F-Droid + Play release. _status: planned_

---

## Cross-cutting non-negotiables (carry into every phase)

- [x] Deterministic action layer — **never** an autonomous LLM agent. _held — `DeviceAction` fixed
      table; verified no LLM in the action path._
- [ ] Accuracy always reported as FRR + FAR/hour. _enforced for plans by
      `verify-plan-workflow-guardrails.mjs`; awaiting real measurement._
- [x] On-device enrollment stays the core — no regression to a language-dependent STT core. _held —
      recognizer is speaker-dependent template matching; no STT/phoneme model._
- [ ] Licensing: keep Silero VAD/whisper.cpp (MIT), Vosk/sherpa-onnx (Apache-2.0); avoid NC-licensed
      models; ship a third-party-licenses screen. _status: planned (no third-party models added yet)._

---

## Workflow / framework track (this port)

- [x] AI workflow + guardrail system transplanted (Wave 0/2/3 + Android guardrails). _status: done_
- [x] Install git hooks (`git config core.hooksPath .husky`) to make gates Enforced. _done 2026-06-28 —
      hooks active; pre-commit + pre-push run green._
- [x] Port worktree/plan tooling (Wave 1). _done — `docs/plans/TEMPLATE.md`, `scripts/ops/create-plan.mjs`,
      `scripts/audits/verify-plan-workflow-guardrails.mjs` (wired into the bundle)._
- [~] CI workflow running the guardrail + core-test subset. _present — `.github/workflows/ci.yml`
      (build-test + guardrails jobs); not yet observed green on a GitHub Actions run._

See `docs/meta/port-status.md` for the honest wave-by-wave status.
