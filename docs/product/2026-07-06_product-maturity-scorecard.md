<!-- Product maturity scorecard. Standing doc; indexed in docs/DOC_TOC.md. -->
# SpeechAngel — Product Maturity Scorecard

**Date:** 2026-07-06 · **Score: 442 / 1000** · **Stage: pre-alpha (exceptionally engineered)**

This scores the **product** — does it deliver validated value to its target users (immobilised,
speech-atypical people)? — not the development framework. The AI-framework maturity is a separate
`/1000` axis at 555 (`docs/standards/ai-framework-maturity-standard.md`); do not conflate the two.
The methodology, the ground-truth evidence, and every dimension below are stated so the number is
reproducible and defensible, not a vibe.

---

## 1. Headline

SpeechAngel is a **genuinely-built, end-to-end-wired, unusually-well-engineered pre-alpha whose
entire value proposition is still unproven.** The recognizer pipeline is real (not scaffolding); the
app is wired mic-to-action; the engineering hygiene is world-class. But the one hypothesis the whole
product rests on — *that speaker-dependent MFCC-DTW template matching hits an acceptable FRR/FAR on
atypical/dysarthric speech* — **has never been measured**, and the app **has never run on a real
device or emulator against real audio.** A green `:app:assembleDebug` is not evidence that it works.

The score is dominated by that gap on purpose. A product's maturity is dominated by delivered,
validated user value, and here that value is *unknown*. Everything that would prove it is still ahead.

---

## 2. Stage placement (the ladder the number hangs on)

| Stage | Gate | SpeechAngel |
|---|---|---|
| PoC | core idea shown in isolation | passed |
| Prototype | components built | passed |
| **Pre-alpha** | **full system built + wired, unit-tested, but unvalidated end-to-end in the real world** | **← here** |
| Alpha | runs on a device; internal dogfooding; known-incomplete | **not yet — never run on device** |
| Beta | real target users; accuracy measured; robustness survives the field | not yet |
| GA | shipped + validated + supported | not yet |

Empirical validation is the wall between pre-alpha and alpha, and nothing has crossed it. That caps
the score well under 500 regardless of how good the code is.

---

## 3. Scorecard (weighted; value/validation dominates, hygiene is capped)

| # | Dimension | Weight | Score | Basis |
|---|---|---:|---:|---|
| 1 | **Validated user value** — does it work, for these users, measured? | 300 | **25** | Zero real-voice measurement. FRR/FAR harness (`core:eval`) is real but its only corpus is `SyntheticCorpus`, banner-marked `SYNTHETIC — NOT the real measurement`. The target population (dysarthric speech) is exactly where the acoustic approach is least certain — and untested. |
| 2 | **Core recognizer built & correct** | 180 | **150** | Real: MFCC front-end (`MfccExtractor.kt:1`, ~250 L, full standard pipeline), length-normalised DTW + Sakoe–Chiba (`Dtw.kt`), multi-template min-distance + OOV reject (`TemplateMatcher.kt`), enroll/adapt logic. Docked: Δ/ΔΔ shipped **off** (`deltaOrder = NONE`) and QbE enhancement dormant, so the *shipped* config is the simplest, least-tuned variant. |
| 3 | **On-device & real-world validation** | 150 | **30** | The runtime — mic streaming, VAD gating, wake window, action dispatch, latency, CPU/battery, always-on survival (Doze / OEM task-kill / reboot) — is **entirely unexercised**. No instrumented/`androidTest` at all. Always-on survival is the historical graveyard of Android assistants; here it is 100% unverified on hardware. |
| 4 | **UX completeness & accessibility fit** | 120 | **72** | 8 Compose screens, navigable, VM-backed, AAA-color design system, caregiver wizard. But zero on-device visual QA, zero usability testing with an actual disabled user or caregiver, and one functional stub (`DictationScreen` → Noop backend). Designed-for-accessibility, not validated-as-accessible. |
| 5 | **Release & distribution readiness** | 100 | **25** | R8 + `:app:assembleRelease` green, fastlane + F-Droid metadata, `docs/release/RELEASE.md`. But no signing key, no Play/F-Droid accounts, no Permission Declaration submitted, no privacy policy live. Nobody can install this. |
| 6 | **Engineering process & hygiene** *(velocity multiplier — capped so it can't substitute for validation)* | 100 | **92** | Exceptional: reproducible pinned toolchain, version-catalog + no-dynamic-version gates, 10 guardrail verifiers, incident/learning loop, 105 real `@Test` / 244 assertions, honest status discipline. Capped at 100 by design. |
| 7 | **Documentation honesty & self-awareness** | 50 | **48** | Rare strength. The project marks synthetic data as synthetic, refuses to fabricate FRR/FAR, labels dormant seams, and its own gap analysis concedes the QbE/acoustic core "may handle severe distortion worse." It knows what it hasn't proven. |
| | **Total** | **1000** | **442** | Pre-alpha. |

---

## 4. Gap register — moderate or larger, by *type* (not by the roadmap's "blocked-on-asset" framing)

The roadmap frames the core gaps reassuringly as "blocked on an external asset" — i.e. procurement.
That framing hides the real risk: **no asset acquisition fixes a wrong hypothesis.** Gaps are split
by what actually retires them.

### A. Existential / unvalidated-hypothesis — these could sink the product; no purchase fixes them

- **A1 — The core accuracy hypothesis is unmeasured (CRITICAL, #1).** Whether MFCC-DTW template
  matching achieves a usable FRR/FAR *on atypical/dysarthric speech* is the entire bet, and there is
  **zero** real-voice evidence. The project's own `research/03_candidate_gap_analysis.md` §B5 flags
  the acoustic core as uncertain for severe distortion. Until a real number exists, product value is
  unknown. **Everything else is secondary to this.**
- **A2 — Never run on a device, end to end.** `:app:assembleDebug` green ≠ working. The full
  real-time loop (`ListeningService` → `WakeGatedRecognizer` → `CommandActionBus` →
  `SpeechAngelAccessibilityService`) has never executed against real audio on real hardware. Latency,
  wake-window behavior, false-fire rate, and CPU cost are all unobserved.
- **A3 — Always-on survival is unproven.** Doze, OEM task-killers, and reboot survival are where
  "always-on hands-free" apps die. All the logic (`BatteryOptimization`, `OemAutostart`,
  `BootReceiver`, `AssistantRole`) is built and unit-tested, but **none is validated on a device**.
  If the service dies silently after 20 minutes, the product fails its core promise no matter how
  accurate the matcher.

### B. Procurement / external-asset-blocked — real, but a lookup-and-acquire, not a research risk

- **B1 — No labeled dysarthric-inclusive corpus.** Blocks A1, threshold calibration, the front-end
  bake-off winner, and far-field gains. **TORGO** is freely downloadable and the lowest-barrier
  option; SAP is the best command-fit but carries DUA lead time. (Runbook:
  `docs/plans/2026-06/external-asset-acquisition.md`.)
- **B2 — No trained QbE encoder.** The milder-impairment few-shot enhancement is a dormant seam
  (`NoopQbeEncoder`); it needs a self-trained ~24k-param encoder. Enhancement, not core — low urgency.
- **B3 — No distribution path.** No signing key, no store accounts, no Permission Declaration. Blocks
  any real user reaching the app.

### C. Execution-remaining — known work, no external blocker

- **C1 — Δ/ΔΔ features are off by default (`deltaOrder = NONE`).** The cheapest accuracy lever ships
  disabled, pending a corpus to tune against. *(Note: the delta code itself is correct — it correctly
  concatenates, deliberately avoiding the upstream "LIVE BUG #1" it is named after. Not a defect.)*
- **C2 — No instrumented/`androidTest` suite.** Needed to make A2/A3 validation repeatable rather
  than a one-off manual pass. Moderate.
- **C3 — Dictation screen is a functional stub** (Noop backend, "isn't available in this build yet").
  Minor; off the command path.
- **C4 — CI never observed green on a real GitHub Actions run.** Minor.
- **C5 — No usability validation with an actual target user or caregiver.** Moderate — the "10-year-
  old-easy" UX claim is unverified with the people it is for.

---

## 5. What the score says to do next (feeds the roadmap update)

The single highest-leverage move is to **retire A1 as cheaply as possible**: pull **TORGO** (free,
~a day), run the existing `core:eval` harness on it, and produce the *first real FRR/FAR number*.
That one action kills the `SYNTHETIC` banner, converts the core hypothesis from faith to data, and
tells you whether the rest of the roadmap is even worth executing. It is the critical path.

Second: run the app **on the emulator/device once, end to end** (A2) — the `make emulator` +
install/launch path already exists — and watch the loop actually fire. Third: a minimal on-device
always-on survival soak (A3).

Nothing on the Phase-3 enhancement list (QbE, far-field, packs polish, dictation) should jump ahead
of A1–A3. Enhancements to an unvalidated core are premature.

---

## 6. Method & honesty notes

- **Ground truth:** dimension scores rest on a direct code inventory (pipeline classes, Noop seams,
  screen wiring, test counts) cross-checked to `path:line`, not on the roadmap's status lines.
- **The number is a placement, not an average of vibes:** it falls out of the pre-alpha stage gate
  (§2) plus the weighted table (§3), with validation weighted to dominate and hygiene capped so
  excellent process cannot masquerade as product maturity.
- **Re-score trigger:** the first real FRR/FAR (A1) and the first successful on-device run (A2) are
  each worth a re-score — they are the two events that move the stage from pre-alpha to alpha.
