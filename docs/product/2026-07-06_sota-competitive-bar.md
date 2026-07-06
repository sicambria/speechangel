<!-- SOTA competitive bar for on-device wake-word / command spotting. Standing reference; index in docs/DOC_TOC.md. -->
# SpeechAngel — SOTA Competitive Bar (wake-word / command spotting)

**Date:** 2026-07-06 · Companion to `docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md`.

This doc pins the **external state-of-the-art** so "SOTA" in our reports is a concrete, sourced number,
not a hand-wave. It sets the acceptance bar the roadmap targets, places SpeechAngel in the same ranking,
and derives roadmap items from what each competitor proves is achievable.

> **The one caveat that governs every number below:** no system is independently verified across
> **noisy + atypical-speaker + language-independent + user-trainable simultaneously.** The figures come
> from *different, non-comparable* test protocols (different corpora, SNRs, FA/hr definitions,
> vocabularies). Treat them as **bars for each axis**, not head-to-head results. This is exactly the
> selection/comparability discipline EVAL-002/003 exist to enforce internally.

---

## 1. The numeric bar (what "exceptional" means, with sources)

| System | Headline result | Conditions | Why it's the bar |
|---|---|---|---|
| **Porcupine** (Picovoice) | **97.1%** detection @ **1 FA / 10 hr** (**0.1 FA/hr**) | 10 dB SNR | The transparent, verifiable commercial bar; 11× more accurate + 6.5× faster than PocketSphinx/Snowboy; <1 MB runtime. Sets the **accuracy-at-low-FAR-under-noise** target. |
| **openWakeWord** | **design targets** FAR < 0.5/hr, FRR < 5% (verified as stated criteria); authors beat Porcupine on their setup | RPi3, 15–20 models/core; FA measured on realistic deployment audio | The **open-source deployable bar**; powers Home Assistant. The concrete candidate for our Stage-1 wake gate. (Targets, not a guaranteed measured result.) |
| **Howl** (Firefox Voice) | **10% FRR @ 4 FA/hr** | production, **8,000 users**, multilingual Common Voice | The **real-deployment reality bar** — what a shipped open system actually gets with real users (not a lab number). |
| **ZP-KWS** (NTNU, 2026; PhonMatchNet-class) | **FRR@1%FAR reduced ~60% relative** to strongest baseline (user-reported strict-mode absolute ≈29–33%); **1.55M params** total (0.9M speaker enc.) | zero-shot, research-only; LibriPhrase / GSC / Qualcomm | The **architecturally-closest SOTA**: phoneme-supervised encoder + text-independent speaker verifier, multiplicative late-fusion veto, **no per-word retraining** — SpeechAngel's exact constraint set, at edge-deployable size. Verified real (arXiv 2606.20106). |
| **PhonMatchNet** (Interspeech 2023) | **67% / 80% relative EER / AUC** improvement on LibriPhrase | zero-shot, research-only | The prior phoneme-guided zero-shot bar ZP-KWS builds on; establishes language-agnostic phoneme matching as a real technique. |
| **LRDWWS'24 winner — PD-DWS** (NPU + Xiaomi) | **FAR 0.321% / FRR 0.5%** (Score 0.00821), Rank 1 | closed-vocab **dysarthric** Mandarin wake word; 10 words × 5 enrollments/speaker | The **atypical-speech ceiling** — near-perfect dysarthric wake-word *is* achievable (speaker-dependent, but closed-vocab + ASR-assisted, so **not** language-independent). Our target population; proof it's possible. See §1.5 for the transferable techniques. |
| **LRDWWS'24 official baseline** (WEKWS **DS-TCN**) | **FRR ~10.2% / FAR ~2.9%** (Score 0.130) | same dysarthric set | **The reframe that matters most:** even a *small neural KWS* in SpeechAngel's weight class hits ~10% FRR on dysarthric speech — vs our **76%**. The gap to a *modest* neural model is already an order of magnitude; SOTA merely closes the last bit. |
| **Euphonia / Universal Personalizer** (Google, 2026) | dysarthric ASR **13.9% WER** (vs 17.5% SI baseline); 2021 personalization gave up to **85% WER reduction** | personalized, few-shot, on-the-fly | Adjacent (ASR, not KWS) but the definitive **personalization proof-point**: the target population's poor default numbers are a *model/data* gap, not a population ceiling. |
| Sensory THF / SoundHound Houndify | claims better-than-benchmark; **no published numbers** | — | Commercial, opaque — noted for completeness, not usable as a bar. |

**Distilled acceptance targets for SpeechAngel** (adopted into the roadmap, §3):

- **Always-on FAR:** MVP **≤ 0.5 FA/hr** (openWakeWord); stretch **≤ 0.1 FA/hr** (Porcupine). *We are at
  ~82 FA/hr — the deployability blocker, ~160–820× off.*
- **FRR:** **< 5%** at that FAR (openWakeWord); production-real **~10% @ 4 FA/hr** (Howl). *We are at
  76%/62% FRR @ ~5% FAR.*
- **Noise:** **~97% detection @ 10 dB SNR** (Porcupine). *We are near-chance by 5 dB, 56% rank-1 @ 20 dB.*
- **Atypical-speaker:** **FRR ~0.5% / FAR ~0.3%** is *possible* closed-vocab (LRDWWS winner); a *modest*
  neural KWS baseline already gets **~10% FRR** on the same dysarthric set. *We are at 76% FRR on real
  dysarthric TORGO — the gap the whole product exists to close, and the baseline says most of it is a
  model gap, not a population limit.*

---

## 1.5. The LRDWWS'24 winner (PD-DWS) — transferable techniques (`research/word-spotting2409.10076v1.pdf`)

This is the closest published work to SpeechAngel's actual problem — **speaker-dependent dysarthric
wake-up-word spotting from a few enrollments per person** — so its architecture is mined here for what
transfers, not just its headline number. The winning **PD-DWS** system (NPU + Xiaomi) stacks four ideas,
each mapping to a SpeechAngel lever:

1. **SSL front-end instead of MFCC** — a pretrained **data2vec2** (~300M params) finetuned multi-task,
   *not* hand-crafted MFCC. This is our A1/QbE lever, now validated *on dysarthric speech*. (Their model
   is far too large to ship on-device as-is — the transferable claim is "learned SSL features beat MFCC
   for this population," which a small distilled/24k-class encoder can chase.)
2. **Multi-task auxiliary ASR** — a joint **ASR + WWS** objective (CTC loss assists the max-pooling KWS
   loss); the phonetic task regularizes the wake detector. *Breaks language-independence* (needs an ASR
   branch), so it's a **milder-impairment / Path-A option**, not the language-independent default — but
   the "auxiliary phonetic supervision helps" lesson is real.
3. **Dual-filter cascade decision (the rejection lever, done right)** — a **threshold filter** then an
   **ASR filter** that cross-verifies the detected wake-word's *length* against an independent Paraformer
   ASR decode; length mismatch → reject. This is a concrete, powerful **verification/rejection** design
   (our A4 lever, our unbanked `margin` territory): a cheap second opinion that cuts FAR without moving
   the primary detector — exactly the "two different problems" framing in the scorecard.
4. **TTS + noise augmentation** — VITS-synthesized *dysarthric* audio (control/uncontrol style embedding)
   plus **MUSAN noise at 8–20 dB SNR**, 10% volume and 0.9–1.1× speed perturbation. This is our R-SOTA-6
   noise-robustness recipe, plus a data-scarcity answer (synthesize dysarthric training audio).

**Operating-point lesson:** their ablation (paper Table 4) shows the accept threshold rank swings Score
from 0.070 → 0.032 — the decision layer, not just the model, is where a large fraction of the error
lives. That is the same "threshold cost dominates" finding as our own held-out TORGO analysis.

**Honest boundary:** PD-DWS is **closed-vocabulary Mandarin, ASR-assisted, and ~300M params** — it
trades away exactly the axes SpeechAngel scores highest on (language-independence, tiny footprint,
any-word). It is the **accuracy ceiling to learn from**, not a design to copy wholesale; the takeaways
that respect our constraints are the SSL front-end (small), the dual-filter cascade, and the augmentation
recipe.

---

## 2. Where SpeechAngel places in the field (same 7 axes, same 0–100 scale)

Scored on the user-supplied axes (noise robustness / trainability / language independence /
atypical-speaker robustness / maturity / efficiency / transparency; **overall = rounded mean**), so
SpeechAngel is directly comparable to the competitive set.

| System | Noise | Train | Lang-indep | Atypical | Maturity | Efficiency | Transparency | **Overall** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Porcupine** | 85 | 70 | 40 | 55 | 90 | 95 | 85 | **74** |
| **Sensory THF** | 60 | 65 | 55 | 60 | 90 | 90 | 20 | **63** |
| **openWakeWord** | 75 | 55 | 30 | 35 | 75 | 75 | 65 | **59** |
| **Howl** | 55 | 45 | 75 | 55 | 30 | 70 | 80 | **59** |
| **⭐ SpeechAngel** | **25** | **85** | **95** | **40** | **15** | **65** | **90** | **59** |
| **PhonMatchNet-class** | 50 | 90 | 55 | 25 | 15 | 55 | 85 | **54** |
| **Houndify** | 45 | 55 | 45 | 40 | 70 | 50 | 15 | **46** |

**SpeechAngel's profile is the most *inverted* in the field** — and that is the strategic read:

- **Best-in-field on language-independence (95)** — no ASR/phonemes, works in *any* language incl.
  unwritten ones; beats even the phoneme-based zero-shot systems (PhonMatchNet 55, Howl 75).
- **Near-best on trainability (85)** — 1-shot, on-device, no cloud, any word; only PhonMatchNet (90,
  zero-shot) edges it, and that's research-only.
- **Best-in-field on transparency (90)** — fully open (AGPL), pre-registered, held-out, honest negatives.
- **Worst-in-field on maturity (15) and noise (25), weak on measured atypical performance (40).** These
  are exactly the axes the roadmap must attack; they are *why* the raw FRR/FAR is an order of magnitude
  off despite a differentiated design.

**Interpretation:** SpeechAngel is a **59 that got there the opposite way** from openWakeWord (75/75
noise/maturity, 30 lang-indep). It has already *won* the axes that are hardest to retrofit
(language-independence, user-trainability, privacy/transparency) and lost the axes that are most
*buildable* (noise handling, maturity, tuned accuracy). That is a fundamentally more promising place to
start than the inverse — you cannot bolt language-independence onto Porcupine, but you *can* bolt noise
robustness and a wake cascade onto SpeechAngel.

> **Why this doc says 59 and the scorecard says 480/1000.** They measure different things and weight
> validation completely differently. This **59** is a *flat mean of 7 technical axes* where maturity is
> only 1/7, so the differentiated-design axes (language-independence, trainability, transparency) pull it
> up to mid-field. The **480/1000** (`…real-life-scorecard.md`) is *validation-weighted product
> maturity* — delivered/measured user value dominates and hygiene is capped, deliberately held under the
> pre-alpha→alpha "validation wall." A differentiated but unvalidated product ranks mid-field on raw
> technical axes yet low on product maturity; both are true.

---

## 3. What each competitor teaches → roadmap items

Every item below is mirrored into `docs/ROADMAP.md` (§ "SOTA competitive bar — derived items").

| From | Lesson | Roadmap item |
|---|---|---|
| **ZP-KWS / PhonMatchNet** | A zero-shot, language-agnostic **phoneme-matching encoder** beats MFCC-DTW while *keeping* our constraints (no retraining, any word) — at **1.55M params**, edge-deployable, with FRR@1%FAR cut ~60% rel. | **R-SOTA-1:** Evaluate a ZP-KWS / PhonMatchNet-class phoneme-supervised encoder (± the text-independent speaker-verifier veto branch) as an alternative/augmentation to MFCC-DTW in the `QbeEncoder` seam — the SOTA that shares our language-independent + user-trainable constraints, at a shippable size. |
| **openWakeWord** | An open model hits **<0.5 FA/hr** and runs 15–20 models/core on an RPi3 → phone-feasible. It's the missing **Stage-1 wake gate** that keeps the command matcher off raw ambient audio. | **R-SOTA-2:** Benchmark openWakeWord (and a personalized wake template) as the Stage-1 wake cascade; target ≤0.5 FA/hr *at the wake stage alone* on a real ambient recording. |
| **Porcupine** | Sets the concrete numeric bar (97.1% @ 0.1 FA/hr @ 10 dB) **and** an open benchmark protocol (`wake-word-benchmark`: detection-rate @ fixed FA/hr @ SNR). | **R-SOTA-3:** Adopt the Picovoice `wake-word-benchmark` reporting protocol (detection @ fixed FA/hr @ SNR) as SpeechAngel's own, so our numbers are externally comparable. Fold into the `core:eval` condition grid. |
| **LRDWWS'24 winner (PD-DWS)** | Near-perfect dysarthric wake-word (FAR 0.32%/FRR 0.5%) **is achievable**; four transferable ideas (§1.5): SSL front-end, auxiliary ASR, **dual-filter ASR cross-verify cascade**, TTS+MUSAN augmentation. And the **baseline** (~10% FRR neural KWS) shows most of our 76% gap is a model gap. | **R-SOTA-4:** Adopt PD-DWS's constraint-respecting techniques: (a) a small SSL front-end for the QbE encoder (R-SOTA-1), (b) a **dual-filter cascade** — length/second-opinion cross-verify at the decision layer as an FAR-cutting rejection stage (the honest `margin`/A4 lever), (c) the TTS-dysarthric + MUSAN augmentation recipe (R-SOTA-6). Skip the ASR-branch default (breaks language-independence → Path-A only). |
| **Howl** | Real production = **10% FRR @ 4 FA/hr** with 8,000 users on **Common Voice** (multilingual, CC0). Sets a realistic non-lab target and a language-independence corpus lever. | **R-SOTA-5:** Add Common Voice (multilingual, CC0) as a language-independence eval corpus; set "**10% FRR @ 4 FA/hr**" as the realistic production milestone before the <5% stretch. |
| **Noise axis (all)** | Every mature shipped system scores 45–85 on noise; we score 25. The sim harness already says noise is the dominant degrader. | **R-SOTA-6:** Multi-condition enrollment/augmentation (RIR + MUSAN) + SNR-adaptive accept threshold, measured on the existing condition grid; target the noise-axis gap directly. |

**Sequencing note:** R-SOTA-2 (wake cascade → FAR) is the deployability gate and comes first; R-SOTA-1
(zero-shot encoder → accuracy) has the highest ceiling; both are gated on R-SOTA-5's corpus and the SAP
acquisition already on the roadmap. R-SOTA-3 (protocol) is cheap and unblocks comparable reporting now.

---

## 4. Sources

- Porcupine — [picovoice.ai/docs/faq/porcupine](https://picovoice.ai/docs/faq/porcupine/) ·
  [github.com/Picovoice/porcupine](https://github.com/Picovoice/porcupine) ·
  [github.com/Picovoice/wake-word-benchmark](https://github.com/Picovoice/wake-word-benchmark)
- Sensory TrulyHandsfree — [sensory.com/custom-wake-words-branded-voice-ux-guide-2026](https://sensory.com/custom-wake-words-branded-voice-ux-guide-2026/)
- openWakeWord — [github.com/dscripka/openWakeWord](https://github.com/dscripka/openWakeWord)
- Howl / Firefox Voice — [arxiv.org/abs/2008.09606](https://arxiv.org/abs/2008.09606) ·
  [github.com/castorini/howl](https://github.com/castorini/howl)
- PhonMatchNet (Interspeech 2023) — [arxiv.org/abs/2308.16511](https://arxiv.org/abs/2308.16511) ·
  [github.com/ncsoft/PhonMatchNet](https://github.com/ncsoft/PhonMatchNet)
- ZP-KWS — "Personalized Keyword Spotting … Leveraging Text-Independent Speaker Verification" (Hu et al.,
  NTNU, 2026), [arxiv.org/abs/2606.20106](https://arxiv.org/abs/2606.20106) — *ID verified via web
  search 2026-07-06; `2606` = June 2026, recent not fictional. 1.55M params; FRR@1%FAR reduced ~60% rel.*
- LRDWWS dysarthric challenge winner (PD-DWS, SLT 2024) — local copy
  `research/word-spotting2409.10076v1.pdf` · [arxiv.org/abs/2409.10076](https://arxiv.org/abs/2409.10076)
  *(numbers read directly from the PDF: test-B FAR 0.00321 / FRR 0.005 / Score 0.00821; baseline Score
  0.130306, FAR 0.028639, FRR 0.101667).*
- Dysarthric ASR personalization (adjacent) — Google Project Euphonia
  [research.google/blog/personalized-asr-models-from-a-large-and-diverse-disordered-speech-dataset](https://research.google/blog/personalized-asr-models-from-a-large-and-diverse-disordered-speech-dataset/)
  · "Universal Personalizer" [arxiv.org/abs/2509.15516](https://arxiv.org/abs/2509.15516) (13.9% WER).

> **Method note:** competitor axis scores are the user-supplied set; the SpeechAngel row is scored on the
> same rubric against this repo's *measured* state (`…frr-far-torgo.md`, `…realistic-conditions…md`) —
> low on maturity/noise (unbuilt/unvalidated), high on lang-independence/trainability/transparency
> (implemented + verified). The most exposed self-score is **efficiency 65** — MFCC-DTW is cheap *a
> priori*, but latency/CPU are as unbenchmarked as maturity (15) and atypical (40); treat 65 as an
> estimate to confirm on a physical device, not a measured axis. Licenses for any adopted component
> (openWakeWord, ZP-KWS, corpora) must clear the roadmap's permissive-only filter before bundling.
