# Typical → 900: the ≤150 MB student holds band 800, and the hard-voice tail is a representation wall

**Date:** 2026-07-11 · **Journey:** "next 30 most valuable experiments toward typical-900" — pruned
(advisor-gated) to the decisive subset: **C3 student-fidelity confirm** (primary) + a **band-900
wall-kill arm** (vocab-diagnostic → verifier → alternate-encoder). · **Corpus:** GSC-19 (typical, robust
word-repeat), identical a5 manifest across all encoders. · **Binding metric (EVAL-007):** D2 = FRR @
FAR≤5%, held-out (LOFO), FAR-matched. **Band cutoffs (DomainBands.kt spec 2):** 900 = ≤5%, 800 = ≤15%.

> **Headline.** Two deliverables. **(1) C3 — the shipped fallback survives, and a committed number is
> corrected.** Measured apples-to-apples on the identical GSC-19/K5 manifest the teacher's 5.81% uses,
> **every deployable ≤150 MB student holds band 800**: best = wavlm-base-plus (94 MB) **8.77% @ FAR 4.1%,
> +3.0 pp** over the teacher (distilhubert 24 MB +3.5 pp; hubert-base +5.5 pp; wav2vec2-base +7.8 pp).
> This **confirms** the layer-route report's *inferred* "1–3 pp penalty" (it lands at the top of that
> range) and **corrects** the carried "~12% / +6 pp" (a GSC-24 cross-corpus confound, EVAL-004): the
> honest penalty is **+3.0 pp**. **(2) The band-900 arm is a confirmed wall-kill, not a win — a
> *mean-pooled-embedding* wall.** The hard-speaker failures are **diffuse** (59% genuine-word-#1-but-
> below-threshold, not vocab-confusable, t8); the most expressive admissible decision function (a learned
> LOSO verifier) **caps below cosine** (7.57% > 5.81%, t9); **98ea0818 is the hardest speaker on all six
> encoders** (wavlm-large/base-plus, distilhubert, hubert-base, wav2vec2-base, xlsr-53 — three objectives,
> two scales, t11); and **enrollment augmentation makes it worse** (7.24%, t12). Five axes closed — layer,
> vocab, decision-fn, encoder, augmentation — **all mean-pooled**; the one untested representation axis is
> **frame-level pooling** (the honest next journey). **Band-900-typical is out of reach for both the
> teacher (5.8%, walled tail) and the student (8.8%); the shipped number is band 800 either way** — and
> this is a *localized* hard-voice wall (AUC 0.988), **not** the dysarthric information-theoretic one.

---

## 1. Target framing (resolved from the docs before any coding)

The advisor flagged a blocker: *which encoder actually ships?* Resolved from the authoritative,
most-recent statements — `sota-800-push.md:22` (RESOLUTION) and `uaspeech-acquisition.md:29`: the
typical-800 composite is claimed with **wavlm-large (~316 MB) behind the VAD gate** as the deployable
(the ≤2 MB cap was relaxed under CONSTRAINT-001, with a device argument). The `≤~150 MB` figure is the
**D11/D12 RAM target and a student-fallback line**, and D11/D12 are **excluded from the wall-dominated
composite**. So:

- **Band-900-*teacher* is a legitimate target** — but it is exactly the walled ~6-flip knife-edge the
  layer-route journey (`2026-07-11_typical-d2-layer-route-closed.md`) nearly closed.
- **Caveat carried, not laundered:** wavlm-large's on-device INT8 latency/size is **device-unvalidated**
  (`ssl-ceiling:28`); "typical = 800" is an accuracy-only number resting on an unproven deployability
  assumption. **That is exactly why C3 (the measured student fallback) is the crown jewel.**

Baseline (fidelity-anchored, teacher): **wavlm-large L12/K5 = 5.81% FRR @ FAR 3.9%**, npos = 912
(reproduced by t6/t7/t8 to the decimal). The residual is a 2–3-speaker hard tail (98ea0818 27%,
2aca1e72 25%, c1d39ce8 19%).

## 2. C3 — student-fidelity confirm (the PRIMARY deliverable)

`t10_c3_student.py`: the **identical a5 GSC-19 manifest** (same speakers/words/negatives — change-one-
variable, EVAL-004), only the encoder swapped; best layer per encoder; held-out FRR@FAR≤5%, FAR-matched.

| Encoder | size | best layer | FRR @ FAR≤5% | realized FAR | band | penalty vs teacher | hardest speaker |
|---|--:|:--:|--:|--:|:--:|--:|---|
| wavlm-large (teacher) | 316 MB | L12 | 5.81% | 3.9% | 800 | — | 98ea0818 27% |
| **wavlm-base-plus** | **94 MB** | L12 | **8.77%** | 4.1% | **800** | **+3.0 pp** | 98ea0818 56% |
| distilhubert | 24 MB | L2 | 9.32% | 3.2% | 800 | +3.5 pp | 98ea0818 54% |
| hubert-base | 95 MB | L11 | 11.29% | 4.9% | 800 | +5.5 pp | 98ea0818 54% |
| wav2vec2-base | 95 MB | L4 | 13.60% | 4.4% | 800 | +7.8 pp | 98ea0818 60% |

- **The band-800 fallback claim rests robustly on wavlm-base-plus (94 MB) = 8.77%, +3.0 pp** — a shipped
  typical composite is **band 800 whether the teacher deploys or the best fallback does.** Band 900 (≤5%)
  is out of reach for the student too. This anchor is not selection-on-test: L12 is the *same principled
  deploy layer as the teacher*, and wavlm-base-plus sits on a smooth deep-layer plateau (L7–L12 all
  8.8–10.7%, ~6 pp of band-800 headroom). distilhubert (24 MB, 9.32%) is likewise robust.
- **Caveat (selection-on-test on the mined encoders):** `eval_student` picks each encoder's *best* layer
  by minimizing test FRR. For hubert-base (L11) and especially **wav2vec2-base**, that is mined:
  wav2vec2-base clears band 800 at *only* its shallow L4 (13.60%, and at FAR 4.4% > the teacher's 3.9%,
  which flatters FRR) — **9 of its 12 layers are >15% (below band 800).** So wav2vec2-base is *within
  layer-selection noise of the boundary*, not an independent robust band-800; the conclusion "the shipped
  fallback holds band 800" survives on wavlm-base-plus/distilhubert, and the mined encoders are reported
  but not leaned on.
- **Correction to a committed report (EVAL-004).** `2026-07-11_typical-d2-layer-route-closed.md` §7 wrote
  an *inferred* "normal 1–3 pp student penalty," and the carried A3b/C21 figure was "~12% / +6 pp" — but
  that 12% was **wavlm-base-plus on GSC-24** (harder speakers), a cross-corpus confound. Apples-to-apples
  on GSC-19 the penalty is **+3.0 pp (8.77%)**. Neither the inference nor the carried number was the
  measurement; this is (see §7).
- **Intrinsic-tail evidence (the diagnostic the advisor asked for).** Speaker **98ea0818 is the hardest
  on all five encoders** (27% → 54–60%), worsening monotonically as capacity drops, spanning three SSL
  objectives (wavlm masked-denoising, hubert masked-cluster, wav2vec2 contrastive). Its hardness is not a
  wavlm artifact. (893705bb is *student-sensitive* — fine on the teacher at 10%, hard 29–44% on every
  weaker student — the opposite pattern, and evidence the students lose separability the teacher keeps.)

## 3. The band-900 wall-kill arm

### 3.1 Vocab-co-design diagnostic (`t8`) — the failures are DIFFUSE, not confusable pairs

The advisor's fork: if the hard speakers fail on *specific confusable word pairs*, vocab co-design (the
one lever with a banked cross-speaker positive — dysarthric +5.4 pp held-out) is the band-900 primary; if
diffuse, the wall-kill framing dominates. Classifying every hard-speaker false-reject at L12/K5:

| speaker | false-rejects | wrong-word | below-threshold | top-2-word concentration |
|---|--:|--:|--:|--:|
| 98ea0818 | 13 | 10 (77%) | 3 | 46% |
| 2aca1e72 | 12 | 3 (25%) | 9 | 50% |
| c1d39ce8 | 9 | 1 (11%) | 8 | 44% |
| **aggregate** | **34** | **14 (41%)** | **20 (59%)** | — |

**Verdict: DIFFUSE.** 59% of false-rejects are *below-threshold* (the genuine word is ranked #1 but its
distance exceeds the accept threshold — intrinsic within-word scatter, not a competitor confusion). Even
the one confusion-dominated speaker (98ea0818) has **scattered, non-repeating** pairs (backward→left,
on→go, one→left, one→on — each once), so dropping/replacing 1–2 command words rescues nothing. Vocab
co-design is **not** the band-900 primary. What could help is a representation that clusters within-word
repeats *tighter* — which §3.2/§3.3 test.

### 3.2 Learned pairwise verifier (`t9`) — the strongest admissible decision function caps below cosine

`t9_verifier_gsc.py`: a LOSO-trained MLP on pair features `[q·t, |q−t|]` → same/different logit (cosine
is one special case; ships frozen <1 MB, admissible). Trained on 18 speakers, evaluated on the held-out
speaker with the identical a5 folds/K/manifest. This was the decisive "wall vs soft" test for dysarthric
(capped at AUC ~0.70). On typical:

- **Aggregate verifier FRR = 7.57% @ FAR 3.3% — *worse* than cosine 5.81%.**
- The "2/3 hard speakers improved" (c1d39ce8 19%→12% real; 2aca1e72 25%→23% noise) is a **mirage**: the
  hardest speaker **98ea0818 regressed 27%→58%** (the cross-speaker verifier does not generalize to the
  hardest held-out speaker) and several easy speakers regressed (893705bb 10%→33%). Net aggregate worse,
  higher variance. **A wall-confirmer, not a lever** (EVAL-005 — don't headline the winning cells).

### 3.3 Alternate large encoder (`t11`) — does a different SSL objective at teacher scale rescue the tail?

`t11_altencoder_tail.py`: **wav2vec2-large-xlsr-53** (315 M, multilingual *contrastive* objective — a
genuinely different geometry from wavlm's masked-denoising, at *matched capacity* so the C3 students'
capacity confound is removed). Identical GSC-19 manifest.

- **xlsr-53 best L18 = 9.21% aggregate FRR @ FAR 3.9%, band 800** — worse than wavlm-large 5.81% (a
  different objective is not a better encoder here).
- **Hard-speaker side-by-side:** 98ea0818 **56%** vs wavlm 27% (worse); 2aca1e72 21% vs 25% (marginally
  better, still walled ~21%); c1d39ce8 19% vs 19% (same). **1/3 improved, marginally.**
- **Verdict: the tail is representation-GENERAL.** The same speakers are hard under a fundamentally
  different SSL objective at matched capacity. Combined with §2, **98ea0818 is the hardest speaker on six
  encoders** — wavlm-large, wavlm-base-plus, distilhubert, hubert-base, wav2vec2-base, xlsr-53 — spanning
  three SSL objectives and two capacity scales. Its hardness is a property of the speech.

### 3.4 Enrollment augmentation (`t12`) — more template diversity does not close the below-threshold tail

`t12_aug_enroll.py`: the axis the t8 diagnostic points straight at (59% below-threshold = genuine word
ranked #1 but too far). Each enrolled template gets speed-perturbed copies (±10%, Kaldi-style), encoded
with the wavlm-large teacher at L12, expanding the enroll pool; queries stay original; threshold re-fit
at FAR≤5% (impostors score against the same expanded pool). This is the natural extension of the one
robustly-banked lever (few-shot enrollment) and the *multi-template* generalization of the mean-pooled
axes above.

- **Aggregate FRR = 7.24% @ FAR 4.1%, band 800 — *worse* than baseline 5.81%.** Adding synthetic
  within-word scatter lowers *impostor* min-distances too, so the FAR≤5% threshold tightens and net FRR
  rises.
- **Hard speakers:** 98ea0818 **52%** vs 27% (worse — augmenting an already-scattered voice adds noise on
  both sides); 2aca1e72 25% (same); c1d39ce8 17% vs 19% (marginally better). **1/3 improved.**
- **Verdict: augmentation does not close the tail.** The below-threshold failures are genuine within-word
  scatter that synthetic template diversity amplifies rather than tightens.

## 4. What was NOT re-run (and why — step 11 / EVAL-003)

The 2026-07-10 candidate-experiments campaign already **refuted the learned bolt-on refinements on GSC
typical**: C15 deep-layer win (n=3 artifact, flat on GSC), B6 mean-of-best-2 (−2.5 pp on clean GSC), C14
episodic head (destroys transfer), F29 rate-norm, F28 discrete-variant enrollment, B7 KDE-LR, B11
confusability-tighten (`docs/testing/2026-07-10_candidate-experiments.md`). Re-running them is the
suboptimization step 11 forbids — they are **covered by reference, not re-run**. Likewise the
score-norm/backend/per-command-threshold family (r2/r3/n1) is prior-closed for a tail that survives
per-speaker thresholding (layer-route report §3) and is the same family that died on dysarthric. The
"30 most valuable experiments" is therefore the **decisive subset** (C3 ×4 encoders + t8 vocab-diag +
t9 verifier + t11 alt-encoder + t12 augmentation), with the dead levers documented — not 30 reruns.

## 5. Method integrity

- **EVAL-004 fidelity + change-one-variable:** every C3 student uses the *identical* a5 manifest; the
  teacher L12/K5 = 5.81% anchor is reproduced by t6/t7/t8 to the decimal; the verifier and vocab-diag
  reuse a5's fold/enroll/K/min-agg and cand_lib's threshold primitives verbatim.
- **FAR-matched** on every verdict (realized held-out FAR printed); the verifier's aggregate FAR (3.3%)
  is *below* target, so its regression is not a threshold artifact.
- **Adjudicated on FRR@FAR (EVAL-007)**; the winning verifier cells are reported but explicitly not
  headlined (EVAL-005).
- **No mining:** the pre-registered band-900 primary was chosen *by the t8 diagnostic* (diffuse → wall-
  kill), not after seeing the levers' results.

## 6. Banked, not-banked, and scope

- **BANKED (measured):** every deployable ≤150 MB student holds **typical D2 band 800** on GSC-19/K5
  (robustly on wavlm-base-plus 8.77%, +3.0 pp; §2 caveat on the mined encoders); the shipped typical
  composite is **band 800 under either the teacher or the best student.** The band-900 hard-voice tail is
  a **mean-pooled single-template embedding wall**: diffuse/below-threshold (not vocab, t8), unmoved by
  the strongest admissible decision function (verifier caps below cosine, t9), encoder-general (98ea0818
  hardest on six encoders / three objectives, §2+t11), and not closed by multi-template enrollment
  augmentation (t12, worse).
- **NOT-banked / directional:** the verifier's and augmentation's per-speaker "wins" (c1d39ce8 19%→12% /
  19%→17%) — selection-on-cells, aggregate worse, not adoptable.
- **Scope / honesty (precise — do NOT read this as "typical D2 is walled"):** the wall is closed across
  **five axes** — layer, vocab, decision-function, encoder-objective, enrollment-augmentation — **all of
  which operate on mean-pooled embeddings.** The one representation axis **not tested** is **frame-level
  pooling** (attentive/GeM pooling, frame-QbE-DTW — the sub-word temporal structure mean-pooling
  discards); it needs a frame re-encode and has a low prior (frame-DTW lost on dysarthric) but is **not
  measured on typical** — the honest next journey (§8). This is materially stronger than the layer-route
  report's single axis, but still **milder than the dysarthric wall** (typical AUC 0.988 vs 0.65; 16/19
  speakers ≤3%): a **localized mean-pooled-embedding hard-voice wall**, not an information-theoretic one.
  The teacher's on-device deployability remains device-unvalidated (§1).

## 7. What the measurement settles about the two prior estimates

`docs/testing/2026-07-11_typical-d2-layer-route-closed.md` §7 lever 2 *inferred* a "normal 1–3 pp student
penalty." The clean apples-to-apples measurement is **+3.0 pp** (wavlm-base-plus 94 MB, 8.77%, band 800)
— i.e. it lands at the **top of that inferred range and CONFIRMS the inference.** What it **corrects** is
the *carried* A3b/C21 figure of "~12% / +6 pp," which was **wavlm-base-plus on GSC-24** (harder speakers)
— a cross-corpus confound (EVAL-004: a carried number on a different corpus is not the measurement on
this one). So: the layer-route report's estimate was right; the carried GSC-24 number was the wrong
basis. No committed claim needs retraction — the penalty is now *measured*, not inferred or carried.

## 8. Next levers (hypotheses — a fresh call)

1. **Frame-level representation** (untried on typical at frame scale): attentive/GeM pooling and
   frame-QbE-DTW need a frame re-encode; the diffuse below-threshold failures are what tighter within-word
   frame alignment *could* address — the one remaining representation sub-axis. Low prior (frame-DTW lost
   on dysarthric), but not yet measured on typical.
2. **A purpose-distilled student** (RKD, C18 doubled the <2 MB student QbE) to shrink the +3.0 pp gap — if
   the ≤150 MB fallback becomes the primary shipped encoder.
3. **Device-validate the teacher** (wavlm-large INT8 latency/size on a target device) — closes the §1
   deployability caveat that C3 currently de-risks.

**Artifacts:** `t8_vocab_diag.py`, `t9_verifier_gsc.py`, `t10_c3_student.py`, `t11_altencoder_tail.py`,
`t12_aug_enroll.py`; evidence
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t8_vocab_diag.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t9_verifier_gsc.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t10_c3_student.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t11_altencoder_tail.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t12_aug_enroll.json`.
