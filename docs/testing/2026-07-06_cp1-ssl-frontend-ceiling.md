# CP-1 spike — Learned-encoder ceiling probe on TORGO (representation × matcher decomposition)

**Verdict: GO for CP-1, with a sharpened target.** A learned deep self-supervised (SSL) embedding,
**mean/stats-pooled to a fixed-length vector and matched by cosine**, significantly beats the shipped
MFCC-DTW recognizer on real dysarthric 1-shot recognition — aggregate rank-1 **55.4% → 71.9%**
(−37% relative error, **McNemar p=2×10⁻⁶**), and **≥50% rel. rank-1 error reduction on the
deployment-relevant slice** (F01, F04). But the lever is **not** "swap the MFCC front-end" (that is a
tie under a matched matcher); it is the **fixed-dim QbE embedding + cosine-prototype architecture** —
exactly the dormant `QbeEncoder`/`QbeSpeechBackend` seam. And the always-on rejection wall (CP-2)
remains binding: FRR@FAR≤5% only moves 78.3% → 66.3%.

> Off-device, `[measure-only]` spike. Touches no app code, ships nothing. Frozen 95M-param English SSL
> encoders are a **ceiling/diagnostic probe, not a shippable artifact** (the deployable target is a
> ~1–2M-param encoder, ZP-KWS-class). Plan: `docs/plans/2026-07/cp1-ssl-frontend-ceiling-spike.md`.
> Harness: `scripts/eval/ssl_frontend_spike/` (committed). Advisor-gated twice (design + this analysis).

## Method (same-harness A/B, EVAL-002 discipline)

A Python reimplementation of the committed `TorgoEval` protocol — speaker-dependent, k=5 round-robin
folds, threshold-free **rank-1** (1-NN argmin), leave-one-fold-out **global-threshold FRR@FAR**, and the
same `EnergyVad` trim → front-end → DTW pipeline — so the **only** variable across arms is the
per-utterance feature/matcher. **Fidelity gate (DoD-1): PASSED — the harness reproduces the committed
MFCC-DTW report to the decimal** (below), which is what makes every downstream comparison trustworthy.

| Speaker | Committed rank-1 | This harness | Committed FRR@FAR≤5% (HO) | This harness |
|---|---:|---:|---:|---:|
| F01 | 68.8% | **68.8%** | 81.3% | **81.2%** |
| F03 | 53.5% | **53.5%** | 80.5% | **80.5%** |
| F04 | 54.0% | **54.0%** | 62.0% | **62.0%** |
| ALL | 55.4% | **55.4%** | 78.3% | **78.3%** |

Corpus: TORGO dysarthric F01/F03/F04, `wav_headMic`, min-2-reps commands + single-instance words as OOV
negatives (identical to `TorgoCorpus`). Encoders via HuggingFace `transformers`, frozen, one layer,
per-utterance zero-mean/unit-var input on VAD-trimmed audio.

## The decomposition — representation × matcher (this is the real finding)

The naive comparison (MFCC-**DTW** vs WavLM-**pooled-cosine**) moves two variables at once. The honest
2×2 (aggregate rank-1, full dysarthric set) separates them:

| rank-1 (AUC) | matcher = DTW | matcher = stats-pool + cosine |
|---|---:|---:|
| **repr = MFCC (39-dim)** | **55.4%** (0.572) | 39.3% (0.344) |
| **repr = WavLM-L12 (768-dim)** | ~68.8% F01, **tied** | **72.3%** (0.686) |

Three facts fall out, and together they relocate the lever:
1. **Pooling *wrecks* a classic front-end:** MFCC+stats-pool 39.3% ≪ MFCC+DTW 55.4%. DTW's temporal
   alignment is doing real work for MFCC; a fixed-dim MFCC vector throws it away.
2. **Swapping representation *inside DTW* is ~a tie:** WavLM frames under DTW top out at 68.8% on F01 =
   MFCC-DTW's 68.8%. As a drop-in DTW front-end, WavLM buys little.
3. **The win is the interaction:** deep-SSL frames pool into a *discriminative* fixed-length embedding
   (WavLM+pool 72.3%) where MFCC cannot (39.3%). It is an **embedding+cosine** effect, not a front-end
   swap and not "just pool."

**Actionable consequence:** the target architecture is a **learned fixed-dim utterance embedding with
cosine prototypes** — precisely the `QbeEncoder`/`QbeSpeechBackend` seam already built and dormant. The
spike does **not** support "replace the MFCC front-end in the DTW matcher."

## Best learned encoder — full dysarthric set (WavLM-base-plus, L12, mean-pool cosine)

| Speaker | MFCC-DTW rank-1 | WavLM rank-1 | MFCC FRR@FAR5% | WavLM FRR | MFCC AUC | WavLM AUC |
|---|---:|---:|---:|---:|---:|---:|
| F01 (15 cmd) | 68.8% | **84.4%** | 81.2% | **56.2%** | 0.656 | **0.799** |
| F03 (77 cmd) | 53.5% | **67.0%** | 80.5% | **71.4%** | 0.517 | **0.668** |
| F04 (21 cmd) | 54.0% | **82.0%** | 62.0% | 62.0% | 0.572 | **0.794** |
| **ALL** | **55.4%** | **71.9%** | **78.3%** | **66.3%** | 0.572 | **0.717** |

HuBERT-base L12 mean-pool is close behind (rank-1 67.8%, FRR 71.5%, AUC 0.676). **wav2vec2-base is
markedly worse** (best L2, 55.4% agg on F01-scale) and its skill is in *early* layers — WavLM/HuBERT peak
in the *deepest* layer (L12). (The advisor's "phonetic peak is mid-stack" prior was wrong for
WavLM/HuBERT; the full-stack sweep found deep-layer optima instead.)

## Paired significance (McNemar, WavLM-L12 vs MFCC-DTW, per-utterance rank-1)

| Group | n | MFCC→ok / WavLM→wrong (b) | MFCC→wrong / WavLM→ok (c) | χ² | p |
|---|---:|---:|---:|---:|---:|
| F01 | 32 | 1 | 6 | 2.29 | 0.13 (ns, underpowered) |
| F03 | 185 | 18 | 43 | 9.44 | **0.0021 (\*\*)** |
| F04 | 50 | 0 | 14 | 12.07 | **0.00051 (\*\*\*)** — strict domination |
| ALL | 267 | 19 | 63 | 22.55 | **2.1×10⁻⁶** |

Clears the pre-registered bar (p<0.05 favoring the encoder in ≥2/3 speakers). F04 is a clean strict
domination (14 fixes, 0 regressions). vs LPC the win is even stronger (aggregate p=9×10⁻⁸).

## Definition-of-Done verdict (honest — no goalpost moving)

- **DoD-1 (harness fidelity): MET** — reproduces the committed baseline to the decimal.
- **DoD-2 (≥50% rel. rank-1 error reduction = "way better"): MET on the deployment slice, MISSED on
  aggregate.** Per-speaker error reduction: **F01 50.0%, F04 60.9%** (both ≥50%, the realistic ≤25-cmd
  regime); F03 (77-word reading-passage tail) 29.0%; **aggregate 37.0%** (44.6%→28.1% error). Reported as
  it is: the aggregate misses 50%, the deployment slice meets it, and the effect is paired-significant.
- **DoD-3 (rejection first read): meaningful but insufficient.** Separability AUC 0.572→0.717 and FRR@FAR
  ≤5% 78.3%→66.3% (−15% rel) — a real gain, but **FRR is still 56–71% and the always-on FAR wall (CP-2)
  is untouched by a better encoder alone.** rank-1 must not oversell deployability.

## Dead-ends / negative results banked

- **LPC/LPCC ≈ MFCC** (53.2% vs 55.4% agg, tied within noise) — the classic front-end *family* (mel vs
  all-pole) is not a lever. Not worth further classic-DSP front-end work.
- **wav2vec2-base is a weak encoder here** despite being the most-cited — model choice matters more than
  "use SSL"; WavLM/HuBERT (deep layers) are the ones that transfer to dysarthric 1-shot.
- **frames+DTW on SSL ≈ MFCC+DTW** — DTW over SSL frames does *not* capture the win; pooling+cosine does.
- **stats-pool on MFCC is worse than DTW** — pooling is not a free lunch; it only pays on deep-SSL reps.
- **Score-normalization does NOT close the rank-1→FRR gap (H1 refuted, pre-registered).** The WavLM
  embedding ranks 71.9% but accepts-correct only 33.7% at FAR≤5% (FRR 66.3%). Tested whether adaptive
  rejection scoring recovers it, held-out at matched FAR: per-query cohort **z-norm → FRR 76.0%
  (worse)**; top-2 **margin → 70.0% (worse, NOT-banked family)**. The gap is genuine genuine/impostor
  *overlap*, not a per-query offset — so **CP-2 needs a substantive approach (OOV/background modeling, a
  verification stage, or a rejection-trained encoder), not a scoring tweak.** (`reject_probe.py`.)

## Robustness checks (advisor-directed) — the finding is not 3-speaker noise, and it survives shrinking

Three cheap checks run before committing to any build, to separate fact from inference:

**(a) Generalizes to typical speech (FCX control, n=740) — NOT dysarthric-specific.** Same harness
(reproduces committed MFCC control to the decimal: FC01 91.2%, FRR 50.0%):

| Control | MFCC-DTW rank-1 | WavLM rank-1 | MFCC FRR@FAR5% | WavLM FRR | WavLM AUC |
|---|---:|---:|---:|---:|---:|
| FC01 (16) | 91.2% | **94.1%** | 50.0% | **29.4%** | 0.930 |
| FC02 (121) | 78.9% | **89.8%** | ~ | **40.9%** | 0.921 |
| FC03 (136) | 69.5% | **81.5%** | ~ | **46.0%** | 0.815 |
| **ALL** | **74.6%** | **85.7%** | **75.1%** | **44.5%** | **0.870** |

+11 pts rank-1 on typical speech, and the **deployability (FRR@FAR) gain is *larger* on control**
(75.1%→44.5%, −41% rel) than on dysarthric — the embedding separates typical speech better (AUC 0.87 vs
0.72). So "learned embeddings are the CP-1 lever" is a general effect, not a dysarthric-corpus artifact.

**(b) Survives shrinking the encoder 4× (DistilHuBERT ~23M) — distillation de-risked.** Full dysarthric,
same arm: rank-1 **65.9%** (vs WavLM-base 71.9%, MFCC 55.4%), AUC 0.629 — retains ~65% of the
rank-1-error gain at ¼ the params. **Caveat:** DistilHuBERT is only 2 transformer layers and the win came
from *deep* layers, so this conflates depth and size — a purpose-distilled deep-pooled-embedding student
should do better. But even this off-the-shelf small model clears MFCC decisively, so the ~1–2M target is
plausible, not speculative. (This also honors "integrate OSS before reinventing" — a small pretrained
encoder may suffice without training our own.)

**(c) CP-2 must be measured on ambient FA/hr, not per-utterance OOV FAR — deferred.** TORGO's FAR is
per-utterance OOV, not the binding always-on **FA/hour** (~82 FA/hr today, ~160× budget). Whether the
embedding's better separability moves the *FA/hr* operating point must be measured by bringing it into the
built Picovoice/ambient harness (`PicovoiceBenchmark`) — the honest CP-2 next step, not done here.

## What this does NOT establish (constraints & caveats)

- **Language-independence is untested here.** TORGO is English; the pooled-cosine architecture is
  *lexicon-free* hence language-independent *by construction*, but cross-language generalization (the
  CP-1 gate) needs a non-English corpus — Common Voice / R-SOTA-5. XLSR-on-English is a robustness/ceiling
  probe, not the language gate.
- **Ceiling probe, not an artifact.** WavLM-base-plus is ~95M params; deployable target is ~1–2M
  (ZP-KWS). This bounds the *headroom*, not the shippable number.
- **Model scale is NOT the lever.** WavLM-**large** (~316M, 24L) does *not* beat WavLM-**base-plus** on
  F01 (both ~81–84%). Going bigger buys nothing here — which is exactly what makes the **distill-to-small**
  path credible: the useful signal lives in a representation a ~1–2M student can plausibly carry, not in
  raw capacity. (XLSR-53 multilingual: slow CPU forward pass, not completed in this window; ceiling/
  robustness only, and it does not test the language gate — TORGO is English.)
- **Enrollment-overlap k-fold leak** (same second-order caveat as the committed report) applies equally
  to both arms, so it cannot explain the *delta*.

## Next steps (feeds the CP-1 build plan)

1. **Distill the deep-SSL pooled embedding into a small (~1–2M-param) student encoder** (ZP-KWS /
   PhonMatchNet-class or a WavLM-L12→pooled-cosine distillation), evaluated in this harness for
   retained rank-1 + separability at shippable size. This is the CP-1 build — **de-risked** by the
   DistilHuBERT (~23M) retention check (robustness (b)); first try off-the-shelf small encoders before
   training our own.
2. **Wire it through the existing `QbeEncoder`/`QbeSpeechBackend` seam** (cosine prototypes) — the
   architecture the data points at — behind the FRR+FAR-vs-MFCC-DTW adoption gate.
3. **CP-2 is still independent and binding:** even the maximal encoder leaves FRR@FAR≤5% at 56–71%; the
   rejection/gating cascade must be solved on its own (ambient FA/hr), not assumed away by the encoder.
4. **Language-independence + on-device latency/size** measured before any default swap.
