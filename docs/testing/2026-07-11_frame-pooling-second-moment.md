# The last untested representation axis breaks the mean-pooled wall: frame-level second-moment pooling

**Date:** 2026-07-11 · **Journey:** "next 10 experiments toward typical-900; the one untested
representation axis = frame-level pooling / QbE-DTW." · **Corpus:** GSC-19 (19 speakers × 8 words × 6
reps, npos=912), identical a5 manifest. · **Binding metric (EVAL-007):** typical D2 = held-out (LOFO)
FRR @ FAR≤5%, FAR-matched. **Bands (DomainBands.kt spec 2):** 900 = ≤5%, 800 = ≤15%.

> **Headline.** The pre-registered primary **loses**, and the *other* half of the same axis **wins**.
> **(1) Frame-QbE-DTW (H1) is REFUTED** — DTW alignment over frame-level SSL embeddings is band 800 at
> every layer (L6/9/12/15 = 13.8/13.6/12.1/12.0%; matched-FAR McNemar b=54–82 vs c=0–1, p<1e-11 in the
> *wrong* direction) and does **not** tighten the below-threshold tail it was hypothesized to fix.
> **(2) But frame-level *second-moment pooling* breaks the wall.** Statistics pooling (mean⊕std of the
> L12 frames, cosine 1-NN — a parameter-free, deploy-free drop-in) lifts the teacher **5.81% → 4.71%
> FRR @ FAR 3.55%** (53 → 43 false-rejects, **−19% relative**), matched-FAR McNemar **b=1/c=19,
> p=1.4e-4**, dominant across FAR 2–5%, per-speaker **6 better / 1 worse / 12 tie**. It **replicates on
> the deployable distilhubert student** (9.32% → 8.22%, McNemar b=1/c=34, p=6e-8). An ablation nails the
> mechanism: **std-alone at the *same* 1024 dims beats mean** (distilhubert L2 6.36% vs 9.32%), while
> max/gem pooling lose — so the lever is the **second moment**, not dimensionality and not generic
> frame-awareness. **EVAL-008 is vindicated** (a different pooling of the *same frames* broke the
> "mean-pooled-embedding wall" — the substrate *was* the wall). **Banked:** the second-moment lever,
> scoped to GSC-19 × 2 encoders. **Not banked into the composite:** the teacher's 4.71% clears the 900
> line by only **~3 false-rejects on one 19-speaker cohort** — the *improvement* is banked, the discrete
> **900 label is provisional**; the deployable student is band **800**, so the shipped composite **stays
> 800**.

---

## 1. Target framing and baseline (fidelity-anchored)

Baseline = teacher **wavlm-large L12 / K5, mean-pool + cosine 1-NN = 5.81% FRR @ FAR 3.89%, npos=912**
(reproduced by `f0_pin.py`). Hard tail: 98ea0818 27%, 2aca1e72 25%, c1d39ce8 19%. The t8 diagnostic
found the false-rejects are **diffuse**: 59% below-threshold (genuine word ranked #1 but distance >
accept threshold — within-word scatter), 41% wrong-word. AUC 0.988 — a *localized* hard-voice wall, not
the dysarthric information-theoretic one. Five prior axes were closed, **all on mean-pooled embeddings**
(layer, vocab, decision-fn, encoder-objective, augmentation — EVAL-008); the one untested representation
axis was **frame-level pooling** (attentive/GeM pooling + frame-QbE-DTW). Frame-DTW *lost* on dysarthric
TORGO but was **never measured on typical** — this journey measures it.

## 2. Fidelity gate (EVAL-004) — three anchors, all reproduce 5.81%/912

- **F0(b) speaker set:** `a5.kcurve_speaker` cosine at L12/K5 = 5.81% @ FAR 3.89%, npos=912 (19
  speakers; `pick_speakers` returns exactly 19 — the `N_SPK=24` cap is non-binding, so these are the
  *entire* qualifying cohort).
- **F0(a) DP code:** the frame-DTW harness fed a **single mean-pooled frame** per clip → DP collapses to
  the local cost, ranking == cosine → **5.81% @ 3.89% / 912** exactly (isolates the DP from the pooling).
- **Paired mean-pool arm** inside every confirm run reproduces 5.81%/3.89% verbatim.

Preprocessing (VAD-trim, pad-to-1520, zero-mean/unit-var) is byte-identical to `a5.embed_net`; the only
change is `.mean(0)+L2` → per-frame L2-norm (frames) or mean⊕std (pooling).

## 3. H1 (pre-registered primary) — Frame-QbE-DTW is REFUTED

`frame_qbe.py e1 <L>`: `pool=frames_norm`, banded length-normalized cosine-DTW, min-over-K, **identical**
speakers/words/folds/K/threshold/FAR — only mean-pool+cosine → frame-DTW changes.

| layer | frame-DTW FRR | FAR | band | matched-FAR McNemar (vs mean-pool) |
|---|--:|--:|:--:|---|
| L6 | 13.82% | 4.4% | 800 | b=82 c=0 p=4e-19 |
| L9 | 13.60% | 4.2% | 800 | b=68 c=1 p=2e-15 |
| **L12** | **12.06%** | 4.1% | 800 | b=62 c=1 p=4e-14 |
| L15 | 11.95% | 4.1% | 800 | b=54 c=1 p=2e-12 |

Every hard speaker gets **worse** (98ea0818 27→54%, 2aca1e72 25→29%). The below-threshold split is
**unchanged** at every layer (53–58% vs baseline 59%) — DTW alignment does **not** preferentially tighten
the within-word tail it was meant to. The pre-registered mechanism fails across the whole depth range
where phonetic structure lives. **H1 refuted** (a valid, banked negative, EVAL-003).

## 4. The pivot — the OTHER half of the axis (frame-aware pooling)

`frame_qbe.py e4 <L>`: keep the frames, replace mean-pool with a frame-aware pooling (still one vector +
cosine). Aggregate FRR@FAR≤5%, K5:

| pooling | dim | wavlm-large L12 | distilhubert L2 |
|---|--:|--:|--:|
| mean (baseline) | H | 5.70%¹ | 9.32% |
| **std-alone** | H | 5.92% | **6.36%** |
| **mean⊕std** | 2H | **4.71%** | 8.22% |
| max-abs | H | 9.54% | — |
| gem (p=3) | H | 9.65% | — |

¹ frames_norm-mean ≈ the raw mean-pool baseline (5.81%); the confirm arms below use the *real* 5.81%
baseline. **max/gem lose**; the win is specifically the **first+second moment**.

## 5. Confirmation of the mined lever (EVAL-003 fresh, FAR-matched)

`frame_qbe.py confirm meanstd 12 wavlm_large` and `... 2 distilhubert 2`. Both arms share wav keys;
McNemar re-thresholds each arm to a **common realized FAR** (EVAL-007).

**Teacher (wavlm-large L12), mean⊕std vs shipped 5.81%:**
- Held-out **4.71% @ FAR 3.55%** (53 → 43 FRs). Per-speaker **6 better / 1 worse / 12 tie**. All three
  below-threshold hard speakers improve (2aca1e72 25→17%, c1d39ce8 19→15%, 98ea0818 27→21%); only
  893705bb regresses (10→15%).
- **Matched-FAR McNemar, curve-dominant** (EVAL-005 — not one operating point): @2% b=0/c=18 p=6e-5;
  @3.89% b=1/c=19 p=1.4e-4; @5% b=1/c=19 p=1.4e-4; @8% b=2/c=8 ns (arms converge at loose FAR, expected).

**Student (distilhubert L2), mean⊕std vs shipped 9.32% (the deployable ≤150 MB fallback):**
- Held-out **8.22% @ FAR 3.72%** (85 → 75 FRs), band 800. Per-speaker **6 better / 2 worse / 11 tie**.
- Matched-FAR McNemar dominant at **every** FAR point: @2% b=1/c=35 p=4e-8; @3.89% b=1/c=34 p=6e-8;
  @5% b=4/c=29 p=3e-5; @8% b=3/c=15 p=1e-2. Same direction as the teacher → **encoder-general**.

**Ablation — moment, not dimensionality (the load-bearing check):** std-alone is **1024-dim, the same as
mean**, yet beats mean on the student (distilhubert L2 6.36% vs 9.32%, L1 8.99% vs 11.18%) and ties it on
the teacher; max/gem (also 1024, also frame-aware) lose. And `mean⊕mean` is a **cosine identity to mean
after renorm**, so the 2048-dim mean⊕std win is not a width artifact. ⇒ the active ingredient is the
**frame-level second moment** (within-word dispersion the mean discards). The t8 diagnostic pointed here
(59% below-threshold = within-word scatter) — the *mechanism* was right; DTW alignment was the wrong tool,
std the right one.

**Encoder-inconsistency (kept honest):** the *best variant* flips by encoder — mean⊕std best on
wavlm-large (adding the mean helps); std-alone best on distilhubert (adding the mean *hurts*, 6.36→8.22).
Both support "incorporate the second moment"; the specific variant is **NOT-banked per-encoder tuning**.

## 6. Banked / not-banked / scope

- **BANKED (measured):** **frame-level second-moment (std) pooling beats mean-only pooling on typical
  D2**, on both wavlm-large and distilhubert, FAR-matched-significant across FAR 2–5%, mechanism-verified
  (moment not dims, not generic frame-awareness), cross-encoder-general. A **parameter-free, deploy-free
  drop-in** (replace mean-pool with mean⊕std / std of the frames the encoder already emits; no DTW, no
  new model, no retrain — the only cost is a 2×-wide template vector).
- **BANKED (negative):** **frame-QbE-DTW is refuted** for typical D2 — worse at every layer, wrong-word
  and below-threshold both, McNemar wrong-direction p<1e-11.
- **NOT banked / provisional (the label, not the improvement):** the teacher's **4.71% clears the 900
  line (45.6 FRs) by only ~2.6 FRs on a single 19-speaker cohort** — a knife-edge discrete label. The
  **−10-FR / −19% improvement is banked**; the **"typical D2 = 900" label is provisional** pending
  cross-cohort + deployable-student confirmation. The **composite stays band 800** (`sota-typical-800-900
  -split` unchanged): the deployable student is band **800** (8.22%), and the teacher's on-device INT8
  deployability remains device-unvalidated (the same caveat the 5.81% carried).
- **NOT banked (mined tuning):** per-encoder best variant (meanstd vs std-alone), best layer.
- **Scope:** GSC-19 (19 speakers — the entire qualifying cohort; no disjoint ≥15-speaker set exists at a
  relaxed bar, only 6) × 2 encoders. Cross-cohort is a **named next lever**, not run.

## 7. Prior art and next levers

mean+std **statistics pooling is standard in speaker verification** (x-vector statistics pooling) — this
is not a lucky trick but a **known-good pooling never tested in this QbE / few-shot-enrollment setting**,
and it works. That also names the SOTA continuation: **attentive statistics pooling** (learned frame
weights over mean+std) is where this axis tops out. Next levers: (1) **attentive/learned statistics
pooling**; (2) **cross-cohort / relaxed-speaker replication**; (3) **production-Kotlin reproduction** of
std pooling in `core:matching` (the recognizer currently mean-pools); (4) per-encoder std-vs-meanstd
confirm; (5) **second-moment pooling on the dysarthric D2 tail** (does the moment help the AUC-0.65 wall,
or is that one genuinely information-theoretic?).

## 8. EVAL-008 — vindicated, not upgraded

The five closed axes shared **one substrate: mean-pooled single-vector embeddings**. A different pooling
of the **same frames** broke the wall — so the substrate *was* the wall, exactly as EVAL-008 warned
against generalizing. **Do not read this program as "representation wall closed."** The frame-level
representation axis is now **open and productive**. The rule stands and is strengthened: *a negative
across N levers that share a pooling bounds only that pooling.*

## 9. Method integrity

- **EVAL-004:** three fidelity anchors reproduce 5.81%/912; change-one-variable (only the matcher/pooling
  differs; identical manifest/folds/K/threshold).
- **EVAL-003:** H1 pre-registered and refuted; the winning pooling was **mined** from an exploratory
  family and held NOT-banked until a **fresh cross-encoder FAR-matched confirmation** (distilhubert) +
  the moment-vs-dims ablation both passed.
- **EVAL-007:** adjudicated on FRR@matched-FAR (McNemar re-thresholds both arms to a common realized
  FAR); AUC not used as the verdict.
- **EVAL-005:** curve-level (FAR 2/3.89/5/8%), ≥maj-fold direction, both encoders agree — not a single
  operating-point extreme; the discrete band-900 label explicitly flagged as knife-edge (~3 FRs).

**Artifacts:** `frame_qbe.py` (build/f0a/e1/e4/confirm), `f0_pin.py`, `PREREG_frame_qbe.md`; evidence
`_ceiling_cache/frame_qbe_e1_L{6,9,12,15}.json`, `frame_qbe_e4_L{9,12}.json`,
`frame_qbe_confirm_wavlm_large_meanstd_L12.json`, `frame_qbe_confirm_distilhubert_meanstd_L2.json`;
frame caches `gsc_wavlm_large_frames_L{6,9,12,15}.npz`, `gsc_distilhubert_frames_L{1,2}.npz`.
