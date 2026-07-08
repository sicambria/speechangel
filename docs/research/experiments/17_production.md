# Domain 17: Production System Engineering & Hardening

**Goal:** Harden the always-on recognition loop for real-world deployment — reliability, crash resilience, graceful degradation, and monitoring.

---

## E17-01: Audio pipeline watchdog (silence detection + auto-restart)
**Hypothesis:** Android's AudioRecord can silently fail (return zeros, stop delivering buffers) without throwing exceptions, especially after Doze cycles or Bluetooth reconnects. A watchdog that detects sustained silence (>30s of near-zero audio) and auto-restarts the capture ensures always-on reliability.
**Score:** Impact=300 Feasibility=280 Constraints=200 Evidence=80 → **860 (S)**
**Description:** Monitor audio RMS over 30-second windows. If RMS < 0.001 (near silence) for 30 consecutive seconds while the service is "listening," close and re-open AudioRecord. Log restart events. Measure: (a) mean time between silent failures, (b) recovery time, (c) false restart rate (restarting during genuine silence).
**Expected outcome:** Auto-restart recovers from 90%+ of silent AudioRecord failures within 5 seconds. This is shipping-critical — a "listening" icon with silent capture is the worst UX failure mode.
**How to run:** Watchdog logic in AndroidAudioRecorder + failure injection + recovery measurement.

## E17-02: Graceful degradation under CPU throttling
**Hypothesis:** When the OS throttles CPU (thermal, battery saver), the recognition pipeline should degrade gracefully — skip non-critical processing (vocabulary distinctness check, embedding quality scoring), reduce frame rate, extend VAD hangover — rather than dropping audio or crashing.
**Score:** Impact=260 Feasibility=240 Constraints=200 Evidence=60 → **760 (A)**
**Description:** Monitor CPU throttling via `thermal status` and `battery saver` intents. Implement degradation levels: Level 1 (mild): drop non-critical processing. Level 2 (moderate): increase frame step from 10→20ms. Level 3 (severe): Stage-2 only, skip wake-gated streaming. Measure accuracy at each level.
**Expected outcome:** Graceful degradation preserves Stage-1 wake detection at all levels. Stage-2 FRR degrades by 5-10pp at Level 3. System stays alive and functional — never silently drops audio.
**How to run:** Throttling monitor + degradation controller + accuracy-at-each-level benchmark.

## E17-03: Crash-loop detection with exponential backoff
**Hypothesis:** If the ListeningService crashes (rare but possible from unhandled edge cases in native code or OS resource exhaustion), it should restart with exponential backoff (1s, 2s, 4s, 8s, ... max 60s) rather than looping or staying dead. The AccessibilityService and assistant role provide survival even across crashes.
**Score:** Impact=280 Feasibility=270 Constraints=200 Evidence=70 → **820 (S)**
**Description:** Implement `UncaughtExceptionHandler` in ListeningService that logs crash, increments backoff counter, and reschedules service start via `AlarmManager` with exponential delay. After 10 crashes in 1 hour, disable listening and show persistent notification: "SpeechAngel paused — tap to restart."
**Expected outcome:** Crash recovery within 30s for 95% of crash types. Crash-loop prevention prevents battery drain from repeated restart attempts.
**How to run:** Crash handler + exponential backoff + crash-injection testing.

## E17-04: Permission state machine (runtime permission loss handling)
**Hypothesis:** RECORD_AUDIO permission can be revoked at runtime (Settings app, permission auto-reset on Android 11+). The app must detect permission loss immediately and guide the user/caregiver to restore it, rather than silently failing.
**Score:** Impact=260 Feasibility=270 Constraints=200 Evidence=70 → **800 (A)**
**Description:** Check `checkSelfPermission(RECORD_AUDIO)` before every AudioRecord session start. On permission loss: (a) post persistent notification, (b) if AccessibilityService is running, use it to open Settings, (c) on permission restore, auto-resume listening.
**Expected outcome:** Permission loss detected within 1 frame (~150ms). Recovery UX guides user to restore permission in <30s. Never show "listening" when mic is unavailable.
**How to run:** Permission state monitor + recovery flow + permission-revocation testing.

## E17-05: Bluetooth headset transition (SCO → audio rerouting)
**Hypothesis:** When a Bluetooth headset connects/disconnects, the audio source silently changes — the built-in mic stops and the BT mic starts (or vice versa). The app must detect routing changes and restart the AudioRecord on the new device without missing more than 1-2 seconds.
**Score:** Impact=240 Feasibility=200 Constraints=200 Evidence=60 → **700 (A)**
**Description:** Register `AudioManager.AudioDeviceCallback` to detect route changes. On change: (a) drain remaining buffers from old source, (b) close old AudioRecord, (c) open new AudioRecord on new source with same config, (d) measure gap duration. Notify user with a quiet tone or vibration.
**Expected outcome:** Audio route transition gap <2 seconds. User experiences at most a brief pause. Essential for headset-using users.
**How to run:** AudioDeviceCallback + route-change handler + BT plug/unplug testing.

## E17-06: Feature parity verification with CI regression tests
**Hypothesis:** A regression test suite that runs the full recognition pipeline (MFCC → DTW → match) on a set of fixed WAV files and verifies that the output matches (within float tolerance) ensures that code changes don't silently degrade recognition.
**Score:** Impact=200 Feasibility=260 Constraints=200 Evidence=80 → **740 (A)**
**Description:** Commit 10-20 reference WAV files (synthetic or anonymized TORGO clips) + expected match results (command ID, distance, confidence). CI test: run pipeline on reference files, assert output matches expected within tolerance. Fail CI on deviation.
**Expected outcome:** Catches silent-regression bugs (MFCC config change, DTW algorithm change, threshold drift) before they reach users. Standard practice for ML systems.
**How to run:** Reference WAV + expected results + CI pipeline test.

## E17-07: Structured error telemetry (opt-in, privacy-preserving)
**Hypothesis:** Opt-in error telemetry (anonymized, aggregated, no raw audio) that reports: (a) command ID of false accepts/rejects (user corrected), (b) DTW distance distribution, (c) VAD drop rate, (d) CPU throttling events, (e) crash stack traces. This data is essential for debugging field issues that can't be reproduced in the lab.
**Score:** Impact=220 Feasibility=180 Constraints=160 Evidence=60 → **620 (B)**
**Description:** Implement telemetry collector with strict privacy guarantees: (a) opt-in only, (b) never sends raw audio or features, (c) command IDs are hashed, (d) all data aggregated before leaving device. Dashboard for analyzing field accuracy per Android version / device / OEM.
**Expected outcome:** Field accuracy measurement reveals deployment-vs-lab gap. Identifies OEM-specific issues (Xiaomi audio capture failures, Samsung CPU throttling patterns).
**How to run:** Telemetry collector + hashing + aggregation + dashboard.

## E17-08: Command action execution confirmation (deterministic feedback loop)
**Hypothesis:** After executing a device action (e.g., HOME, BACK), the AccessibilityService should verify the action was executed (e.g., check if the current package changed, or if the notification shade is now open). If the action failed silently, retry or notify the user.
**Score:** Impact=200 Feasibility=220 Constraints=200 Evidence=50 → **670 (B)**
**Description:** After `performGlobalAction(HOME)`, wait 500ms, check `rootInActiveWindow.packageName == "com.android.launcher"`. If not, retry once. If still fails, post a notification: "Action 'Home' didn't execute." Measure action success rate and silent failure rate.
**Expected outcome:** Action success rate >99%. Silent failures detected and surfaced rather than ignored.
**How to run:** Action verification + retry + success-rate telemetry.

## E17-09: Power-efficient notification management
**Hypothesis:** The persistent foreground service notification ("SpeechAngel is listening") should be as lightweight as possible to minimize notification-drawer clutter and battery impact. A minimal notification (no lights, no vibration, low priority) that still meets FGS requirements.
**Score:** Impact=120 Feasibility=280 Constraints=200 Evidence=70 → **670 (B)**
**Description:** Configure notification channel: IMPORTANCE_LOW, no sound, no vibration, no lights. Notification content: "Listening" with a small icon. Update only when state changes (wake detected, command recognized) — never every frame. Measure notification-trigger wakelocks.
**Expected outcome:** Notification channel causes <0.1%/hr battery impact. Meets Android FGS requirements with minimal user disruption.
**How to run:** Notification channel config + wakelock measurement.

## E17-10: Emulator-vs-device accuracy gap quantification
**Hypothesis:** The emulator's silent microphone provides no useful audio, so all accuracy numbers are from offline WAV evaluation. Recording real commands on a physical device and comparing offline MFCC-DTW rank-1 vs emulator eval quantifies the sim-vs-real gap.
**Score:** Impact=250 Feasibility=180 Constraints=200 Evidence=60 → **690 (B)**
**Description:** Record a small command set (10 commands × 3 repetitions) on a physical Android device in quiet conditions. Run the same pipeline offline and on-device. Compare: (a) MFCC values (device capture vs WAV loading), (b) DTW distances, (c) rank-1. Quantify the hardware gap.
**Expected outcome:** Device capture introduces 2-5% rank-1 degradation vs clean WAV (due to mic frequency response, AGC, codec compression). This is the "hardware tax" that must be accounted for in sim-eval numbers.
**How to run:** Device recording + offline pipeline + comparison analysis.
