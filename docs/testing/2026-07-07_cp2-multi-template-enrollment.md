# CP-2 multi-template enrollment spike — directional, small, NOT demonstrated

**Date:** 2026-07-07 · **Bucket:** measure-only · **Verdict: H1 NOT DEMONSTRATED.**
More templates per word produce a directionally-positive but tiny effect (≤5.4% relative FRR
reduction at 0.5 FA/hr, vs ≥20% target). Multi-template enrollment is a second-order lever;
the first-order lever remains embedding separability at the extreme tail.

**Harness:** `scripts/eval/ssl_frontend_spike/multi_template_enroll.py` · **Protocol:** k=5 folds,
fixed test set per fold, Monte Carlo (5 iters), WavLM-L12 pooled-cosine, 1.01h LibriSpeech bg.

## Results

| Speaker (sessions) | N=1 FRR@0.5 | N=2 FRR | N=all FRR | Δ all vs N=1 | Rel FRR |
|---|---:|---:|---:|---:|---:|
| F01 (1 session) | 25.6% | 25.6% | 25.6% | 0.0% | 0.0% |
| F03 (3 sessions) | 69.9% | 65.5% | 68.1% | +3.9% det | +5.4% |
| F04 (1 session) | 43.3% | 41.2% | 41.2% | +2.1% det | +4.8% |

**H1 (≥20% relative FRR reduction): NOT DEMONSTRATED.** The maximum observed effect is +5.4%
relative FRR reduction (F03, multi-session). Single-session speakers show near-zero gain.
The effect is directionally positive but far below the pre-registered threshold.

## What is banked

1. **Multi-template enrollment provides at most a ~5% relative FRR reduction at 0.5 FA/hr.**
   This is a second-order lever — useful but not decisive for closing the CP-2 wall.
2. **Cross-session templates help more than intra-session.** The only measurable gain is on
   F03 (the only multi-session speaker). Single-session speakers (F01, F04) show zero gain
   because all templates are acoustically similar.
3. **The fold-based protocol (k=5) is conservative** — it uses only 80% of utterances as
   enrollment, vs 99% in the all-in-LOO protocol. This underestimates the true enrollment
   scenario. The committed CP-2 all-in-LOO numbers (F01 25% FRR, F03 53.5%, F04 54.0%) are
   the correct baseline for downstream comparisons.

## Next lever

Neither per-template calibration (Stage N+1, refuted) nor multi-template enrollment (Stage N+2,
directional but small) closes the CP-2 5× FRR gap at 0.5 FA/hr. The binding constraint remains
**embedding separability at the extreme tail** — the nearest OOV/background window is too close
to in-vocab templates.

The next lever to spike: **a dual-cascade verification model** that adds a second rejection
signal beyond raw distance:
- **Length-ratio cross-verify** (from PD-DWS/LRDWWS winner): reject matches where the query
  duration differs substantially from the template duration
- **Margin-ratio filter**: reject matches where the best-vs-second-best gap is ambiguous
  (similar distances to multiple words)

A dual-cascade gate — Stage-1 (distance threshold) AND Stage-2 (length/margin) — could reject
background FAs that slip through the distance gate without rejecting genuine queries, because
background windows that happen to have similar embeddings are unlikely to also have similar
durations and unambiguous best-match margins. This is the cheapest possible verification model
to spike: it uses no trained parameters, only two additional thresholds.
