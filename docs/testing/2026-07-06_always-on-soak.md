# Always-on survival soak — emulator (critical-path item 3)

- **Date:** 2026-07-06
- **Device:** `changemappers-test` AVD (Pixel 6, API 35). Always-on preference persisted (Home toggle
  ON before the tests).

## Results

| Scenario | Method | Result |
|---|---|---|
| **Doze (deep idle)** | `dumpsys deviceidle enable` → `battery unplug` → `dumpsys deviceidle force-idle` | Device entered **deep IDLE** (`get deep` → `IDLE`); the app process (pid 3140) **survived** the transition. |
| **Reboot survival** | `adb reboot` → wait `sys.boot_completed=1` → `dumpsys notification` | **`BootReceiver` fired and posted the legal tap-to-resume notification:** id=2001, channel=`resume`, `android.title="Tap to resume listening"`, `contentIntent` → `startActivity` (AUTO_CANCEL). |
| **BootReceiver registration** | `dumpsys package` | `com.speechangel.app.debug/…/service.BootReceiver` registered for `android.intent.action.BOOT_COMPLETED` with `RECEIVE_BOOT_COMPLETED`. |

The reboot behaviour is **by design**, not a limitation: on SDK 35 a `microphone` foreground service
**cannot** be started from a `BOOT_COMPLETED` broadcast. `BootReceiver` therefore reads the persisted
always-on flag and posts a one-tap "Tap to resume listening" notification whose intent re-enters the
app and restarts the foreground mic service legally. That mechanism was observed working end to end on
the emulator after a real reboot.

## The honest boundary (needs a physical device)

- **Per-OEM task-kill is NOT emulable.** Aggressive OEM battery managers (Xiaomi/Huawei/Oppo/Vivo/…)
  kill background apps in ways the stock AOSP emulator does not reproduce. The in-app mitigation
  (`OemAutostart` guidance + DontKillMyApp deep links) is unit-tested, but its real effect can only be
  measured on the specific OEM devices — Bucket B.
- **Long-duration battery/wake soak** (hours of always-on listening → battery drain, wakelock
  behaviour) likewise needs a physical device with a real battery.
- **The Phase-2 exit lines are NOT flipped** on this run — Doze + reboot-resume are shown on the
  emulator; OEM-kill and battery soak remain physical-device-only.
