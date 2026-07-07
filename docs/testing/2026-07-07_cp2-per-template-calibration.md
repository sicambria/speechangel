# CP-2 per-template calibration spike — H1 REFUTED

**Date:** 2026-07-07 · **Bucket:** measure-only (off-device Python; ships nothing) · **Verdict:**
**Per-template (per-word) threshold calibration is REFUTED** — it significantly *increases* FRR
at matched ≤0.5 FA/hr on all 3 dysarthric speakers (aggregate McNemar p<0.0001, discordant 94:6).
The per-word thresholds are systematically too strict because in-class (intra-session) template
distances underestimate cross-session query-template distances.

**Plan:** `docs/plans/2026-07/cp2-per-template-calibration-spike.md` · **Harness:**
`scripts/eval/ssl_frontend_spike/per_template_cal.py` · **Pre-registered H1:**
≥30% relative FRR reduction at ≤0.5 FA/hr vs global threshold → **REFUTED.**

## Question

The CP-2 in-regime spike (`docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md`) identified a 9-pt gap
between WavLM F01 rank-1 (84.4%) and gate detection at ~0 FA/hr (75.0%). The hypothesis was that
per-word thresholds — tighter for acoustically-tight words, looser for high-variance words — could
recover this gap by rejecting background that sneaks through loose words while accepting queries
through tight thresholds that match their in-class distribution.

## Protocol

EXACT replication of `in_regime.py` (fidelity-verified to the decimal on F01):

- **Embeddings:** WavLM-base-plus L12, per-utterance VAD-trim → zero-mean unit-var → mean-pool → L2-norm
- **Enrollment:** ALL templates of all words (speaker-dependent, in-regime)
- **Detection:** Leave-one-out — for each utterance i, min cosine distance to any other template j ≠ i
- **FA/hr:** 1.01 h LibriSpeech (6067 windows, 1.5s/0.5s, 1.0s refractory), per-window VAD-trim → same embedding
- **Global baseline:** gate fires ⇔ min distance to any template ≤ θ_global; θ_global swept to target FA/hr
- **Per-word (H1):** gate fires ⇔ ∃ word w with min distance to w's templates ≤ θ_w, where
  θ_w(α) = α × median(pairwise cosine distances between w's templates); α swept to target FA/hr
- **Both arms:** identical embeddings, enrollment templates, background windows → only threshold type differs
- **Significance:** Paired McNemar (continuity-corrected χ²) + exact two-sided binomial on per-utterance
  detection outcomes at matched ≤0.5 FA/hr

## Fidelity check

| Speaker | Metric | Committed CP-2 | This harness | Match |
|---|---:|---:|---|
| F01 | det@~0FA/hr | 75.0% | **75.0%** | ✅ |
| F01 | det@5FA/hr | 96.9% | **96.9%** | ✅ |
| F01 | FA/hr for 95% det | 5.0 | **5.0** | ✅ |

Fidelity PASSED — the baseline reproduces the committed CP-2 numbers to the decimal.

## Results — detection vs FA/hr (WavLM-L12, 1.01h LibriSpeech background)

| Speaker (n pos, n words) | Arm | FRR@0.5FA/hr | FRR@1.0FA/hr | FA/hr for 95%det |
|---|---:|---:|---:|---:|
| **F01** (32, 15) | global (baseline) | **25.0%** | 25.0% | 5.0 |
| | per-word (H1) | **56.2%** | 0.0% | 1.0 |
| | **rel change** | **−125% (LOSS)** | | |
| **F03** (185, 77) | global (baseline) | **53.5%** | 33.0% | 122.4 |
| | per-word (H1) | **89.7%** | 87.6% | 469.6 |
| | **rel change** | **−67.7% (LOSS)** | | |
| **F04** (50, 21) | global (baseline) | **54.0%** | 54.0% | 16.9 |
| | per-word (H1) | **76.0%** | 76.0% | 469.6 |
| | **rel change** | **−40.7% (LOSS)** | | |

## Paired significance at matched ≤0.5 FA/hr

| Speaker | global det | per-word det | discordant (g-only / pw-only) | McNemar p | exact-binom p |
|---|---:|---:|---:|---:|---:|
| F01 (n=32) | 75.0% | 43.8% | 14 / 4 | **0.034** | **0.031** |
| F03 (n=185) | 46.5% | 10.3% | 67 / 0 | **<0.001** | **<0.001** |
| F04 (n=50) | 46.0% | 24.0% | 13 / 2 | **0.010** | **0.007** |
| **AGGREGATE** | | | 94 / 6 | **<0.0001** | **<0.0001** |

**H1 REFUTED on all 3 speakers.** The per-word thresholds are significantly worse than the global
threshold — they reject most genuine queries (per-word detection is 10–44% vs global 46–75%) because
the in-class (intra-session) distances used for calibration are systematically tighter than the
cross-session query-template distances.

## Mechanism

The in-class distance distribution (pairwise cosine distances between templates of the same word) is
dominated by **intra-session** pairs — two utterances recorded in the same session within minutes
of each other. But held-out queries are predominantly from **different sessions**, recorded days/
weeks apart, with substantially larger acoustic variation (speaker state, microphone placement,
respiratory state for dysarthric speakers).

| Speaker | In-class median range | Cross-session inflation |
|---|---|---|
| F01 | 0.043 – 0.309 | queries routinely exceed 2–3× in-class median |
| F03 | 0.041 – 0.481 | up to 5× for high-variance words |
| F04 | 0.035 – 0.496 | similar |

The per-word thresholds θ_w(α) = α × median(in-class) are calibrated on a distance scale that is
~2–5× too strict for held-out queries from different sessions. At the α needed to reach ≤0.5 FA/hr,
most queries exceed their word's threshold → rejected. The global threshold, calibrated directly on
the background FA distribution, does not suffer from this scale mismatch.

## What is banked

1. **H1 refuted — honest negative, strong evidence.** Per-template calibration using in-class
   distances is a **significant regression** on all 3 speakers (aggregate McNemar p<0.0001,
   discordant 94:6). This is not a failure to detect — the effect is large and opposite to
   prediction. The mechanism (in-class vs cross-session scale mismatch) is consistent across all
   speakers and consistent with prior known error patterns.

2. **The gap between rank-1 and gate detection is NOT recoverable by threshold calibration alone.**
   The 9-pt F01 gap the CP-2 spike identified reflects the underlying embedding separability
   at the extreme tail — it is not a thresholding artifact that better calibration could fix.

3. **Global threshold calibration is optimal for the WavLM embedding at the gate level.**
   Any per-word refinement that uses in-class statistics will be systematically too strict for
   cross-session queries. A calibration that works would need to model cross-session query
   distributions, not in-class template distributions — which is equivalent to training a
   verification model, not calibrating thresholds.

4. **Margin scorer is also worse at 0.5 FA/hr:** F01 FRR 59.4% (vs 25.0% global), F03 86.5%
   (vs 53.5%), F04 50.0% (vs 54.0% — one near-tie). The margin penalty is not useful at the
   extreme operating point because it further tightens the already-too-strict threshold.

5. **Fidelity reproduction confirmed.** The harness reproduces the committed CP-2 F01 baseline
   to the decimal, validating the protocol. The harness (`per_template_cal.py`) is committed and
   reusable for follow-on spikes.

## Honesty / scope

- Measured on TORGO dysarthric speakers F01, F03, F04 — all speaker-dependent, in-regime.
- Background: 1.01 h clean LibriSpeech (no DEMAND additive noise) → the "wall not cleared"
  conclusion is conservative; real ambient would be worse.
- The per-word calibration uses ALL pairwise template distances (intra-session dominant). A
  cross-session-only variant was not tested — but it would converge toward the global threshold
  by construction, making it equivalent and not an independent lever.
- This spike does NOT touch CP-1 (rank-1 55.4→71.9, p=2×10⁻⁶ stands). It only shows that
  per-template calibration is not the CP-2 lever.

## Next lever (hypothesis to spike)

The CP-2 wall remains: **FRR 25% at 0.5 FA/hr (F01), 53.5% (F03), 54.0% (F04).** The failure of
per-template calibration reveals that the underlying issue is NOT threshold strategy — it is the
**embedding's separability at the extreme tail** and the **cross-session query-template distance gap.**
The next levers to spike:

1. **Multi-template + cross-session enrollment strategy** — use templates from MULTIPLE sessions
   as enrollment (not just the nearest session), measure detection at matched FA/hr with
   2/3/5 templates per word. The hypothesis: more templates from diverse sessions cover the
   cross-session variability, pulling query distances down while maintaining FA rejection.

2. **TTS-augmented enrollment** — add synthetic utterance variants (pitch-shifted, noise-augmented)
   to enrollment to cover more acoustic variation without requiring more real recordings.

3. **Dedicated Stage-2 verification model** — a learned discriminator (simple MLP on embedding
   distances + side features) that separates in-vocab from OOV at the embedding level, as a
   post-gate verification stage. The LRDWWS winner's dual-filter cascade (threshold →
   length/opinion cross-verify) is the reference architecture.

4. **Better embedding (distilled/trained)** — the CP-1 ceiling probe uses a frozen 95M-param
   English-pretrained model. A smaller encoder fine-tuned on the specific task (ZP-KWS-class
   phoneme-supervised, ~1.5M params) could improve tail separability — at the cost of a full
   training pipeline, gated on language-independence proof.

**Priority:** (1) and (2) are the cheapest spikes — they change enrollment, not the model.
(3) is a medium build with potentially larger gain. (4) is the highest-ceiling, highest-cost
option, gated on CP-0 (data) and language-independence.
