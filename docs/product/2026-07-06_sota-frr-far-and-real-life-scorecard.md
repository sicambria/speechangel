<!-- SOTA FRR/FAR path + real-life factor scorecard. Standing doc; index in docs/DOC_TOC.md. -->
# SpeechAngel — Path to SOTA FRR/FAR + Real-Life Factor Scorecard

**Date:** 2026-07-06 · **Overall real-life score: 480 / 1000** · **Stage: early-alpha (measured, not yet deployable)**

Two deliverables in one document, per request:

1. **Part A — How to achieve truly exceptional, state-of-the-art FRR/FAR** on this product's actual
   problem (speaker-dependent, language-independent, on-device command spotting for atypical/dysarthric
   speech), ordered by leverage and grounded in what we now *measure*, not what we assume.
2. **Part B/C — A 0–1000 score on all relevant real-life factors**, with an explicit map of **where we
   are at/near state-of-the-art and where we are not.**

Both rest on the first real numbers this project produced (`docs/testing/2026-07-06_frr-far-torgo.md`,
`docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`). This supersedes the
442/1000 pre-alpha scorecard (`docs/product/2026-07-06_product-maturity-scorecard.md`), whose two
re-score triggers — first real FRR/FAR and first on-device run — have both now fired.

---

## 0. The honest baseline we are starting from

Every SOTA discussion has to anchor on the real, held-out, matched-FAR numbers — not a target.

| Metric | Shipped static front-end, held-out | SOTA reference (2024–2026) | Gap |
|---|---:|---|---:|
| **Closed-set rank-1** (dysarthric, deployment slice) | ~60–69% | personalized dysarthric ASR/KWS: 85–95%+ | large |
| **Open-set FRR @ FAR≤5%/utt** (dysarthric) | **75.7%** | few-shot KWS on typical speech: 3–10% FRR | very large |
| **Open-set FRR @ FAR≤5%/utt** (control/typical) | **61.9%** | commercial KWS: <5% | very large |
| **Always-on ambient false-accepts** | **~82 FA/hr** (optimistic proxy) | commercial wake word: **≤0.1–1 FA/hr** | **~100–800×** |
| Rank-1 vs chance | 10–40× chance (real signal) | — | hypothesis holds |

**Read this honestly:** the recognizer extracts real, well-above-chance signal (the core MFCC-DTW
hypothesis is *alive*), but at every deployable operating point it is **one to three orders of magnitude
from SOTA**. The single most damning number is ambient FAR: an always-on assistant that false-fires ~82
times/hour is unusable regardless of how good its FRR is. **That is the number SOTA work must attack
first.**

---

## Part A — How to achieve truly exceptional FRR/FAR

The gap decomposes into **three independent problems**, each with a different SOTA lever. Ordered by
leverage-per-effort *for this product*.

### A0. The framing that makes the rest tractable: separate the three problems

1. **Discrimination** (closed-set): pick the right command given that one was spoken. Today rank-1
   55–75%.
2. **Verification / rejection** (open-set): decide *whether* a command was spoken at all. This is where
   ~34 points are lost — the argmin is right but the threshold throws it away to hold FAR
   (`…frr-far-torgo.md` §D2).
3. **Always-on gating** (continuous stream): reject 3600 s/hr of TV, speech, and noise while staying
   awake. Today ~82 FA/hr — the true product-killer.

SOTA is a *different technique per problem*. Conflating them is why single-lever attempts (per-command
calibration D1, common-mode rejection H1) keep returning honest negatives.

### A1. Learned few-shot embeddings (QbE) — the single biggest discrimination + verification lever

MFCC-DTW is a 1980s–2000s technique. Modern SOTA few-shot keyword spotting replaces the hand-crafted
front-end + elastic-distance matcher with a **learned encoder** producing fixed-length embeddings, then
does nearest-prototype in embedding space:

- **Self-supervised speech representations** (wav2vec2 / HuBERT / WavLM) fine-tuned or used frozen as
  the front-end are the current backbone of low-resource and atypical-speech recognition. They encode
  phonetic structure far more robustly than MFCC, *and they transfer to dysarthric speech* better than
  MFCC because they were pretrained on thousands of hours.
- **Metric-learning / prototypical networks** (the arXiv 2403.07802 ~24k-param on-device encoder the
  roadmap already targets) give few-shot cosine prototypes that beat DTW-on-MFCC at equal enrollment
  count — this is the dormant `QbeEncoder`/`QbeSpeechBackend` seam.
- **Why it helps verification too:** a discriminative embedding space makes true-vs-OOV separable by a
  *margin*, so the accept/reject threshold stops throwing away 34 points. The embedding is the lever
  that moves both problem 1 and problem 2 at once.

**Concrete path:** train the 24k-param encoder on MSWC + Google Speech Commands (both CC-BY-4.0,
bundleable), keep MFCC-DTW as the cold-start/1-shot fallback, and A/B it on real corpora at matched FAR.
This is the highest-ceiling lever and the one most aligned with the roadmap's own Phase-3 bet.

### A2. Kill the always-on FAR with a cascade + a real wake stage (the deployability gate)

82 FA/hr → ≤0.5 FA/hr is a **~160×** reduction. No single threshold does this; SOTA always-on systems
use a **cascade**:

1. **Stage-0 VAD** (already built: `StreamingEnergyGate`) — drop silence for free.
2. **Stage-1 tiny always-on wake word** — a dedicated, personalized wake template (`WakeWordGate` is
   built) or a microWakeWord-class tiny CNN, tuned to ≤1 FA/hr *by itself*. Only audio past the wake
   gate reaches the expensive matcher. This is how commercial assistants hold FAR: the command matcher
   is **never** exposed to raw ambient audio.
3. **Stage-2 command verifier** with the A1 embedding + a **background/cohort (UBM) model** or an
   explicit "garbage" class so OOV audio scores low.
4. **SNR-adaptive thresholds** — raise the accept bar as measured noise floor rises (the sim proves
   noise is the dominant degrader, §A3).

The product's own two-stage architecture already anticipates this; what's missing is (a) a wake stage
tuned to a measured FA/hr and (b) a real continuous-ambient measurement (`-Dambient.wav` seam is built).
**Until Stage-1 holds ≤0.5 FA/hr on real ambient audio, no amount of Stage-2 accuracy ships.**

### A3. Noise robustness — multi-condition enrollment, not dereverberation

The realistic-condition harness settles an open question: **additive noise is the dominant degrader**
(rank-1 64.6%→34.1%→8.5% at 20/10/5 dB SNR), while reverb and telephone band-limiting are mild. So SOTA
effort should target noise:

- **Multi-condition enrollment / augmentation** — enroll (or augment enrolled templates) across
  SNR/room conditions so the matcher sees the deployment distribution. Cheapest robustness win; needs no
  new model. RIR (OpenSLR, Apache-2.0) + MUSAN noise convolution is the standard recipe.
- **SNR-adaptive operating point** (above).
- **Multi-mic beamforming** where hardware allows (out of scope for a single-mic phone MVP).
- **Deprioritize dereverberation** — the data says it's not the bottleneck.

### A4. Better rejection decision (the open-set lever, done right)

Two honest negatives (per-command calibration D1, common-mode H1) show naive threshold tricks don't
work. What the evidence points to:

- **`margin` (runner-up gap) is an unbanked lead** — directionally better than raw on *both* corpora
  (`…realistic-conditions…md` exploratory table), but it rode a higher FAR and was not pre-registered.
  The correct next step is a **fresh-data, FAR-matched, pre-registered McNemar test** (EVAL-003).
- **Cohort/UBM normalization done with a real background model** (not the per-trial own-command cohort
  that failed as H1) — a learned "is this speech-like garbage?" score.
- **Per-command calibration with a *global* fallback** instead of accept-all for commands with no
  training negatives (the documented D1 failure mode) — the natural fix that might make per-command
  competitive.

### A5. Speaker adaptation / continual learning (voice drift)

Dysarthric and fatigued speech drifts. SOTA personalized systems adapt online: the built
`decideAdaptation` (confirmation-gated, condition-aware pruning) is the mechanism; it needs a
voice-drift corpus to quantify the FRR-at-fixed-FAR benefit. Continual few-shot updating of prototypes
is a real 2–5 point lever on longitudinal use.

### A6. The lever above all levers: **real data**

None of A1–A5 can be *tuned or trusted* without labeled dysarthric-inclusive audio at scale:

- **Speech Accessibility Project (SAP)** — 959 speakers, has a "digital-assistant commands" category:
  the single best fit for command FRR/FAR tuning. DUA lead time is the real cost — **start now.**
- **UASpeech** (per-severity table), **TORGO** (already used — the only real corpus in hand),
  **EasyCall** (has an OOV split mirroring our FAR problem).

**Personalization is where SOTA dysarthric recognition actually lives** (Google Project Euphonia /
Relate reach usable accuracy with ~100s of per-user phrases). The product's speaker-dependent design is
*correct*; it is under-powered on enrollment count and starved of a corpus to tune the shared pieces
(encoder, thresholds, augmentation).

### A7. Sequenced program to "exceptional"

| Rank | Lever | Attacks | Ceiling | Cost | Blocker |
|---|---|---|---|---|---|
| 1 | Stage-1 wake cascade tuned to real ambient | FAR/hr | deployability gate | med | real ambient recording |
| 2 | QbE learned embedding | rank-1 + FRR | largest accuracy ceiling | high | train encoder + corpus |
| 3 | More enrolled templates / multi-condition enroll | rank-1 + noise | 5–15 pts | low | UX + augmentation |
| 4 | `margin` rejection (pre-registered, FAR-matched) | FRR@FAR | 2–8 pts | low | fresh holdout |
| 5 | SAP corpus acquisition | tunes 1–4, unblocks measurement | enables everything | low effort, long lead | DUA |
| 6 | Speaker adaptation | drift FRR | 2–5 pts longitudinal | med | drift corpus |

**Bottom line:** exceptional FRR/FAR is reachable, but it is a *learned-embedding + cascade + real-data*
program, not a threshold tweak. The current MFCC-DTW core is the right **cold-start fallback**, not the
SOTA endpoint.

---

## Part B — Where we are state-of-the-art, and where we are not

The product is a study in contrasts: **near-SOTA on the axes almost nobody optimizes, far from SOTA on
the accuracy axis everyone benchmarks.**

### At or near state-of-the-art

| Axis | Why it's near-SOTA |
|---|---|
| **Privacy / on-device** | 100% local, zero cloud calls anywhere in the pipeline (enforced by architecture + audits). This is *better* than most commercial assistants, which round-trip audio to the cloud. |
| **Language independence** | Genuinely rare: the recognizer is template/DTW (and future QbE), with **no ASR, no phonemes, no language model**. It works in any language the user speaks, including unwritten ones — a capability mainstream KWS lacks. |
| **Cold-start / few-shot** | Learns a command from **1 example**. SOTA KWS needs training data per keyword; this needs one recording. For the target population this is a real differentiator. |
| **Policy-safe deterministic action layer** | `isAccessibilityTool=true`, fixed command→action table, no LLM/autonomy in the loop — ahead of the 2026 Play policy curve by construction. |
| **Footprint** | Tiny: templates are short MFCC sequences in Room; no multi-hundred-MB model shipped. Runs on low-end hardware. |
| **Engineering honesty / measurement discipline** | Exceptional and genuinely rare: pre-registration, held-out FAR-matching (EVAL-002/003), refusal to claim gains from synthetic audio, honest negatives documented as deliverables. Most published KWS work is *less* rigorous about selection bias. |

### Not state-of-the-art

| Axis | Gap |
|---|---|
| **Raw FRR/FAR accuracy** | 1–3 orders of magnitude from SOTA (§0). MFCC-DTW vs learned embeddings is the core gap. |
| **Always-on ambient FAR** | ~82 FA/hr vs ≤0.1–1 commercial. The deployability blocker. |
| **Noise robustness** | Near-chance by 5 dB SNR; no multi-condition training or adaptive thresholding yet. |
| **Learned representations** | No SSL/embedding front-end; the QbE seam is dormant (needs a trained encoder). |
| **Dysarthric-specific accuracy** | Far below personalized-SSL SOTA (Euphonia-class), which the design *could* reach with data + encoder. |
| **Real-device latency / power / CPU** | **Unmeasured** — emulator has a silent mic; no physical-device numbers exist. SOTA claims require these. |
| **Field validation** | No real target-user or caregiver usability data; no continuous real ambient measurement. |

**One-line synthesis:** *SpeechAngel is at/near SOTA on privacy, language-independence, cold-start,
policy-safety, and measurement honesty — and roughly a decade behind SOTA on the accuracy and always-on
robustness axes, held back by (a) a hand-crafted front-end where the field has moved to learned
embeddings and (b) the absence of a real dysarthric corpus to tune against.*

---

## Part C — Real-life factor scorecard (0–1000)

Weighted so **delivered, measured user value dominates** and engineering hygiene is capped (it cannot
substitute for a working product). Same rubric family as the 442 scorecard, re-scored against the new
measured numbers and the landed simulation/rejection harness.

| # | Real-life factor | Weight | Score | Basis |
|---|---|---:|---:|---|
| 1 | **Validated user value** — does it work, for these users, *measured*? | 300 | **70** | Now **measured** on real TORGO (was unmeasured → +45 from knowledge de-risking). But the measurement says **not yet deployable**: FRR 76%/62% @ FAR≤5%, ambient ~82 FA/hr. Real signal (10–40× chance) keeps it well above the old 25, but the honest answer to "does it work" is still *no, at any deployable operating point*. |
| 2 | **Core recognizer built & correct** | 170 | **135** | Real, complete MFCC-DTW pipeline; now with a validated held-out eval, a realistic-condition sim harness, and rejection-scoring machinery. Docked harder than the engine alone would suggest: the **shipped** config is the least-tuned variant (threshold 8.0, Δ/ΔΔ off, noise-reduction off, empty per-command map), two rejection levers (D1 per-command, H1 common-mode) returned negatives, and QbE is dormant — so "built & correct" holds for the engine, not for a tuned operating point. |
| 3 | **On-device & real-world validation** | 150 | **50** | +20: emulator e2e proves the loop is wired (accessibility service bound, recognizer reactive) and always-on survives Doze + reboot-resume. Still no **real audio** on device → latency, CPU, false-fire, battery all unmeasured (silent emulator mic). No `androidTest`. |
| 4 | **Robustness & always-on survival** | 110 | **45** | Sim harness now *quantifies* the always-on gap (first FA/hr number) and proves noise is the dominant degrader — a real maturity gain. The Picovoice wake-word-benchmark (`docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`) adds the first FA/hr measurement on a **standard, citable** stream (LibriSpeech+DEMAND): confirms there is **no cross-speaker operating point that is both sensitive and quiet** (0.1 FA/hr ⇒ 87.5% miss) while closed-set rank-1 stays high (89.2%) — i.e. rejection/gating, not discrimination, is the wall. But the gap itself is large (~160× budget) and mitigations (wake cascade, adaptive threshold, OEM-kill survival) are unbuilt/unvalidated on hardware. |
| 5 | **UX completeness & accessibility fit** | 90 | **52** | 8 navigable Compose screens, caregiver wizard, AAA-color system, vocabulary-distinctness nudge; multi-template enrollment (1.5 s/recording, cap 5). No on-device visual QA, no real-user usability test, no enforced sample-count target, one functional stub (dictation). Designed-for, not validated-as, accessible. |
| 6 | **Privacy / language-independence / policy** *(near-SOTA differentiators)* | 60 | **54** | 100% on-device (no INTERNET permission, no telemetry); genuinely language-independent (no ASR/phonemes); deterministic policy-safe action layer; permissive-only licensing. The product's strongest, most SOTA-aligned axis — docked only because Play policy *submission* (declaration form, live privacy policy) is unbuilt (counted in factor 7). |
| 7 | **Release & distribution readiness** | 60 | **18** | R8/`assembleRelease` green, fastlane + F-Droid metadata. No signing key, no store accounts, no Permission Declaration, no live privacy policy. Nobody can install it. |
| 8 | **Engineering process & measurement honesty** *(velocity multiplier — capped)* | 60 | **56** | World-class and rare: pinned toolchain, guardrail bundle, pre-registration, EVAL-002/003, honest negatives as deliverables, incident loop. Capped so it can't mask product immaturity. |
| | **Total** | **1000** | **480** | **Early-alpha: measured, not yet deployable.** |

### Why 480 (and why it stays under the 500 wall)

The number is the **bottom-up component sum**, not a delta on the old 442 — the two scorecards use
different weight structures (this one splits engineering hygiene out and adds explicit privacy/policy and
robustness dimensions), so they are not directly additive. The 442 scorecard set a hard rule: empirical
validation is *"the wall between pre-alpha and alpha,"* capping the score **under 500** until real-world
value is demonstrated. Nothing has crossed that wall — factor 1 is still 70/300 and the product has still
never processed real audio on a real device — so 480 is deliberately kept below 500.

What moved it up from 442 is **measurement and validation maturity, not new capability**: the plan landed
this session refuted H1, so **no runtime change shipped**. But the core hypothesis is now **measured,
bounded, and shown not-yet-deployable** (factor 1: 25→70), the loop is proven wired on the emulator
(factor 3: 30→50), and the always-on gap is **quantified for the first time** via the new sim harness
(the new factor 4). Knowing precisely how far you are from SOTA — and having the harness to track it — is
real progress; it is not the same as being closer to it, which is why the value dimensions stay low.

### Re-score triggers (what moves this next)

- **Stage-1 wake cascade holding ≤0.5 FA/hr on a real ambient recording** → factor 4 jumps; first
  credible always-on claim. **Highest leverage.**
- **QbE encoder beating MFCC-DTW at matched FAR on a real corpus** → factor 1 & 2 jump; first SOTA-track
  accuracy gain.
- **Real-audio on-device run** (physical device: latency, CPU, false-fire) → factor 3 jumps; crosses
  into true alpha.
- **SAP corpus in hand** → unblocks tuning every accuracy lever; enables the first defensible
  SOTA-comparison numbers.

---

## Method & honesty notes

- Scores are a **placement** (early-alpha stage gate) plus a weighted table, not an average of vibes.
  Validation weighted to dominate; hygiene/privacy capped so they can't masquerade as product maturity.
- Every number traces to a committed report (`…frr-far-torgo.md`, `…realistic-conditions…md`) or the
  roadmap's verified code-state. No field far-field or real-ambient number is claimed — both remain
  Bucket B.
- SOTA references are directional (commercial wake-word FAR, few-shot KWS FRR, personalized dysarthric
  ASR) — order-of-magnitude anchors for *where the bar is*, not head-to-head benchmarks on identical
  data (which would themselves require the absent corpus). **The concrete, sourced bar** — Porcupine
  97.1% @ 0.1 FA/hr, openWakeWord <0.5 FA/hr / <5% FRR, Howl 10% FRR @ 4 FA/hr (production), PhonMatchNet
  29–33% FRR @ 1% FAR (zero-shot), LRDWWS'24 dysarthric FAR 0.32%/FRR 0.5% — plus SpeechAngel's placement
  in the 7-axis ranking (overall 59) lives in `docs/product/2026-07-06_sota-competitive-bar.md`, with the
  derived R-SOTA-1..6 roadmap items.
