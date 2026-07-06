# CP-1 spike — Is the MFCC front-end the accuracy bottleneck? (SSL representation ceiling probe)

- **Status:** done (2026-07-06 — GO verdict; report `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`).
  Result: best-classic MFCC-DTW 55.4% → best-learned WavLM-L12 pooled-cosine **71.9% rank-1** (−37% rel
  error aggregate, **≥50% on the F01/F04 deployment slice**, McNemar p=2×10⁻⁶). **Sharpened by the 2×2
  decomposition:** the lever is a **fixed-dim QbE embedding + cosine prototypes** (the dormant
  `QbeEncoder` seam), NOT a front-end swap (WavLM-under-DTW ties MFCC; MFCC-under-pooling drops to 39.3%).
  CP-2 rejection wall remains binding (FRR@FAR≤5% only 78.3%→66.3%). Next: distill to a ~1–2M student.
- **Bucket:** measure-only (off-device Python; touches no app code, ships nothing).
- **Serves:** ROADMAP **CP-1** (learned encoder vs MFCC-DTW) + **R-SOTA-1**; first read on **CP-2** margin.
- **Advisor-gated:** yes (2026-07-06 — approved as a lightweight spike; a second call caught the
  representation×matcher confound before any claim was written → EVAL-004).

## Goal

Answer one question with a measurable DoD: on real dysarthric 1-shot speaker-dependent recognition
(TORGO F01/F03/F04), does swapping the **MFCC front-end for a frozen self-supervised speech encoder**
(wav2vec2 / WavLM / HuBERT) — everything else held identical — materially beat the shipped MFCC-DTW
baseline (rank-1 55.4% / FRR 78.3%), or is the front-end *not* the bottleneck? "Way better than current"
is pre-defined as a **≥50% relative reduction in rank-1 error** (rank-1 ≥77.7% aggregate) with paired
significance — see Test & Verification.

## Context & Constraints

- **Why first (no-suboptimization):** the shipped MFCC-DTW core is ~1–3 orders of magnitude from
  deployable and the constraint-matched SOTA point is ZP-KWS ≈29–33% FRR@1%FAR. Chasing MFCC-DTW
  threshold/template tweaks is sub-optimization while the *representation* is the prime suspect.
- **This is a ceiling/diagnostic probe, NOT a shippable artifact.** wav2vec2/WavLM-base are English-
  pretrained, ~95M params. A win localizes the bottleneck and greenlights a *small/distilled* build; it
  does not mean "ship WavLM". Stated up front (EVAL-002/003 honesty).
- **Constraint box (CP-1):** frozen-SSL + template-match preserves language-independence + 1-shot
  arbitrary-word enrollment (no lexicon), so the probe stays inside CP-1's gate. Language-independence
  itself is **untestable on English TORGO** — recorded as such.

## Approach

Same-harness A/B where the front-end is the only variable. A Python reimplementation of the committed
`TorgoEval` protocol (speaker-dependent, k=5 round-robin folds, `EnergyVad`-trim → front-end → banded
length-normalised DTW, threshold-free rank-1, leave-one-fold-out global-threshold FRR@FAR). Arms:
classic (MFCC, LPCC) and frozen learned (wav2vec2/WavLM/HuBERT, one layer, mean / stats-pool / frames).
Because the naive comparison moves representation *and* matcher together, also run the **representation ×
matcher 2×2** to isolate cause (EVAL-004).

## Steps

1. Front-end-agnostic harness (numpy + stdlib `wave`; not blocked on torch).
2. **Fidelity gate:** reproduce the committed MFCC-DTW report within a few points before trusting any
   delta (achieved: to the decimal — 55.4% agg, per-speaker exact).
3. Classic baselines: MFCC-DTW, LPCC-DTW.
4. Learned arms: sweep {wav2vec2, WavLM, HuBERT} × layer × {mean, frames_norm} to find the best config.
5. 2×2 decomposition (MFCC/WavLM × DTW/stats-pool-cosine) to assign cause.
6. Paired McNemar (per speaker + aggregate) for the winner vs MFCC-DTW.
7. Rejection first-read: genuine-vs-impostor separability (d′/AUC) for both arms (CP-2 seed).
8. Ceiling: WavLM-large / XLSR (robustness only; do not gate banking).
9. Report win **or** dead-end + the next-step decision; commit the harness.

## Risks & Mitigations

- **torch@py3.14 wheel absent** → use the pinned `research/.venv` (torch 2.12.1) or onnxruntime; classic
  arms need no torch. (Resolved: `research/.venv` used for SSL arms.)
- **Fold-protocol drift from the JVM** → keep fold logic dead-simple; A/B validity needs internal
  consistency, not JVM identity; the fidelity gate catches gross drift.
- **CPU-only SSL forward passes slow** → cache one forward pass per utterance; subsample only if needed,
  held constant across arms.
- **Confounded attribution** → the 2×2 decomposition + EVAL-004 (do not claim cause from a 2-variable
  change).

## Definition of Done

Measured on real TORGO, held-out (EVAL-002), at a **matched FAR** operating point — never a bare %:

- **Primary (discrimination):** threshold-free **rank-1** ≥ 77.7% aggregate (≥50% rel. error cut from the
  55.4% baseline), with **McNemar p<0.05** favoring the encoder in ≥2/3 speakers.
- **Deployability (FRR + FAR):** report held-out **FRR at FAR ≤ 5%** for every arm (baseline 78.3% @ FAR
  5.1%); a win must *lower FRR at matched FAR*, and the report must state whether the always-on ambient
  **FAR/hour** wall (CP-2) is addressed (it is not — this spike measures per-utterance OOV FAR only).
- **Rejection margin:** genuine-vs-impostor separability (d′ / ROC-AUC) reported for baseline and encoder.
- **Outcome:** GO (with the sharpened QbE-embedding target) — MET on the deployment slice, FRR@FAR≤5%
  moved 78.3%→66.3%, AUC 0.572→0.717; full numbers in `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`.

## Test & Verification

- **DoD-1 (harness fidelity): MET** — Python MFCC-DTW reproduces the committed 55.4% aggregate (and
  per-speaker) to the decimal; else the harness, not the encoder, is suspect.
- **DoD-2 (primary "way better" = ≥50% relative rank-1-error reduction):** MET on the deployment slice
  (F01 50.0%, F04 60.9%), 37.0% aggregate (F03 77-word tail 29.0%) — reported honestly, no goalpost
  move; win also requires **McNemar p<0.05 favoring the encoder in ≥2/3 speakers** (MET: F03 \*\*, F04 \*\*\*).
- **DoD-3 (rejection first read):** report SSL-vs-MFCC separability (d′, AUC) — no pass/fail gate; feeds
  the CP-2 hypothesis (AUC 0.572→0.717; FRR@FAR≤5% 78.3%→66.3%, wall still binding).
- **Dead-end criterion:** encoder not distinguishable from MFCC (McNemar n.s. all speakers) ⇒ record
  "front-end swap negligible," redirect. (Not triggered — decisive GO.)
- **Deliverables:** `scripts/eval/ssl_frontend_spike/` (committed harness) +
  `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md` (report) + a follow-on CP-1 build plan
  (distill-to-small QbE encoder).
