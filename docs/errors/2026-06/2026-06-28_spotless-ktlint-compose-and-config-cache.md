# Incident: spotless ktlint Compose crash and config-cache partial format

- **Date:** 2026-06-28
- **Area:** BUILD
- **Trigger:** `spotlessApply` threw a ktlint AssertionError on a Compose file; later `spotlessCheck` failed on files a prior apply appeared to have formatted.
- **Status:** resolved
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (BUILD-002)
- **Automation Links:** .editorconfig

## Summary

Two coupled formatting issues. (1) `spotlessApply` aborted with a ktlint `AssertionError` ("found problem in TryScreen.kt") because ktlint's `function-naming` and `property-naming` standard rules fire (non-autocorrectably) on Jetpack Compose's PascalCase `@Composable` functions and theme `val`s. (2) After fixing that, a `spotlessApply` reported BUILD SUCCESSFUL in ~1s yet `spotlessCheck` later failed — the Gradle configuration cache had served a stale graph and the apply only partially ran, so several modules were never actually reformatted.

## Root Cause

(1) ktlint's default ruleset is hostile to Compose naming conventions and surfaces the violation as a hard crash through Spotless's glue. (2) Trusting a fast "BUILD SUCCESSFUL" from a configuration-cache-reusing `spotlessApply` instead of verifying with `spotlessCheck` — a green sub-command masked incomplete work.

## Rerun Analysis

- **Last command proved:** ktlint crashes on PascalCase composables; a full `spotlessApply` then `spotlessCheck` passes.
- **Failed phase:** formatting (apply crash, then check after partial apply).
- **Still unknown:** n/a.
- **Failure class:** tool-default-vs-framework-convention; trust-green-without-verify.
- **Smallest next probe:** `spotlessApply` then immediately `spotlessCheck` in one invocation.
- **Stop condition:** `detekt spotlessCheck` green across all modules.

## Prevention

Disabled the two offending ktlint rules for Kotlin in both the root Spotless config and `.editorconfig` (`function-naming`, `property-naming`, plus `no-wildcard-imports`). Standardised on running `spotlessApply` followed by `spotlessCheck` (the `make verify` and CI gate run `spotlessCheck`, which cannot be satisfied by a partial apply).

## Guardrail Updates

- `.editorconfig` and the root Spotless `editorConfigOverride` disable `function-naming` / `property-naming` / `no-wildcard-imports`.
- app/src/main/kotlin/com/speechangel/app/ui/tryit/TryScreen.kt — the Compose file whose PascalCase composables triggered the original ktlint crash, now formatted clean.

## Planning Integration

ACTIVE_DEV_RULES BUILD-002 ("Compose-friendly ktlint config; always confirm formatting with `spotlessCheck`, never a bare `spotlessApply` exit code"). The CI workflow's `spotlessCheck` step is the Definition-of-Done enforcement.

## Shift-Left Decision

- **Tests:** skip — formatting is not unit-testable.
- **Guardrail/automation:** update — `.editorconfig` + root Spotless config; `spotlessCheck` already gates CI and `make verify`.

## Automation Follow-Up

`spotlessCheck` in CI is the standing automation. No additional script needed.
