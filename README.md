# SpeechAngel

[![CI](https://github.com/sicambria/speechangel/actions/workflows/ci.yml/badge.svg?branch=phase012-eval-and-app-layer)](https://github.com/sicambria/speechangel/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Android minSdk 26](https://img.shields.io/badge/minSdk-26_(Android_8)-brightgreen.svg)](https://developer.android.com/about/versions/oreo)
[![Kotlin 2.0](https://img.shields.io/badge/Kotlin-2.0.21-7F52FF.svg?logo=kotlin&logoColor=white)](https://kotlinlang.org)
[![On-device only](https://img.shields.io/badge/on--device-no_cloud-important.svg)](https://github.com/sicambria/speechangel)

**On-device, trainable, *language-independent* voice control for Android — built for people who cannot use their hands and whose speech may be atypical (stroke, illness, dysarthria).**

SpeechAngel recognises a small set of commands by matching the acoustic shape of **your own** recordings — no language model, no cloud, no phonemes. You teach it a few examples of each command on the phone; it listens hands-free and performs a fixed device action for each. Because it matches your sounds rather than a language, it works for speech that no speech-to-text engine understands.

> Conceptual & technological research behind this design lives in [`research/`](research/). The recognizer approach (speaker-dependent acoustic template matching, "Path C") is the language-independent core; see `research/01_conceptual_findings.md`.

---

## Status

| Area | State |
|---|---|
| Recognizer core (MFCC · energy-VAD · length-normalised DTW · multi-template matcher) | ✅ implemented, **JVM unit-tested** (incl. end-to-end command discrimination) |
| Persistence (Room), audio capture (AudioRecord), DI (Hilt) | ✅ implemented, builds |
| UX (Material 3 Compose: Home / Teach / Try) | ✅ implemented, builds |
| Always-on mic foreground service + deterministic AccessibilityService | ✅ implemented, builds |
| Debug APK | ✅ `:app:assembleDebug` green |
| On-device QA, instrumentation tests, threshold calibration (FRR/FAR), R8 | ⏳ requires a device/emulator — see `docs/ROADMAP.md` |

**Honesty note:** accuracy is engineered and must be reported as **FRR + FAR/hour**, never a bare "99%". >99% on a few-dozen distinct commands is realistic *in quiet*; it is a per-user, to-be-measured target, not a guarantee (see `research/`).

---

## Architecture

Multi-module, clean-architecture. The recognizer core is **pure Kotlin/JVM** so it is fast to test without a device.

```
:core:model        domain types (no deps)
:core:dsp          MFCC, FFT, mel filterbank, energy VAD          (pure Kotlin)
:core:matching     DTW + multi-template matcher (+ OOV reject)    (pure Kotlin)
:core:enrollment   Enroller + Recognizer + repository interfaces  (pure Kotlin)
:data              Room persistence, AudioRecord capture, Hilt DI (Android lib)
:app               Compose UX, ViewModels, services, Accessibility (Android app)
build-logic        Gradle convention plugins (DRY build config)
```

The always-on design follows the platform reality in `research/02_technological_findings.md` §T2: a `microphone` foreground service runs a two-stage listen loop; recognised commands are published on an in-process bus to a **deterministic** `AccessibilityService` (`isAccessibilityTool=true`) that performs one fixed action per command — *not* an autonomous agent (the Google Play 2026 policy line).

---

## Reproducible build

Pinned toolchain: **Gradle 8.14.3 · AGP 8.7.3 · Kotlin 2.0.21 · JDK 21 (Java 17 bytecode) · compileSdk 35 · minSdk 26.** No dynamic dependency versions (enforced by a guardrail); everything flows through `gradle/libs.versions.toml`.

```bash
make setup     # verify JDK 21 + Android SDK, write local.properties
make verify    # detekt + spotless + all unit tests + debug APK  (what CI runs)
make build     # debug APK
make test      # unit tests
make format    # auto-format (spotless)
make guardrails# AI-workflow guardrail verifiers
make help      # list all targets
```

Or directly: `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ANDROID_HOME=$HOME/Android/Sdk ./gradlew :app:assembleDebug`.

---

## Quality gates (automated, trackable)

- **Static analysis:** detekt (repo config + tuned thresholds) and Spotless/ktlint formatting.
- **Tests:** JVM unit tests across all core modules + data; coverage via Kover.
- **CI:** `.github/workflows/ci.yml` runs static analysis + tests + debug build + guardrails on every push/PR and uploads the APK.
- **AI-workflow guardrail system** (`scripts/`, `docs/`): the failure→known-error→rule→gate learning loop ported from the meta-system and adapted to Android — Android-specific verifiers (no dynamic versions, pinned wrapper, version-catalog usage, foreground-service-type sanity, secret scan), the incident/learning loop, the audit loop, and contracts-as-data. See `docs/meta/port-status.md` for honest wave-by-wave status and `AGENTS.md` / `docs/ai/START_HERE.md` to get oriented.

---

## Where to read next

- `docs/ROADMAP.md` — phased plan and the non-negotiable product gates.
- `docs/ai/START_HERE.md` — source-of-truth order for contributors/agents.
- `research/` — the conceptual + technological findings and the build/reuse rationale.

## License

AGPL-3.0. See `research/04_build_and_reuse_plan.md` §6 for the licensing rationale and third-party components.
