# Incident: host toolchain JDK and shell quirks

- **Date:** 2026-06-28
- **Area:** BUILD
- **Trigger:** First bash calls exited 1 on bare builtins; the host default JDK is 25 while AGP needs 17-21.
- **Status:** resolved
- **Guardrail Links:** docs/ai/ACTIVE_DEV_RULES.md (BUILD-001)
- **Automation Links:** scripts/setup/check-env.sh

## Summary

Two host-capability gaps surfaced before any code compiled. (1) The interactive shell fails on bare builtins (`echo`, `pwd`, `ls` exit 1); only absolute binary paths work (`/bin/ls`, `/usr/bin/git`). (2) The default JDK is 25, but Android Gradle Plugin 8.7 supports JDK 17-21 only — running Gradle on 25 is unsupported. JDK 21 is installed at `/usr/lib/jvm/java-21-openjdk-amd64`.

## Root Cause

Environment/host issues, not project bugs: a non-standard shell init, and a newer-than-supported default JDK. The meta-workflow doc (§0.5) predicts exactly this class — "a host-capability gap mistaken for a hard blocker" — and prescribes probing then capturing the working invocation.

## Rerun Analysis

- **Last command proved:** `/bin/ls <abs>` works; `JAVA_HOME=<jdk21> ./gradlew` builds.
- **Failed phase:** bare-builtin shell commands; Gradle on JDK 25.
- **Still unknown:** n/a — both fully diagnosed and worked around.
- **Failure class:** host-capability-gap.
- **Smallest next probe:** run any Gradle task with `JAVA_HOME` pinned to JDK 21.
- **Stop condition:** `make verify` is green.

## Prevention

The pinned invocation is captured so no future session rediscovers it: the `Makefile` hard-codes `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` (overridable), `scripts/setup/check-env.sh` verifies JDK 21 + the Android SDK and writes `local.properties`, and `CLAUDE.md` documents both the JDK pin and the absolute-path shell rule.

## Guardrail Updates

- scripts/setup/check-env.sh — fails fast if JDK 21 / Android SDK are missing.
- Makefile — pins JAVA_HOME/ANDROID_HOME for every target.
- CLAUDE.md — records the working Gradle invocation and the absolute-path shell quirk.

## Planning Integration

ACTIVE_DEV_RULES BUILD-001 ("always invoke Gradle through `make` or with JAVA_HOME pinned to JDK 21; never assume the default JDK"). `make setup` is the Definition of Done step for environment readiness.

## Shift-Left Decision

- **Tests:** skip — environment capability is not unit-testable; the precheck script covers it.
- **Guardrail/automation:** add — `scripts/setup/check-env.sh` as the Wave-0.5 precheck.

## Automation Follow-Up

`scripts/setup/check-env.sh` is the automation; CI uses `actions/setup-java@v4` with JDK 21 so the same pin holds remotely. No further work needed.
