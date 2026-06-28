# Plan: always on survival

- **Date:** 2026-06-28
- **Phase:** 1 (battery) + 2 (assistant role, OEM autostart)
- **Roadmap item:** Phase 1 "Battery-optimization exemption flow"; Phase 2 "Assistant role
  (`RoleManager.ROLE_ASSISTANT`) for reboot survival"; Phase 2 "Per-OEM autostart handling
  (DontKillMyApp guidance)"
- **Status:** planned
- **Worktree:** n/a (single-session, on `main`)
- **Plan quality:** 95/100 — independently confirmed over two review rounds (61 → 93 → 95)

## Goal

Help the always-on listening service survive Doze/battery optimization, reboots, and OEM
process-killers on non-rooted phones — within what the platform actually permits. The honest ceiling on
SDK 35 is **assisted, user-tap re-arm**, not silent auto-restart; this plan delivers the legal flows
(battery-exemption request, a boot *notification* that the user taps to re-arm, OEM autostart guidance)
and is explicit that true unattended survival is not achievable for a `microphone` foreground service.

## Context & Constraints

- **Hard platform limit (verified):** a `microphone` foreground service **cannot** be started from a
  `BOOT_COMPLETED` receiver on Android 14/15 (compile/targetSdk 35) — it throws
  `ForegroundServiceStartNotAllowedException` (boot-completed type restriction *and* the Android-14
  while-in-use background-start rule). The only service here (`ListeningService`,
  `foregroundServiceType="microphone"`) is exactly this type. **The battery-optimization exemption does
  NOT lift this** (different policy axis). So boot survival is a *user-tap* flow, not silent restart.
- **Play-policy line:** battery exemption uses a Play-permitted route with prominent disclosure; the
  assistant role is requested, never forced and is not claimed to lift any FGS/boot restriction.
- **Deterministic, no autonomy:** re-arming only restarts the existing service after a user tap; no
  autonomous action.
- **SDK span:** minSdk 26, compileSdk 35 — `RoleManager`/`ROLE_ASSISTANT` are API 29+ and must be
  version-guarded.
- **Bucket A vs B:** the request flows, the boot notification + tap re-arm, the role-request intent, and
  the OEM table are buildable + unit-testable here. Confirming survival across a real reboot / Doze /
  OEM killer is on-device (Bucket B).

## Approach

Four pieces in `:app` + a persisted flag in `:data`: (1) a persisted "listening enabled" flag (DataStore
in `:data`) written by the toggle and read on boot; (2) battery-exemption check + a Play-permitted
settings intent; (3) a `BootReceiver` that, on boot, if the flag is set, **posts a notification** ("tap
to resume listening") whose tap brings the app to the foreground and legally starts the FGS — it never
starts the FGS itself; (4) an OEM autostart guidance table + screen, and an optional, version-guarded
`ROLE_ASSISTANT` request presented as unverified hardening.

Rejected: starting the FGS from `BOOT_COMPLETED` (illegal — the core review finding); the direct
`ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` allow-prompt as the default (Play restricts it to approved
categories; disclosure does not cure eligibility); claiming the assistant role grants reboot survival
(unsubstantiated); `AlarmManager`/`WorkManager` keep-alive as the primary mechanism.

## Steps

1. **Persisted enable flag (write + read).** Add `ListeningPreferences` (DataStore) in `:data` with a
   suspend write + a `Flow` read. **Write it wherever the toggle flips** — today the toggle is ephemeral
   `mutableStateOf` in `MainActivity.applyListening()`; move that to a `HomeViewModel`/holder that writes
   the flag on enable/disable. Without this write-path the boot read is vacuously always-off.
2. **Battery exemption.** `app/src/main/kotlin/com/speechangel/app/service/BatteryOptimization.kt`:
   `isExempt(context)` + an intent using `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS` (Play-permitted
   list view) by default; document that the direct allow-prompt requires establishing an approved
   use-case category. Add the manifest permission + an in-app disclosure before sending the user there.
3. **Boot receiver (legal, tap-to-resume).** `app/src/main/kotlin/com/speechangel/app/service/BootReceiver.kt`,
   manifest `android:exported="true"` with an `android.intent.action.BOOT_COMPLETED` intent-filter +
   `RECEIVE_BOOT_COMPLETED` permission. `@AndroidEntryPoint`; in `onReceive` use `goAsync()` + a
   coroutine to read the flag off the main thread; if set, **post a resume notification** (tap →
   `MainActivity` → user-initiated FGS start). It must NOT call `startForegroundService`.
4. **Assistant role (optional, guarded).** `app/src/main/kotlin/com/speechangel/app/service/AssistantRole.kt`:
   behind `Build.VERSION.SDK_INT >= Q`, build `RoleManager.createRequestRoleIntent(ROLE_ASSISTANT)`;
   offer from the Always-on screen as optional hardening, explicitly **not** claimed to lift FGS/boot
   restrictions.
5. **OEM autostart guidance.** `app/src/main/kotlin/com/speechangel/app/service/OemAutostart.kt`: a pure
   function `resolve(manufacturer: String): OemGuidance` (known OEMs → steps + best-effort settings
   `Intent`; unknown → generic) + an `OemAutostartScreen` whose deep links catch
   `ActivityNotFoundException` and fall back to manual steps.
6. **Add app test deps.** `app/build.gradle.kts` currently has no Robolectric/androidx-test — add
   `testImplementation(libs.robolectric)` + `testImplementation(libs.androidx.test.core)` *before*
   writing the Android-typed tests.
7. **Tests.** Pure JUnit for `OemAutostart.resolve` (known/unknown manufacturer) and the
   battery-exemption intent action; Robolectric for the boot-receiver decision (flag set → posts
   notification, does NOT start FGS; flag unset → no-op) and `ShadowBuild.setManufacturer` cases.
8. **Docs.** A `docs/` survival-matrix note: mechanism → what it defends → how to verify on device, with
   the explicit statement that unattended reboot survival is not possible for a microphone FGS.

## Definition of Done

- Persisted enable flag has a real write-path (toggle) + read; unit-tested.
- Battery-exemption check + Play-permitted settings intent implemented, reachable from UI, with
  disclosure + manifest permission.
- `BootReceiver` is `exported=true`, reads the flag via `goAsync()`, and on a set flag **posts a
  resume notification** (never starts the FGS); decision logic Robolectric-tested.
- Assistant-role request intent built behind an API-29 guard, offered as optional hardening with no
  survival claim.
- OEM `resolve` + guidance screen handle known/unknown manufacturers (pure-JUnit tested); deep links
  fail soft.
- `app/build.gradle.kts` has the Robolectric/androidx-test deps. Reliable autonomous gate after
  implementation: `:core:*:test` + the new `:app` unit/Robolectric tests; whole-project `make verify`
  is the target full-build gate, re-run after each change (it is green on the *current* tree as of
  2026-06-28; this plan's code is not built yet and makes no green claim).
- **Bucket-B honesty:** real reboot/Doze/OEM-killer survival is on-device verification; this plan
  delivers the legal flows + tests and is explicit that silent auto-restart is impossible here.

## Risks & Mitigations

- **Risk (the #1 finding): FGS-from-boot crashes.** Mitigation: boot only posts a notification; FGS
  starts from the user tap; Robolectric test asserts no FGS start in `onReceive`.
- **Risk: battery-exemption prompt rejected by Play.** Mitigation: default to the settings-list intent;
  direct prompt only with an established category; disclosure copy shared with the policy plan.
- **Risk: OEM settings intents vary / throw.** Mitigation: every deep link wrapped with
  `ActivityNotFoundException` + manual-steps fallback.
- **Risk: boot receiver never fires.** Mitigation: `exported=true` + correct permission/intent-filter
  (the system UID sends the broadcast); covered by review note.
- **Risk: ROLE_ASSISTANT unavailable / pre-Q.** Mitigation: version guard + availability check;
  optional-only.

## Test & Verification

- Autonomous: pure-JUnit (OEM resolve, intent action) + Robolectric (boot decision, manufacturer
  shadows); `:core:*` tests stay green; guardrail bundle green; whole-project `make verify` re-run after
  implementation (green on the current tree this session; this plan's code is not built yet).
- Blocked (device): real reboot survival, Doze survival over hours, specific OEM killers (e.g. MIUI) —
  physical/emulated devices + time; on-device QA, not here.
