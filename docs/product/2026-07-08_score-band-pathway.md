<!-- Code-only score band pathway. Standing reference. -->

# SpeechAngel — Score Band Pathway (480 → 900+), code-only

**Date:** 2026-07-08 · **Current score: 480 / 1000** · Companion to
`docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md`.

Code-specific milestones, roadmap items, and point contributions per band. Non-code tasks
(store accounts, DUA paperwork, usability studies, policy declarations) are excluded — factors 6
and 7 have inherently low code-only headroom as a result.

---

## Current state: 480/1000

| # | Factor | Weight | Score |
|---|---:|---:|
| 1 | Validated user value | 300 | 70 |
| 2 | Core recognizer built & correct | 170 | 135 |
| 3 | On-device & real-world validation | 150 | 50 |
| 4 | Robustness & always-on survival | 110 | 45 |
| 5 | UX completeness & accessibility fit | 90 | 52 |
| 6 | Privacy / language-independence / policy | 60 | 54 |
| 7 | Release & distribution readiness | 60 | 18 |
| 8 | Engineering process & measurement | 60 | 56 |
| | **Total** | **1000** | **480** |

---

## 480 → 600: Cross the deployability gate (+120)

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **Stage-1 wake cascade ≤0.5 FA/hr** on real ambient recording. Fix the ~82 FA/hr deployability blocker via threshold calibration + dedicated rejection model (CP-2 spike: MFCC gets ~65-69% detection at ~0 FA/hr in-regime; needs calibration, not a better encoder). | CP-2, R-SOTA-2 | F4 (45→80), F1 (70→80) | +45 |
| 2 | **Real-device audio metrics** (CP-3): measurement harness on physical device — latency, CPU, battery drain, false-fire rate. Crosses the emulator-silent-mic ceiling. | CP-3 | F3 (50→90) | +40 |
| 3 | **Multi-template enrollment** (cap 5, 1.5 s/recording, built) + **margin rejection pre-registered test** (A4: fresh-holdout, FAR-matched McNemar). | A4, EVAL-003 | F1 (80→88), F2 (135→140) | +13 |
| | | | **Total** | **~600** |

**Projected scores at 600:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 88 | 140 | 90 | 80 | 52 | 54 | 18 | 56 | **578** |

Note: code-only caps this band at ~578 — the ~22 points from store accounts / signing keys / privacy
policy (F7) are non-code and excluded.

---

## 600 → 700: Reach SOTA-track accuracy (+100)

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **QbE learned encoder beats MFCC-DTW** at matched, held-out FAR on real dysarthric audio (CP-1). Distill the deep-SSL pooled-embedding ceiling (WavLM pooled-cosine 71.9% rank-1 vs MFCC-DTW 55.4%, McNemar p=2×10⁻⁶) into a ~1-2M param student — language-independence + 1-shot arbitrary-word enrollment preserved. | CP-1, R-SOTA-1 | F1 (88→155), F2 (140→158) | +85 |
| 2 | **R-SOTA-6 — Multi-condition enrollment**: RIR + MUSAN augmentation on the condition grid. Rank-1 climbs back above 55% at 10 dB SNR. | R-SOTA-6 | F4 (80→85), F1 (155→160) | +10 |
| 3 | **R-SOTA-3 — Picovoice `wake-word-benchmark` protocol** adopted as reporting standard; folded into `core:eval` condition grid. | R-SOTA-3 | F3 (90→95), F8 (56→57) | +6 |
| 4 | **R-SOTA-5 — Common Voice eval corpus loader** integrated into `core:eval`; "10% FRR @ 4 FA/hr" (Howl) set as production milestone. | R-SOTA-5 | F3 (95→100) | +5 |
| | | | **Total** | **~680** |

Note: Common Voice integration is a corpus-loader code task, not the administrative SAP DUA.

**Projected scores at 700:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 160 | 158 | 100 | 85 | 52 | 54 | 18 | 57 | **684** |

---

## 700 → 800: Productionize and validate (+100)

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **FRR approaching 10% at production FAR**: encoder + multi-condition templates + margin rejection + speaker adaptation combine. Operating point tuned across all conditions, not just TORGO quiet. | CP-1, R-SOTA-1, A5 | F1 (160→210) | +50 |
| 2 | **Full on-device validation suite**: androidTest suite, JMH benchmarks (FFT/MFCC/DTW latency), battery drain per hour measured, Doze/OEM-kill survival on 3+ device models. | CP-3, Phase-3 perf | F3 (100→130) | +30 |
| 3 | **R-SOTA-4 — Dual-filter cascade**: length/second-opinion cross-verify at the decision layer as an FAR-cutting rejection stage. | R-SOTA-4 | F4 (85→90) | +5 |
| 4 | **Speaker adaptation quantified**: voice-drift corpus loaded, `decideAdaptation` loop exercised longitudinally, FRR-at-fixed-FAR benefit measured in points. | A5 | F1 (210→215), F2 (158→160) | +7 |
| | | | **Total** | **~775** |

**Projected scores at 800:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 215 | 160 | 130 | 90 | 52 | 54 | 18 | 57 | **776** |

Note: the 700→800 band flattens because factors 5 (UX studies), 6 (policy filings), and 7 (store
accounts) are non-code and frozen; factors 2 and 8 are near-ceiling. All remaining headroom is in
factors 1 (accuracy) and 3 (on-device measurement).

---

## 800 → 900+: SOTA-class (+100+)

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **FRR <5% at ≤0.5 FA/hr** (openWakeWord target); approaching Porcupine noise bar (~97% @ 10 dB SNR). ZP-KWS "60% rel FRR reduction" fully realized. Dysarthric per-severity: ≥60% rank-1 severe, ≥75% moderate, ≥85% mild. | CP-1, R-SOTA-1, R-SOTA-6 | F1 (215→270) | +55 |
| 2 | **Always-on FAR ≤0.1 FA/hr** (Porcupine stretch): dual-filter cascade fully deployed + SNR-adaptive thresholds + UBM/garbage model. Picovoice `wake-word-benchmark` fully integrated. | R-SOTA-2, R-SOTA-3, R-SOTA-4 | F4 (90→105) | +15 |
| 3 | **Per-severity dysarthric accuracy tables** (UASpeech corpus loader in `core:eval`): measured, reproducible, per-condition breakdown. | CP-0 (code half) | F1 (270→278), F2 (160→165) | +13 |
| 4 | **Production-hardened device metrics**: end-to-end latency <200 ms, battery <5%/hr active, sub-1% CPU silent. 50+ device-model compat tested. | CP-3, Phase-3 perf | F3 (130→145) | +15 |
| 5 | **Accessibility UX implementation**: AAA-contrast system proven by impairment type via automated contrast-audit tests, voice-feedback `AccessibilityDelegate` for blind users, vocabulary-distinctness nudge A/B-tested. | Phase-3 UX (code half) | F5 (52→68) | +16 |
| | | | **Total** | **~890** |

**Projected scores at 900+:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 278 | 165 | 145 | 105 | 68 | 54 | 18 | 57 | **890** |

Note: the code-only ceiling is ~890, not 966. The ~76-point gap to a perfect product score is
inherently non-code: Play Store listing, F-Droid publication, GDPR/policy declarations, signing
keys, real-user usability studies, caregiver field validation, and SAP DUA paperwork. These are
gating for actual deployment but are not code tasks.

---

## The shape of the curve (code-only)

```
480 ─ wake cascade + real device ─── 578 (deployability gate, code-only)
578 ─ QbE encoder + augmentation ─── 684 (SOTA-track accuracy)
684 ─ production FRR + device suite ─ 776 (validated product)
776 ─ sub-5% FRR + full robustness ─ 890 (code-only ceiling)
```

The two biggest single-point jumps are CP-2 (wake cascade, ~+45) and CP-1 (QbE encoder, ~+85).

**The hardest band is 700→800** — once factors 2, 6, 7, and 8 hit their ceilings, every point must
come from measured accuracy (factor 1) and device validation (factor 3).

**The ceiling at 890** is structural: factors 6 and 7 are frozen at near-baseline without store
accounts, legal filings, and policy declarations. Factor 5 (partly code) caps at ~68 without
real-user studies.

---

## Re-score triggers (code-only)

1. **Stage-1 wake cascade ≤0.5 FA/hr** → factor 4 jumps. 600 band.
2. **QbE encoder beating MFCC-DTW at matched FAR** → factor 1 & 2 jump. 700 band.
3. **Real-audio on-device run** (physical device: latency, CPU, false-fire) → factor 3 jumps. 600 band.

---

## Method note

Same 8-factor weighted framework from `2026-07-06_sota-frr-far-and-real-life-scorecard.md`.
Projections are directional. Factors 6 and 7 are held at baseline (54, 18) throughout because their
headroom is almost entirely non-code (store accounts, legal filings, policy declarations).
