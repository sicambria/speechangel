# Incident: shipped config untested by permissive test threshold

- **Date:** 2026-06-28
- **Area:** MATCH
- **Trigger:** Advisor review noticed the recognizer tests only proved discrimination, never acceptance.
- **Status:** resolved
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (MATCH-001)
- **Automation Links:** core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/RecognizerTest.kt

## Summary

`RecognizerTest` exercised the matcher with `MatcherConfig(defaultAcceptanceThreshold = 1000f)` and asserted only that the correct command had the smallest distance (discrimination). The app, however, ships `MatcherConfig()` with `defaultAcceptanceThreshold = 8.0f`. The green test suite therefore proved nothing about whether the *shipped* configuration would accept any real utterance — it could have rejected everything as `NoMatch(BELOW_CONFIDENCE)` and every test would still pass. A classic case of a passing test masking the actual ship-time failure mode.

## Root Cause

The test substituted a permissive stand-in value for a production constant to make assertions convenient, decoupling the test from the value the user actually runs. The acceptance threshold is the single most behaviour-defining constant in the matcher, and it had zero end-to-end coverage at its real value.

## Rerun Analysis

- **Last command proved:** discrimination (argmin selects the right command) on synthetic tones.
- **Failed phase:** acceptance at the shipped threshold — never executed.
- **Still unknown:** real-speech FRR/FAR at 8.0f (synthetic tones are not speech).
- **Failure class:** test-double-diverges-from-production-config.
- **Smallest next probe:** add one test running `Recognizer(..., TemplateMatcher())` (defaults) and assert `Match`.
- **Stop condition:** shipped-default test is green AND ROADMAP records real-audio calibration.

## Prevention

Added a test that constructs the recognizer with the **default** `TemplateMatcher()` and asserts a fresh enrolled take is accepted as a `Match` (not merely that it would win if accepted). This makes a rejecting default fail CI. Confirmed green: the 8.0f default does accept and correctly classify the tested signals.

## Guardrail Updates

- core/enrollment/src/test/kotlin/com/speechangel/core/enrollment/RecognizerTest.kt — new test `the shipped default config accepts a fresh take of an enrolled command`.
- docs/ai/ACTIVE_DEV_RULES.md — rule MATCH-001.

## Planning Integration

ACTIVE_DEV_RULES MATCH-001 ("any behaviour-defining default must have an end-to-end test at its shipped value"). `docs/ROADMAP.md` Phase 0 carries the real-audio FRR/FAR threshold calibration that this test cannot substitute for.

## Shift-Left Decision

- **Tests:** add — an end-to-end acceptance test at the shipped default config.
- **Guardrail/automation:** update — promoted ACTIVE_DEV_RULES MATCH-001; a static gate that asserts "every config default is referenced by a test" is possible but low-value now, so deferred to the rule + review.

## Automation Follow-Up

Real-audio threshold calibration (FRR + FAR/hour) is a Phase-0 measurement task in `docs/ROADMAP.md`; a calibration harness is the future automation. No further static gate added now.
