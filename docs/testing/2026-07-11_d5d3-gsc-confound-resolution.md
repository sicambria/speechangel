# Typical 800 floor — resolving the D5/D3 cross-corpus confound: the number didn't move, the diagnosis did

**Date:** 2026-07-11 · **Journey:** "continue experiments — re-measure D5-reverb + D3-ambient on
GSC-scale to resolve the confound, then real-RIR / real ≥6 h ambient for typical-900" (deferred under
host load, not walls). · **Corpora:** GSC-19 (typical, robust word-repeat), + real ambient
DEMAND+LibriSpeech. · **Binding metrics:** D5/D4/D6 = rank-1 identification (FAR-free), paired
within-corpus; D3 = false-accepts/hour on a REAL ambient stream at the deployment threshold.

> **Headline.** The committed typical composite carried an **800 floor as a three-way tie** — D2 (~5.6 %
> FRR), **D5-reverb (81.4 %)**, and **D3-ambient (~800)**. This session re-measured D5 and D3 on the
> **same robust basis D2 uses** (the cross-corpus confound, EVAL-004) and both legs of the tie turned out
> to be **cross-corpus artifacts, not real blockers**: **D5-reverb = 95.8 % → band 900** (the 81.4 % was
> a TORGO-n3 small-corpus artifact) and **D3-ambient = 0.07 FA/hr mean → band 900** (the "~800" was a
> hard-coded literal; the ~82 FA/hr was a naive bridge). **The composite is still 800** — but it is now
> gated by a **single, un-walled domain (D2)**, not three. The number didn't move; the **diagnosis**
> did — from "fix three things" to "fix one un-walled thing." That is the strategic win.

---

## 1. What was actually banked before this session (the confound)

The 2026-07-11 population-split composite (`2026-07-11_population-split-800-900.md`) put typical at band
800 as a three-way tie: D2 ~5.6 % (robust GSC-19), D5-reverb 81.4 %, D3-ambient ~800. But **only D2 was
on the robust corpus.** D5/D4/D6 were TORGO **control n=3** (`typical_composite.py`), and D3 was a
**hard-coded literal** (`typical_composite.py:137` prints `"D3 ambient: ~800 (dual-cascade,
off-encoder)"` and injects the literal `800`). We had already rejected TORGO-n3 for D2's old 13.8 % — so
trusting it for D5=81.4 %, or trusting a hard-coded 800 for D3, to crown them 800-floor co-blockers was
the **cross-corpus confound (EVAL-004)**. This session re-measures both on the robust basis.

## 2. D5-reverb (and D4/D6) — re-measured on GSC-19 → all band 900

`t4_gsc_channel.py`: wavlm-large L15, few-shot + multi-condition enrollment (**the augmentation fns and
scoring imported VERBATIM from `typical_composite.py`** → EVAL-004 fidelity gate near-automatic; only
the corpus changed). Rank-1 is threshold-free. Confound resolved on the **paired within-GSC**
degradation (cross-corpus absolute rank-1 is not comparable — GSC is easier: clean 98.2 % vs TORGO-n3
89.9 %), not on matching 81.4 %.

| Domain | cond | GSC-19 rank-1 | band | paired Δ vs clean | McNemar exact p |
|---|---|--:|:--:|--:|--:|
| D1 | clean | 98.2 % | 900 | — | — |
| **D5** | reverb rt60≈250 ms | **95.8 %** | **900** | **+2.4 pp** | **2.7e-5** |
| D4 | noise @20 dB | 98.4 % | 900 | −0.1 pp | 1.0 (ns) |
| D6 | bandwidth 300–3400 Hz | 98.2 % | 900 | 0.0 pp | 1.0 (ns) |

- **D5-reverb clears band 900 (95.8 %).** Reverb is a **real but tiny** degrader — the paired Δ (+2.4 pp,
  25 clean-only-hits vs 3 cond-only-hits) is highly significant (p=2.7e-5) yet mild in magnitude, and the
  reverb condition sits ~13 pp above the 85 % band-900 bar. The advisor's trap (a mild Δ that still lands
  <85 %) did **not** occur.
- The committed **81.4 % was a TORGO-n3 artifact** (small vocab / n=3 difficulty), not a reverb wall.
  D4/D6 likewise band-900 with null paired deltas. **All three channel-robustness domains leave the 800
  floor.**

## 3. D3-ambient — the honest FA/hr on a REAL ≥6 h stream → band 900

The composite's D3 was never measured for this encoder. `t5_gsc_ambient_fahr.py` supplies it:
wavlm-large L15 few-shot, **GSC-19 enrolled**, each speaker at its own **FAR≤5 % threshold** (fit on the
speaker's near-vocab OOV negatives — the deployment model), streamed against a **real 6.0 h ambient
recording**. The gated pipeline (StreamingEnergyGate/VAD + WIN 1.5 s / HOP 0.5 s / refractory 1.0 s) and
the ambient sources are **reused verbatim from `a3_far_bridge.py`**; only the encoder
(distilhubert→wavlm-large L15) and the enrollment corpus (TORGO→GSC-19) changed.

**Result: 15,664 gated windows over 6.00 h → aggregate mean = 0.070 FA/hr → band 900.**

| statistic | value |
|---|---|
| Ambient mix (real, un-looped) | 1,383 DEMAND-noise windows + 14,281 LibriSpeech-speech windows (**speech-heavy = adversarial upper bound**) |
| Per-speaker FA/hr distribution | 14/19 = **0.0**; five at 0.17–0.50; **worst-of-19 = 0.50** (exactly at the bar) |
| Total false accepts | 8 — **all from LibriSpeech speech, 0 from DEMAND noise** |
| 95 % rule-of-three UB (0-accept speaker, 6 h) | 0.50 FA/hr |

- **D3 clears band 900**, but honestly it is a **distribution**: clean band-900 for 14/19 speakers, with
  a tail whose worst speaker sits **exactly at** the 0.5 FA/hr bar — treat it like D2's hard-speaker tail,
  not a clean pass.
- **The old numbers were pessimistic, not wrong-for-their-regime.** The naive bridge (FAR5%/trial ×
  T≈1,800 windows/hr ≈ 92 FA/hr) and the product doc's ~82 FA/hr describe the **speaker-INDEPENDENT
  single-stage wake-word** regime ("0.1 FA/hr ⇒ 87.5 % miss"). The composite recognizer is
  **speaker-DEPENDENT few-shot with a per-speaker threshold** — real ambient sits far from any individual
  user's specific command templates, a fundamentally easier rejection problem (confirms the a3 bridge's
  0 FA/hr at 6 h scale on the actual encoder).
- **Same operating point as D2 (now verified at one layer):** D3's threshold, the channel domains, and a
  fresh D2 recompute are all at L15. D2 @ L15 = **5.5 % FRR @ FAR 4.3 %** (vs the L12-banked 5.6 % @
  4.2 %) — band 800 either way. So "D2 (5.5 % FRR) and D3 (0.07 FA/hr) are the same FAR≤5 % operating
  point" is now a **fact**, not a claim.

## 4. The revised typical composite (one coherent layer/threshold, L15)

| Domain | TYPICAL band | note |
|---|:--:|---|
| D1 rank-1 (clean) | 900 | 98.2 % (GSC-19) |
| **D2 FRR@FAR≤5 %** | **800** | **5.5 % @ L15 (5.6 % @ L12) — the SOLE remaining 800 domain; un-walled** |
| D3 ambient FA/hr | 900 | 0.07 mean (real 6 h; worst-of-19 at the 0.5 bar) |
| D4 noise @20 dB | 900 | 98.4 % |
| **D5 reverb** | **900** | **95.8 % (was 81.4 % TORGO-n3)** |
| D6 bandwidth | 900 | 98.2 % |
| D13 enrollment | 950 | carried |
| **Composite (min)** | **800** | **gated by D2 alone** |

**Framing (honesty contract — the number did not move):** the composite is **still band 800**. What
changed is the **diagnosis**: the 800 floor was a three-way tie whose other two legs (D5, D3) were
**cross-corpus artifacts**; **one un-walled blocker (D2) actually remains.** Typical-900 is therefore a
**single representation problem for D2's 2–3 hard-voice speakers** (a mild, localized analogue of the
dysarthric within-word overlap), not a channel-robustness or always-on-rejection wall. Fix one thing,
not three.

## 5. Method integrity

- **EVAL-004 fidelity:** augmentation + gate + scoring imported verbatim from the committed harnesses;
  only the corpus/encoder under test changed. GSC clean rank-1 (98.2 %) is the sanity anchor.
- **Paired adjudication** for D5/D4/D6 (McNemar exact on 912 same-item pairs); **cross-corpus absolutes
  explicitly not compared.**
- **Real ambient** for D3 — DEMAND+LibriSpeech, un-looped 6.0 h, at the deployment gate + per-speaker
  FAR≤5 % threshold; disjoint corpora (OOV-word threshold-fit vs ambient test → no leakage).
- **One-layer composite:** D2 recomputed at L15 so all domains share a layer/threshold.
- **FAR-matched throughout** (realized held-out FAR printed).

## 6. Caveats, bounded risks, and next levers (hypotheses, not results)

1. **Real-RIR (D5) — acknowledged bounded risk, deferred not dropped.** D5 cleared on the **synthetic
   exp-decay RIR**. Real measured RIRs (early reflections, coloration) can be harsher — but with a +2.4 pp
   paired Δ and ~13 pp headroom to the 85 % bar, a regression below 900 is very unlikely. No RIR corpus is
   on disk and `pyroomacoustics` is absent; a quick confirm would download OpenSLR SLR26/28 and convolve
   with `scipy.signal.fftconvolve`. **Lever, low priority.**
2. **D3 further fidelity.** The 6 h stream is real but **speech-heavy** (adversarial UB) and assembled
   from DEMAND + LibriSpeech; a **single continuous real-room recording** (one long domestic capture)
   would remove the assembled-stream caveat and tighten the worst-speaker tail below the 0.5 bar.
3. **The real work is D2.** With D3/D5 off the floor, typical-900 = closing D2's 2–3 hard-speaker tail
   (they survive more reps AND per-speaker thresholding, §1.2 of the population-split doc) — a
   representation problem for hard voices, the honest next journey.

**Banked:** D5-reverb = band 900 (GSC-19, paired); D3-ambient = band 900 (real 6 h, distribution with
worst-of-19 at the bar); typical composite = **800, D2-gated (single un-walled domain)**, verified at one
layer. **NOT-banked / next:** real-RIR confirm, single-continuous-room D3, D2 hard-voice tail.
Artifacts: `_ceiling_cache/t{4,5}_*.json` (measure-only, git-tracked evidence); harnesses
`t4_gsc_channel.py`, `t5_gsc_ambient_fahr.py`.
</content>
