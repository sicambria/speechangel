# Plan: stage1 wake word gate

- **Date:** 2026-06-28
- **Phase:** 1
- **Roadmap item:** Phase 1 "Stage-1 (24/7) Silero VAD gate → software wake word (enrolled DTW wake
  OR microWakeWord)"
- **Status:** done (A-deliverables implemented 2026-06-28; B-items — device battery measurement — pending external input)
- **Worktree:** n/a (single-session, on `main`)
- **Plan quality:** 95/100 — independently confirmed over two review rounds (67 → 93 → 95)
- **Depends on:** `docs/plans/2026-06/recognizer-eval-and-calibration.md` (the `core:eval` harness is a
  hard prerequisite for the wake FRR/FAR DoD). **That prerequisite has landed** — `core:eval` exists and
  is wired in `settings.gradle.kts` — so the remaining wake-FRR/FAR block is a real corpus (Bucket B),
  not a missing harness.

## Goal

Introduce the low-power Stage-1 gate the always-on design needs: a cheap, continuously-running filter
(running-energy gate + an enrolled DTW wake word) that stays silent on the audio that is not the user
addressing the device and, only on a wake, opens the heavier Stage-2 command window — *without* the
wake word leaking into or suppressing Stage-2 command matching.

## Context & Constraints

- **Honest cheapness premise:** today's `Recognizer.recognize` already VAD-gates *before* MFCC
  (`core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/Recognizer.kt` lines 23-26), so
  silence is already cheap. The gate's real, bounded win is **(a)** matching one wake command's
  templates instead of *all* command templates during ambient speech (fewer DTW comparisons), and
  **(b)** not firing Stage-2's full candidate set on every window. This is "fewer DTW comparisons on
  ambient speech", *not* an order-of-magnitude "far cheaper Stage-1" — stated honestly.
- **Capture reality:** `data/.../audio/AudioRecorder` exposes only `suspend fun record(durationMs)`;
  `AndroidAudioRecorder` opens/`startRecording`/`stop`/`release`s a fresh `AudioRecord` per call. A
  per-tiny-frame loop would open/close the mic each frame and clip across the gap — so this plan adds
  a **streaming capture API** rather than pretending one exists.
- **VAD reality:** `EnergyVad.detect` estimates the noise floor as the 10th percentile *of the buffer*
  (`core/dsp/src/main/kotlin/com/speechangel/core/dsp/Vad.kt`). On a short frame that is entirely
  speech, that percentile is itself speech and nothing clears `floor * config.energyRatioOverNoise` (an
  `EnergyVadConfig` field, default 3 — defined `Vad.kt:30`, applied `Vad.kt:57`) → the wake is missed.
  The gate
  therefore needs a **running** noise-floor estimate (or a fixed absolute gate floor), not per-frame
  percentile VAD.
- **Language-independent + on-device:** the wake word is an *enrolled* template matched by DTW — not an
  STT/phoneme model. microWakeWord is an optional alternative (a trained model — note its
  language-independence tension), not the default.
- **Deterministic:** wake detection gates Stage-2; it never itself triggers an action.
- **Accuracy honesty:** the gate has wake **FRR** (missed wakes) and wake **FAR/hour** (spurious
  wakes), measured via the `core:eval` harness, reported as FRR + FAR — never a bare percentage.
- **Battery is Bucket B:** the real power saving is only measurable on a device.

## Approach

Add a pure-Kotlin `WakeWordGate` in `core:enrollment` that is given the wake templates (not just an
id) and a dedicated tighter threshold, and decides `Wake`/`NoWake` on a captured frame using a
running-floor energy check + DTW match restricted to the wake templates. Add a streaming capture API
to `AudioRecorder` so the service can feed the gate continuous frames over one persistent recorder. In
`ListeningService`, run the gate on the stream; on `Wake`, open a Stage-2 command window whose
candidate templates **exclude reserved ids** (so the wake tail can't win Stage-2). Wake templates are
stored under a reserved `CommandId("__wake__")` (valid — `CommandId` only requires non-blank) and are
filtered out of the Stage-2 candidate set everywhere.

Rejected: (a) reusing the unfiltered `allTemplates()` for Stage-2 — it poisons command matching; (b)
looping `record(durationMs)` on tiny frames — mic open/close per frame + inter-frame clipping; (c)
per-frame `EnergyVad` — wrong noise-floor model for short frames; (d) microWakeWord as default — model
dependency + language tension.

## Steps

1. **Streaming capture.** Add `fun stream(frameMs): Flow<AudioSamples>` (one persistent `AudioRecord`,
   emitting fixed-size frames) to `data/src/main/kotlin/com/speechangel/data/audio/AudioRecorder.kt`
   and `AndroidAudioRecorder`; close the recorder on flow cancellation. (Bucket-B note: real capture
   only runs on a device; the interface + a fake `AudioRecorder` drive unit tests.)
2. **Running energy gate.** In `core:dsp`, add a small streaming energy gate (running noise-floor EMA +
   absolute floor) suitable for short continuous frames — do **not** reuse the percentile `EnergyVad`
   for this path. Unit-test that an all-speech frame passes and a quiet frame does not.
3. **Wake gate type.** `core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/WakeWordGate.kt`:
   `WakeWordGate(mfcc, matcher, wakeThreshold)` with
   `evaluate(frame: AudioSamples, wakeTemplates: List<Template>): WakeDecision` (`Wake(distance)` |
   `NoWake(reason)`); internally calls the matcher restricted to `wakeTemplates` with
   `mapOf(wakeCommandId to wakeThreshold)`. The gate holds no repository — templates are passed in.
4. **Reserved wake command + Stage-2 filtering.** Define `ReservedCommands.WAKE = CommandId("__wake__")`.
   Add a `TemplateRepository.commandTemplates()` (or filter at the call site) that returns templates
   with `commandId != WAKE`; **use it for the Stage-2 candidate set** in `ListeningService` so the wake
   tail can never win command matching or resolve to a null `VoiceCommand`.
5. **App wiring (no mic restart at the wake→command boundary).** In `ListeningService`, when a wake word
   is enrolled and the gate is enabled, consume a single persistent `recorder.stream(...)`, run the
   running-energy gate then `WakeWordGate.evaluate(frame, wakeTemplates)` off the main thread
   (`Dispatchers.Default`, matching the existing `recognize` offload). On `Wake`, **assemble the Stage-2
   window by continuing to drain the next N frames from the same already-open stream** — do NOT issue a
   fresh `record()` / reopen the mic, or the command onset (which follows the wake word within a few
   hundred ms) is clipped, inflating command FRR. Then run
   `recognizer.recognize(window, commandTemplates, thresholds)`. When no wake word is enrolled OR the
   gate is disabled, fall back to today's all-templates windowed loop (candidate set still excludes
   reserved ids). The gate derives the wake command id from `ReservedCommands.WAKE` (equivalently the
   passed templates' `commandId`).
6. **Wake enrollment ops.** Enroll/fetch wake templates via the existing `Enroller`/`TemplateRepository`
   under the reserved id (UI lands in the enrollment-adaptation-ux plan's Always-on screen).
7. **Eval integration (the `core:eval` harness now exists).** Extend the landed `core:eval` module to
   score the gate: wake FRR (missed enrolled-wake utterances) and wake FAR/hour over a *named* negative
   corpus (state its duration/source). The harness is no longer a blocker; the remaining gap is a real
   labeled corpus (Bucket B).
8. **Optional backend note.** Document microWakeWord as an alternative `WakeWordGate` implementation
   (model + license + language-independence tension), unimplemented.

## Definition of Done

- `WakeWordGate` + the running-energy gate build and are unit-tested in `:core:enrollment:test` /
  `:core:dsp:test` (the reliable autonomous gate); a test asserts no mic restart occurs between Wake and
  Stage-2 capture (the window is drained from the same stream). **These A-deliverables landed
  2026-06-28** (`WakeWordGate.kt`, `AudioRecorder.stream()`, `ReservedCommands`, the `ListeningService`
  two-stage loop) with `make verify` + 9/9 guardrails green then (see `docs/plans/INDEX.md`); re-run
  `make verify` after any further change.
- Stage-2's candidate set provably **excludes** reserved ids (unit test: a stored `__wake__` template
  does not appear in the command-matching set and cannot be returned as a Match).
- `AudioRecorder.stream` exists with a fake-driven unit test; real mic streaming is Bucket-B.
- Fallback (no wake enrolled / gate disabled) reproduces today's behavior, covered by a test.
- **Blocked-on-corpus:** wake **FRR** and wake **FAR/hour** are reported by the `core:eval` harness
  (now landed) on a named corpus — the harness is in place; this DoD line is satisfied only once a real
  labeled negative/wake corpus exists (Bucket B). No wake FRR/FAR is claimed until measured.
- **Bucket-B honesty:** the battery/CPU saving and real-world wake reliability need on-device
  measurement and are recorded as blocked.

## Risks & Mitigations

- **Risk: wake template poisons Stage-2 (silently drops real commands).** Mitigation: Stage-2 candidate
  set excludes reserved ids; covered by an explicit test (this was the #1 review finding).
- **Risk: streaming capture API regresses the existing `record()` path.** Mitigation: add `stream()`
  alongside `record()`; existing callers untouched; fake-driven tests.
- **Risk: gate threshold too loose (everything wakes) / too tight (misses).** Mitigation: dedicated
  wake threshold calibrated via the eval harness to a wake-FAR budget; conservative default.
- **Risk: running-floor estimator mis-tuned across devices.** Mitigation: EMA + absolute floor with
  unit tests on synthetic frames; device tuning is Bucket-B.
- **Risk: added latency before commands.** Mitigation: gate runs off-main on the stream; Stage-2 opens
  on Wake; end-to-end latency measured on device (B).
- **Rollback:** the gate is opt-in — set no wake word / disable the gate and `ListeningService` falls
  back to today's all-templates windowed loop (Step 5). `WakeWordGate`/`stream()`/`ReservedCommands`
  are additive; reverting the `ListeningService` wiring commit restores the prior single-stage loop
  with no schema or template change.

## Test & Verification

- Autonomous: `:core:dsp:test` (running gate), `:core:enrollment:test` (wake gate + Stage-2 reserved-id
  exclusion + fallback), guardrail bundle green (plan passes `verify-plan-workflow-guardrails.mjs`);
  whole-project `make verify` re-run after implementation (green on the current tree this session).
- Blocked: wake FRR/FAR needs the `core:eval` harness (prereq plan); real wake reliability in noise and
  the battery saving vs always-Stage-2 need an emulator/phone — on-device QA, not here.
