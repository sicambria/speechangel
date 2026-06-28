# Incident: module bring-up compile gotchas

- **Date:** 2026-06-28
- **Area:** BUILD
- **Trigger:** A cluster of one-off compile failures while standing up the Gradle/Kotlin/Android modules.
- **Status:** resolved
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (BUILD-003)
- **Automation Links:** Makefile

## Summary

Six distinct compile-time failures hit during initial scaffolding, each caught by building the module standalone before wiring the next: (1) root `build.gradle.kts` registered a `clean` task that already exists; (2) `rootProject.libs` is not valid inside a `subprojects {}` block (capture catalog values in a `val` first); (3) Room 2.6.1's `fallbackToDestructiveMigration(dropAllTables = …)` overload does not exist (use the no-arg form); (4) a Compose `var x by mutableStateOf` generates `setX`, clashing with a hand-written `fun setX`; (5) Robolectric/JUnit rejected test methods whose expression body returned Truth's `Ordered` (`containsExactly`) instead of `Unit`; (6) `ApplicationProvider` needs an explicit `androidx.test:core` test dependency.

## Root Cause

Version- and API-specific surface mismatches between the pinned toolchain (AGP 8.7.3 / Room 2.6.1 / Kotlin 2.0.21 / Robolectric) and assumed-but-wrong API shapes — the meta doc's "audit version-coupled constants in vendored config" class, at the source level.

## Rerun Analysis

- **Last command proved:** each module compiles + tests green standalone after its fix.
- **Failed phase:** compilation of core / data / app at various points.
- **Still unknown:** n/a — all six fully resolved.
- **Failure class:** version-coupled-API-mismatch.
- **Smallest next probe:** build the single failing module (`:module:compileDebugKotlin` / `:module:test`).
- **Stop condition:** `make verify` green.

## Prevention

Each fix was validated by building the affected module in isolation before adding the next module (the meta doc's "wire only what exits 0" applied per module). This staged bring-up — encoded as the normal workflow — is what kept the failures cheap and localised rather than compounding into one opaque failure.

## Guardrail Updates

- app/src/main/kotlin/com/speechangel/app/MainActivity.kt — fix for the `mutableStateOf` setter / `fun setListening` JVM-signature clash.
- data/src/main/kotlin/com/speechangel/data/di/DataModule.kt — fix for the Room 2.6.1 `fallbackToDestructiveMigration` overload.
- core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/RecognizerTest.kt — tests that caught the Robolectric/Truth `void` return issue.
- The `Makefile` `verify` target runs the full gate so any regression of these is caught.

## Planning Integration

ACTIVE_DEV_RULES BUILD-003 ("bring up each Gradle module standalone — compile/test it green before wiring the next; never enable the whole graph blind"). This is the Definition of Done for adding a module.

## Shift-Left Decision

- **Tests:** add — the per-module unit tests added during bring-up (these caught #5 and #6).
- **Guardrail/automation:** skip — these are one-off, version-specific compile fixes; a bespoke static gate per item is not worth it. The staged-bring-up rule + `make verify` cover the class.

## Automation Follow-Up

Skip: no dedicated automation. The standing `make verify` / CI gate plus BUILD-003 are sufficient; revisit only if this failure class recurs.
