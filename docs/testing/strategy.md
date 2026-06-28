# Test Strategy

The layered testing approach for SpeechAngel. Read this before touching tests.

---

## Layers

| Layer | Scope | Tooling | Where |
|---|---|---|---|
| **Unit (JVM)** | Pure logic: DSP math, DTW, thresholds, domain invariants | JUnit4 + Truth (+ MockK, Turbine, coroutines-test) | `core/*/src/test/kotlin` |
| **Robolectric** | Android-API logic without a device | Robolectric | module `src/test` (when Android deps land) |
| **Instrumentation** | On-device behavior (services, accessibility, mic) | androidx.test + Espresso, Compose UI test | `src/androidTest` (added when `:app`/`:data` land) |
| **Manual / device** | FRR + FAR/hour measurement on real (incl. dysarthric) voices | manual protocol | Phase 0 measurement |

The unit layer is where the matcher's correctness is won — DTW distance, per-command thresholds, and
the reject path are deterministic and must be fully unit-tested. **A mocked feature vector cannot
catch an MFCC concatenation bug** (the LIVE BUG #1 from `research/04_build_and_reuse_plan.md` §2:
concatenate static+Δ+ΔΔ, never sum) — keep a real-signal fixture test (`TestSignals.kt`).

---

## Selection rules

- **Default to a JVM unit test.** It is the cheapest and most of the IP (`core:*`) is pure Kotlin.
- **Robolectric** only when you need an Android API but not a device.
- **Instrumentation** for service lifecycle, foreground-service start, accessibility actions, mic
  capture — anything the emulator/device exercises that the JVM cannot.
- **Manual device measurement** for accuracy: report FRR + FAR/hour against the FAR budget
  (≤0.5 false accepts/hr), never a bare percentage.

---

## RED→GREEN

Write the failing test first where a test applies, watch it fail, then fix (`AGENTS.md` §4 step 5).
A fix without a test is an unguarded fix.

---

## Running tests

The four green core test tasks (see `CLAUDE.md` for the full JDK 21 / `ANDROID_HOME` invocation):

```
:core:model:test  :core:dsp:test  :core:matching:test  :core:enrollment:test
```

`:app` / `:data` assemble + instrumentation tests are wired into the pre-push gate once those
modules land (Wave 7 — "wire only what is green").

---

## Coverage

Kover aggregates core-module coverage with a ≥70 % line-coverage bound on core logic (root
`build.gradle.kts`). Coverage is a ratchet, not a vanity number — tie new coverage to behavior.
