# On-device end-to-end run — emulator (critical-path item 2)

- **Date:** 2026-07-06
- **Device:** `changemappers-test` AVD (Pixel 6, API 35, x86_64), headless (`-no-window`).
- **Build:** `:app:assembleDebug` (BUILD SUCCESSFUL), `app-debug.apk` (21.4 MB), pkg
  `com.speechangel.app.debug`.

## What was verified (the wiring is live on-device)

| Check | Evidence |
|---|---|
| Install + launch, no crash | `adb install -r` → `Success`; `am start …/MainActivity` → pid 3140; logcat has **no** `FATAL`/`AndroidRuntime`. |
| Full UI renders + navigates | Home screen (`2026-07-06_on-device-home.png`): "Always-on listening" toggle **ON**, "Your commands" list with action mappings (`home · does: HOME`, `lights …`), Teach / Try / Packs / Dictation. `Try it` → mic screen (`…-try.png`). |
| **AccessibilityService bound & running** | `dumpsys accessibility` → `Bound services:{Service[label=SpeechAngel voice control, feedbackType[FEEDBACK_GENERIC], capabilities=32, eventTypes=TYPE_WINDOW_STATE_CHANGED]}`; `Enabled services:{…SpeechAngelAccessibilityService}`. The deterministic action executor — the **tail** of the command loop — is live. |
| RECORD_AUDIO grantable | `pm grant … android.permission.RECORD_AUDIO` → granted. |
| Recognizer path reactive | Tapping the `Try it` mic → the ViewModel → recognizer/template store → UI returned **"Teach me a command first"** (`…-mic.png`), the correct result for the 0-template seeded state. The UI→recognizer→UI reactive path executes. |

So the loop is wired end to end and every stage **except live audio** was exercised on-device:
`MainActivity`/UI → `TryViewModel` → `Recognizer`/template store → UI; and independently the
`SpeechAngelAccessibilityService` action executor is bound and running.

## The honest emulator ceiling (needs a physical device)

- **Real audio → enrollment → match → action fire was NOT exercised.** The emulator microphone is
  silent, so no command can be enrolled (needs recorded audio) or matched (needs spoken audio). The
  `Try it` flow correctly reported "Teach me a command first" precisely because there is no real audio
  path to populate templates.
- **Roadmap item 2's real-audio metrics — latency, false-fire rate, CPU — are therefore unmeasured
  here.** They require a physical device (or a debug-only `AudioRecorder` DI binding that feeds a WAV
  through the existing `data/src/main/kotlin/com/speechangel/data/audio/AudioRecorder.kt` interface;
  deliberately **not** built — it is
  debug-only code whose sole purpose is to stand in for the physical-device gap this section
  documents, and the wiring evidence above stands without it).
- **The Phase-1 exit line is NOT flipped** on this run — it validates wiring, not real-audio behaviour.

## Artifacts

`docs/testing/2026-07-06_on-device-home.png`, `…-try.png`, `…-mic.png` (screenshots pulled from the
emulator).
