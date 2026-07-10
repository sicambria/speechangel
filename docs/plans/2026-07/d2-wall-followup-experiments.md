# D2-wall follow-up — 26 pre-registered experiments (W-series)

**Status:** active (design; W0/W7/W12/N1 executed 2026-07-10 as R1/R2/R3/N1 — see Steps)

## Goal

Find an admissible lever that moves the binding D2 metric — **FRR @ FAR≤5% held-out, per severity, on the
moderate dysarthric population** — from its current wall (moderate ~58%, band <600) toward band 700+
(FRR ≤ 30% @ FAR ≤ 5%), OR prove no such voice-only lever exists and pivot to the P5 product reframe. Every
banked positive must clear ≥8pp moderate FRR reduction **at matched FAR≤5%**, preserved on a cross-gender
held-out speaker.

## Context & Constraints

Anchored on the deep-research report `docs/research/2026-07-10-move-d2-wall.md` and the Round-4 results
`docs/testing/2026-07-10_d2-wall-p1p2p3-results.md`, which ran the three top-ranked bets (P1/P2/P3) + the
Round-3 primary N1 and found **all four fail** the binding metric on moderate severity.

- **Binding metric (all experiments):** FRR @ FAR≤5%, held-out (LOFO), per severity, moderate-centered,
  **FAR-matched** — any lever whose realized held-out FAR > 5%+2pp is FAR-invalid (EVAL-007).
- **Admissibility (hard filter):** on-device, speaker-dependent, language/vocabulary-agnostic, few-shot
  enrollment, deterministic (no LLM/cloud), NNAPI/INT8 ≤~150 MB.
- **Corpus discipline:** real dysarthric only (TORGO now; UASpeech/EasyCall/Nemours on acquisition, W25/W26);
  no simulator (S22 unfit). Held-out **speaker**; for any learned linear transform a **cross-gender transfer**
  guard (train F → test M) — the condition that refuted G1 (EVAL-006).
- **Governing insight (Round-4, EVAL-007):** separability is mediocre everywhere (unbiased all-genuine AUC
  ~0.65 moderate; best lever = backend at 0.72; frame-DTW *lowers* it) and **AUC is a poor proxy for the
  binding tail** — the backend's real +0.07 central-AUC gain bought only +0.6/+1.3pp FRR@FAR≤5%, because the
  operating point is set by the worst confusors, not the mean. **Prioritize tail-direct levers (T-cluster) and
  the P5 reframe; adjudicate on FRR@FAR (all-genuine AUC only as a diagnostic).**

### What is already settled — DO NOT re-run

| Refuted / null | Where | Reason |
|---|---|---|
| Front-end swaps (MFCC↔ΔΔ) | round-2 | within sampling error |
| SSL encoder upgrade as a D2 fix | ceiling study | encoder-invariant; lifts accuracy not the tail |
| Per-user within-word whitening (G1) | round-2/3 | refuted on held-out males p=0.63 |
| Nuisance-subspace projection (G3) | round-2 | train/test leakage artifact |
| Confusion-aware vocab (N2) | round-3 | rep-limited negative |
| **LDA+WCCN backend (P2 = W7)** | **Round-4 R2** | **killed +0.6/+1.3pp; unbiased AUC 0.65→0.72 but tail flat** |
| **frame-trajectory DTW (P3 = W0)** | **Round-4 R1** | **not-banked −1.7pp; unbiased AUC 0.65→0.61 (lower)** |
| **AS/S-norm + per-cmd thresholds (P1 = W12)** | **Round-4 R3** | **null at matched FAR; per-cmd "gain" was FAR-inflation to 24%** |

## Approach

Six clusters, run in priority order T → P5 → (one representative each of P2'/P3'/P1') → P4, gated by the
acquisition of a larger corpus (W25) before any positive is banked. Each experiment carries a pre-registered
success and kill threshold expressed against the binding FRR@FAR metric.

## Steps

### Cluster T — TAIL-DIRECT (highest priority; motivated by EVAL-007)

- **W1 — Per-confusor-pair thresholds.** Accept boundary per ordered pair (w, top-confusor w′) from
  enrollment scores. *Success:* ≥8pp moderate ΔFRR @ FAR≤5%. *Kill:* <3pp or FAR-invalid.
- **W2 — Worst-confusor-aware enrollment.** Mine each command's nearest in-vocab confusor; request 1–2 extra
  targeted reps. *Success:* ≥8pp moderate ΔFRR @ FAR≤5%. *Kill:* <3pp.
- **W3 — Tail-loss metric head** (soft-quantile / minDCF surrogate on the 5th-impostor-percentile margin).
  Cross-gender held-out. *Success:* ≥8pp moderate ΔFRR preserved F→M. *Kill:* <3pp or transfer-vanish.
  **HIGH self-deception risk (learned-transform family); NOT-BANKED until transfer holds.**
- **W4 — Enrollment-time confusor simulation for calibration** (time-warp / partial-splice the user's own
  other reps as hard negatives). *Success:* ≥5pp moderate ΔFRR @ FAR≤5%. *Kill:* <1pp.
- **W5 — Reject-option at the 5th percentile (conformal tail)** (Johansson/Löfström MDAI 2023). *Success:*
  ≥8pp fewer hard rejects OR ≥8pp ΔFRR with abstain-rate <15% @ FAR≤5%. *Kill:* abstain >30% for <3pp.
- **W6 — Quantization-error score calibration for DTW-KWS** (Wilkinghoff 2025 arXiv:2510.15432). *Success:*
  ≥5pp moderate ΔFRR @ FAR≤5%. *Kill:* <1pp.

### Cluster P5 — REFRAME (product route; own success definition)

- **W20 — Abstain+confirm turn** (three outcomes via W5). *Success:* moderate effective task-success ≥85%
  with confirm-turn rate <20% at FAR≤5%. Absorbs SPRT multi-attempt (K25/Q).
- **W21 — Per-severity operating points** (mild→FAR≤5% direct; moderate→relaxed FAR+confirm; severe→abstain).
  *Success:* deployable policy with stated FRR/FAR/confirm-rate per severity cell.
- **W22 — Complementary-modality fusion (severe tail)** (voice + switch/dwell/gaze). *Success:* severe
  effective task-success ≥85% @ FAR≤5%.
- **W23 — Severity auto-detection at enrollment** (within-word scatter / fisher ratio). *Success:* ≥80%
  agreement with the D2-band label on held-out speakers.

### Cluster P2' — trainable backends (LDA+WCCN killed on MAGNITUDE, not transfer)

> **Correct kill-guard (Round-4 correction):** unlike G1, the LDA+WCCN backend's central-AUC gain *does*
> transfer cross-gender (F→M, +0.07 on every held-out speaker) — it dies because 0.72 ≪ the ~0.95 AUC needed
> for the tail to move, i.e. **insufficiency, not the G1 transfer artifact**. So for W8–W11 the binding
> kill-criterion is "did FRR@FAR≤5% move ≥8pp on moderate," NOT "did it survive cross-gender" (it will).
> Keep the cross-gender report as a diagnostic, but do not let a passing transfer test read as a win.

- **W7 — LDA+WCCN.** ✅ DONE (R2) — KILLED (transfer passed; magnitude/tail failed).
- **W8 — Two-covariance / constrained PLDA** (Wang IS2022). *Success:* ≥8pp moderate ΔFRR @ FAR≤5%,
  transfer-preserved. *Kill:* <3pp or transfer-vanish.
- **W9 — Neural PLDA (NPLDA)** (Ramoji 2020) on a DCF surrogate (targets the tail). *Success/kill:* as W8.
- **W10 — DCA-PLDA robust backend** (Ferrer 2022). *Success/kill:* as W8.
- **W11 — Prototypical / centroid metric head** (Wang ICASSP2019). *Success/kill:* as W8.

### Cluster P3' — trajectory / multi-vector (frame-DTW not-banked)

- **W16 — Multi-sample DTW cost-tensor** (Wilkinghoff 2024 arXiv:2404.14903), joint over all exemplars.
  *Success:* ≥8pp moderate ΔFRR @ FAR≤5% vs pooled. *Kill:* <3pp or worse.
- **W17 — TACos temporally-structured embeddings** (Wilkinghoff ICASSP2024). *Success/kill:* as W16.
- **W18 — LPM latent-KWS embeddings** (Lea/Apple IS2023) — frame-DTW on a keyword-spotter latent space, not
  WavLM L14. *Success:* ≥8pp moderate ΔFRR @ FAR≤5%. *Kill:* <3pp.
- **W19 — Segmental posteriorgram DTW** (Zhang&Glass 2009; Rudzicz 2012). *Success/kill:* as W16; feasibility-
  gate first.

### Cluster P1' — score-domain (AS-norm + per-cmd null at matched FAR)

- **W12 — AS/S-norm + per-command thresholds.** ✅ DONE (R3) — NULL at matched FAR.
- **W13 — QMF non-monotonic quality calibration** (Thienpondt 2020) — the one P1 sub-lever not ruled out by
  monotone-invariance. *Success:* ≥5pp moderate ΔFRR @ FAR≤5%. *Kill:* <1pp.
- **W14 — Phonetic-richness calibration** (Pindrop 2024). *Success/kill:* as W13.
- **W15 — Per-user personalized threshold from enrollment quantile.** FAR-matched per user. *Success:* ≥5pp
  moderate ΔFRR @ FAR≤5%. *Kill:* <1pp or FAR-invalid.

### Cluster P4 — enrollment-side (low-ceiling; run only stacked on a T/P5 win)

- **W24 — Variance-aware exemplar selection vs augmentation** (child-ASV analogue Aziz 2025). *Success:* ≥5pp
  moderate ΔFRR @ FAR≤5% at fixed rep count. *Kill:* <1pp.

### Enabling — corpus acquisition (currently BLOCKED)

- **W25 — UASpeech acquisition + embedding** (fixes n=8 per-severity single-speaker fragility). Blocks all
  generalization claims.
- **W26 — EasyCall (Italian) acquisition** (language-independence + LPM's public benchmark for W18).

## Definition of Done

- **Primary (bank or refute):** for each executed W-experiment, an adjudicated verdict on the binding metric
  **stated as both FRR and the realized FAR** — e.g. "moderate FRR 58%→X% @ realized FAR ≤5%," never a bare
  accuracy %. A lever is BANKED only at ≥8pp moderate FRR reduction @ matched FAR≤5%, cross-gender preserved;
  otherwise NULL/KILLED/NOT-BANKED with numbers.
- **Program-level:** if no T-cluster lever clears ≥8pp moderate FRR @ FAR≤5%, the voice-only D2 wall is
  declared information-theoretic for moderate and the program commits to P5 (W20–W23) with a per-severity
  policy specifying FRR + FAR + confirm-rate per cell.
- Each executed experiment lands a committed evidence JSON under `scripts/eval/ssl_frontend_spike/_ceiling_cache/`
  and a report-table row.

## Risks & Mitigations

- **False positive via FAR inflation** (the R3 trap) → every verdict prints realized held-out FAR; FAR-invalid
  levers are excluded (EVAL-007).
- **Same-family self-deception** (P2'/P3' extrapolate external-lit priors that lost twice in-house) → strict
  cross-gender transfer guard; run at most one representative each (W8, W16/W18) before spending more.
- **n=8 single-speaker fragility** (EVAL-005/006) → acquire UASpeech (W25) before banking any positive;
  per-severity cells reported with raw counts.
- **Simulator contamination** → real corpora only; S22 unfit, excluded.

## Test & Verification

- Verdict metric computed by the R-series harnesses (`scripts/eval/ssl_frontend_spike/r1_frame_dtw_d2.py`,
  `r2_backend_d2.py`, `r3_scorenorm_d2.py`, `n1_stack_d2.py`), which print FRR **and realized FAR** per
  severity and flag FAR-invalid levers.
- Every banked positive requires a fresh, pre-registered, FAR-matched confirmation on a held-out speaker
  (EVAL-002/003) — no headlining a mined variant.
- Reproducibility: cached embeddings (`wavlm-large.npz`, `male_wavlm_large.npz`, `large_frames_L14.npz`,
  `male_frames_L14.npz`) + committed evidence JSON under `scripts/eval/ssl_frontend_spike/_ceiling_cache/`.

## Execution policy

1. Run T-cluster (W1–W6) first — the only cluster whose theory targets the binding tail. If none clears the
   bar, pivot entirely to P5 (W20–W23).
2. P2'/P3' are confirmations of external-lit extrapolations that lost twice in-house; one representative each.
3. Acquire UASpeech (W25) before banking any positive.
