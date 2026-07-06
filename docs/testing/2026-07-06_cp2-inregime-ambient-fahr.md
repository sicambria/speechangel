# CP-2 in-regime ambient FA/hour — does the CP-1 embedding close the always-on wall?

**Date:** 2026-07-06 · **Bucket:** measure-only (off-device Python; ships nothing) · **Verdict:**
**the encoder does NOT close the CP-2 wall.** The CP-1 learned-embedding win (rank-1 55.4→71.9,
p=2×10⁻⁶ — CP-1 report: `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`) does **not auto-translate** to a
deployable always-on operating point. Rejection/threshold-calibration remains the binding CP-2 lever.

## Question

CP-1 measured discrimination on TORGO's per-utterance OOV FAR — *not* the axis that kills always-on.
The binding axis is **false-fires per hour of continuous ambient audio**. In the product regime
(a speaker enrolls their *own* words as the wake vocabulary), at a near-zero FA/hr, does the WavLM
embedding detect materially more of the user's held-out words than MFCC-DTW — i.e. does CP-1's better
separability move the **FA/hr** operating point toward a shippable one (**FRR < 5% at FA/hr ≤ 0.5**)?

## Protocol (`scripts/eval/ssl_frontend_spike/in_regime.py`, `inregime_paired.py`)

Product-regime, speaker-dependent, **no cross-speaker confound** (unlike the Picovoice cross-speaker
lower bound):

- **Enroll** a TORGO speaker's own repeated words as an open-set wake **gate**: fire ⇔ min-distance to
  ANY enrolled template < global threshold (Stage-1 gate; command identity is the downstream job).
- **Detection (positives):** leave-one-out over the speaker's own utterances.
- **FA/hr:** scan **1.01 h of real LibriSpeech background** (6067 windows, 1 s refractory-merged
  events) against the enrolled templates.
- **Both arms identical:** every template, positive, and background window is `energy_vad_trim`'d, then
  feature → min-distance (MFCC-DTW vs WavLM-L12 mean-pooled cosine). Only feature+distance differ →
  any delta is attributable to the representation (no EVAL-004 asymmetry).
- **Significance (EVAL-003):** paired McNemar (continuity-corrected) **and** exact two-sided binomial on
  the discordant detected/missed pairs, at each arm's own ~0-FA/hr operating threshold.

## Results — 1.01 h background, both speakers

| Speaker (n pos) | Arm | det @ ~0 FA/hr (FRR) | det @ 5 FA/hr | FA/hr for 95% det |
|---|---|---:|---:|---:|
| **F01** (32, dysarthric) | MFCC-DTW | 68.8% (31.2%) | 87.5% | 23.9 |
| | **WavLM-L12** | 75.0% (25.0%) | 96.9% | 5.0 |
| **FC01** (34, control) | MFCC-DTW | 64.7% (35.3%) | 100.0% | 3.0 |
| | **WavLM-L12** | 70.6% (29.4%) | 70.6% | 6.0 |

**Paired significance at ~0 FA/hr (the primary DoD metric):**

| Speaker | MFCC → WavLM det | discordant (mfcc-only / ssl-only) | McNemar p | exact-binom p |
|---|---|---|---:|---:|
| F01 | 68.8% → 75.0% | b=1 / c=3 | 0.617 | 0.625 |
| FC01 | 64.7% → 70.6% | b=1 / c=3 | 0.617 | 0.625 |

Both speakers show the **identical** discordant pattern (b=1/c=3): a +2-net-utterance move in the
embedding's favour, n.s. at n≈32–34. Consistent direction, underpowered — not demonstrated.

## What is banked

1. **No arm clears the deployable bar — the headline, and it does not depend on the small delta.**
   The best case is **WavLM F01 = FRR 25% at FA/hr ≤ 0.5** (product needs FRR < 5%). This is
   *conservative*: the background is clean LibriSpeech with **no DEMAND additive noise** — under real
   ambient noise the wall is worse. **CP-1's "rejection still binding" holds on the ambient-FA axis:
   a better encoder does not close CP-2.**

2. **The ~0-FA/hr lift is a consistent direction but underpowered — NOT demonstrated.** Both speakers
   move the same way (+6.2 / +5.9 pts), but F01's is a **2-utterance** move (b=1/c=3) at p≈0.62 — i.e.
   indistinguishable from noise at n≈32, *not* evidence of no effect. Not banked as a win. Chasing
   significance with more speakers (F03/F04/FC02/FC03) on a ~6-pt n.s. delta while far below the bar is
   suboptimization (per `/goal`) — n=2 already answers the strategic question: **the encoder alone is
   insufficient.**

3. **The dramatic F01 tail compression does NOT generalize — retracted.** F01's ~5× tail gain
   (24→5 FA/hr for 95% det) looked robust, but FC01 shows a **tail regression** (det@5FA/hr 100%→70.6%;
   95% det 3.0→6.0 FA/hr). "FA/hr for 95% det" is pinned by the 1–2 hardest positives out of ~32 — as
   knife-edge as the ~0-FA/hr point, not low-variance. **No bankable tail effect in either direction.**

## The reframe (updated) and the next lever

- **In-regime ≫ cross-speaker — stands.** In-regime MFCC (68.8% det @ ~0 FA/hr) vastly beats the
  cross-speaker Picovoice lower bound (40%). The committed "~82 FA/hr / no viable point" was
  **substantially a cross-speaker-benchmark artifact**; the real in-regime wall is far lower — but real.
- **The in-regime wall is discrimination-bound, and the embedding carries *recoverable* headroom MFCC
  lacks.** MFCC: rank-1 68.8% = gate@~0FA/hr 68.8% → **zero slack** (every correctly-ranked positive
  already passes the global threshold; nothing to recover). WavLM: rank-1 **84.4%** vs gate **75.0%** →
  a **9-pt gap** of positives that are rank-1-correct but whose *absolute* distance exceeds the
  background-calibrated **global** threshold.
- **⇒ Next CP-2 lever (hypothesis to spike, not established): per-template / per-word threshold
  calibration or a dedicated rejection model — NOT a better encoder and NOT more speakers.** Only the
  embedding has headroom for calibration to recover; that is where the next spike should look.

## Honesty / scope

- Absolute detection is speaker-dependent in-regime (the intended product regime), not the cross-speaker
  lower bound; FA/hr is regime-independent.
- Clean LibriSpeech background (no DEMAND) ⇒ the "wall not cleared" conclusion is conservative.
- This spike does **not** touch CP-1: rank-1 55.4→71.9 (p=2×10⁻⁶) stands. It shows only that CP-1's gain
  does not *auto-translate* to the ambient gate — the tempered CP-2 result is **not** "the embedding
  didn't pan out."
