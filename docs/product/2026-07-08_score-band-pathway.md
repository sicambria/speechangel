<!-- Score band pathway from current 480/1000 to SOTA-class 900+. Standing reference; index in docs/DOC_TOC.md. -->

# SpeechAngel — Score Band Pathway (480 → 900+)

**Date:** 2026-07-08 · **Current score: 480 / 1000** · Companion to
`docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md` (the 8-factor scorecard that
defines the scoring axes) and `docs/product/2026-07-06_sota-competitive-bar.md` (external SOTA
anchors).

This doc maps the **concrete milestones, roadmap items, and expected point contributions** needed
to push the product through each score band. Every milestone traces to an existing roadmap item
(R-SOTA-1..6, CP-0..3) or actionable lever (A1..A6 from the scorecard).

---

## Current state: 480/1000 — early-alpha, measured, not deployable

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

The score is hard-capped under 500 by rule until real-world value is demonstrated (factor 1 is
70/300, no real audio on a physical device, no deployable operating point).

---

## 480 → 600: Cross the deployability gate (+120)

The cheapest, highest-leverage wins. After this band: someone could actually install and run the
product, and the always-on false-fire rate is bounded.

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **Stage-1 wake cascade ≤0.5 FA/hr** on real ambient recording. Fix the ~82 FA/hr deployability blocker via threshold calibration + dedicated rejection model (CP-2 spike already proved MFCC gets ~65-69% detection at ~0 FA/hr in-regime; no arm clears the deployable bar yet — needs calibration, not a better encoder). | CP-2, R-SOTA-2 | F4 (45→80), F1 (70→80) | +45 |
| 2 | **Real-device audio metrics** (CP-3): physical device run with latency, CPU, battery drain, real false-fire rate. Crosses the emulator-silent-mic ceiling. | CP-3 | F3 (50→90) | +40 |
| 3 | **Release vehicle**: Play Console account + signing key + privacy policy published + Permission Declaration form filed. Nobody can install it today. | Phase-3 release items | F7 (18→40) | +22 |
| 4 | **Multi-template enrollment** (cap 5, 1.5 s/recording, already built) + **margin rejection pre-registered test** (A4: fresh-holdout, FAR-matched McNemar). | A4 lever, EVAL-003 | F1 (80→88), F2 (135→140) | +13 |
| | | | **Total** | **~600** |

**Projected scores at 600:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 88 | 140 | 90 | 80 | 52 | 54 | 40 | 56 | **600** |

---

## 600 → 700: Reach SOTA-track accuracy (+100)

The accuracy bet (learned encoder) is now *measured*, not aspirational. FRR drops from ~76% toward
the ~30-40% zone. The "is it a model problem" question is answered with constraint-preserving
evidence.

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **QbE learned encoder beats MFCC-DTW** at matched, held-out FAR on real dysarthric audio (CP-1). Distill the deep-SSL pooled-embedding ceiling (WavLM pooled-cosine 71.9% rank-1 vs MFCC-DTW 55.4%, McNemar p=2×10⁻⁶) into a ~1-2M param student — language-independence + 1-shot arbitrary-word enrollment preserved. Target: FRR ~30-40% at matched FAR, moving F1 meaningfully. | CP-1, R-SOTA-1 | F1 (88→155), F2 (140→158) | +85 |
| 2 | **CP-0 — SAP corpus in hand**: Speech Accessibility Project DUA cleared (long-lead; start immediately). Unblocks tuning every accuracy lever and enables first defensible SOTA-comparison numbers. | CP-0 | (enables #1 above) | — |
| 3 | **R-SOTA-6 — Multi-condition enrollment lands**: RIR + MUSAN augmentation on the condition grid. Rank-1 climbs back above 55% at 10 dB SNR. | R-SOTA-6 | F4 (80→85), F1 (155→160) | +10 |
| 4 | **R-SOTA-5 — Common Voice eval corpus** integrated; "10% FRR @ 4 FA/hr" (Howl production) set as the realistic milestone before the <5% stretch. | R-SOTA-5 | F3 (90→100) | +10 |
| 5 | **First real-user usability test** with caregivers and target users (qualitative data, not yet NPS). | Phase-1 UX exit | F5 (52→62) | +10 |
| | | | **Total** | **~715** |

**Projected scores at 700:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 160 | 158 | 100 | 85 | 62 | 55 | 42 | 56 | **718** |

---

## 700 → 800: Productionize and validate (+100)

First credible claim that the product *works* for the target population. The "experimental" label
starts coming off.

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **FRR approaching 10% at production FAR**: encoder + multi-condition templates + margin rejection + speaker adaptation combine. "10% FRR @ 4 FA/hr" (Howl bar) as a realistic milestone. Operating point tuned across all conditions, not just TORGO quiet. | CP-1, R-SOTA-1, A5 | F1 (160→210) | +50 |
| 2 | **Full on-device validation suite**: androidTest suite, JMH benchmarks (FFT/MFCC/DTW latency), battery drain per hour measured, Doze/OEM-kill survival on 3+ device models. | CP-3, Phase-3 perf items | F3 (100→130) | +30 |
| 3 | **Field validation**: consented, honestly-labelled experimental build deployed to 10-20 target users; real-world FRR/FAR telemetry flowing. | CP-0 extension | F1 (210→220), F3 (130→135) | +15 |
| 4 | **R-SOTA-4 — Dual-filter cascade**: length/second-opinion cross-verify at the decision layer as an FAR-cutting rejection stage (the `margin` lever, done right). | R-SOTA-4 | F4 (85→90) | +5 |
| 5 | **UX validated with target population**: usability tests with immobilised/speech-impaired users, caregiver workflow validated, vocabulary-distinctness nudge proven effective. | Phase-1 UX exit | F5 (62→75) | +13 |
| 6 | **Store listing + F-Droid metadata shippable**; release pipeline green end-to-end. | Phase-3 release items | F7 (42→50) | +8 |
| | | | **Total** | **~820** |

**Projected scores at 800:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 220 | 162 | 135 | 90 | 75 | 56 | 50 | 57 | **845** |

Note: the 800 band tightens because factor 2 (162/170), factor 6 (56/60), and factor 8 (57/60) are
nearing their ceilings — remaining gains must come from the heavy-weighted factors 1 and 3.

---

## 800 → 900+: SOTA-class (+100+)

The product is genuinely SOTA-class on its own axes — best-in-field on language-independence +
cold-start + privacy, *and* competitive on accuracy. The gap to closed-vocab commercial KWS is
closed on the axes that matter for this population.

| # | Milestone | Roadmap ref | Factors moved | ~Points |
|---|---|---|---|---|
| 1 | **FRR <5% at ≤0.5 FA/hr** (openWakeWord target); approaching Porcupine noise bar (~97% @ 10 dB SNR). The ZP-KWS "60% rel FRR reduction" fully realized. Dysarthric per-severity: ≥60% rank-1 severe, ≥75% moderate, ≥85% mild. | CP-1, R-SOTA-1, R-SOTA-6 | F1 (220→275) | +55 |
| 2 | **Always-on FAR ≤0.1 FA/hr** (Porcupine stretch target): dual-filter cascade fully deployed + SNR-adaptive thresholds + UBM/garbage model. Full Picovoice `wake-word-benchmark` protocol adopted as reporting standard. | R-SOTA-2, R-SOTA-3, R-SOTA-4 | F4 (90→105) | +15 |
| 3 | **Per-severity dysarthric accuracy tables** (UASpeech, SAP): measured, published, defensible. Speaker adaptation quantified longitudinally (drift FRR benefit measured in points). | CP-0, A5 | F1 (275→285), F2 (162→167) | +15 |
| 4 | **Production-hardened device metrics**: end-to-end latency <200 ms, battery <5%/hr active listening, sub-1% CPU when silent. 50+ device-model compatibility tested. | CP-3, Phase-3 perf | F3 (135→147) | +12 |
| 5 | **Polished accessible UX**: AAA-contrast validated by impairment type, caregiver wizard proven <10 min setup, voice feedback for blind users, real-user NPS measured. | Phase-3 UX items | F5 (75→86) | +11 |
| 6 | **GDPR/accessibility declaration filed, Play review passed, F-Droid published**, permissive-only license audit clean. | Phase-3 release items | F6 (56→59), F7 (50→58) | +11 |
| | | | **Total** | **~920** |

**Projected scores at 900+:**

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 285 | 167 | 147 | 105 | 86 | 59 | 58 | 59 | **966** |

At this ceiling, factor 1 (285/300) is genuinely SOTA-class for the product's constraint set,
factor 2 (167/170) is near-perfect, and factor 8 (59/60) reflects world-class engineering
discipline. The remaining ~34 points to a perfect 1000 are the irreducible gaps: nothing is 100%
in field-deployed accessibility software.

---

## The shape of the curve

```
480 ─ wake cascade + real device ─── 600 (deployability gate)
600 ─ QbE encoder + SAP corpus ───── 718 (SOTA-track accuracy)
718 ─ production FRR + field data ─── 845 (validated product)
845 ─ sub-5% FRR + full robustness ─ 966 (SOTA-class)
```

**The two biggest single-point jumps** are CP-2 (wake cascade, ~+45 at 600) and CP-1 (QbE encoder,
~+85 at 700). Together they account for >130 of the ~486 total gap. Everything else is compounding
marginal gains: more data, more templates, better thresholds, real-user feedback.

**The hardest band is 700→800** — once factors 2, 6, and 8 hit their ceilings, every remaining
point must come from measured user value (factor 1, heaviest at 300) and real-world validation
(factor 3). There is no substitute for real dysarthric-inclusive data and real-device numbers.

---

## Re-score triggers (from the scorecard, §"Re-score triggers")

In order of leverage:

1. **Stage-1 wake cascade ≤0.5 FA/hr** → factor 4 jumps; first credible always-on claim. 600 band.
2. **QbE encoder beating MFCC-DTW at matched FAR** → factor 1 & 2 jump; first SOTA-track accuracy. 700 band.
3. **Real-audio on-device run** (physical device: latency, CPU, false-fire) → factor 3 jumps. 600 band.
4. **SAP corpus in hand** → unblocks tuning every accuracy lever. Enables 700+ band.

---

## Method note

Scores are placements projected from the existing scored 8-factor framework
(`2026-07-06_sota-frr-far-and-real-life-scorecard.md`), not independent measurements. The same
capping rules apply: factors 6 and 8 are capped to prevent engineering hygiene from masquerading as
product maturity; factor 1 (user value) dominates at 300/1000. Projections are directional and will
firm up as each milestone's actual measured gain replaces the estimate.
