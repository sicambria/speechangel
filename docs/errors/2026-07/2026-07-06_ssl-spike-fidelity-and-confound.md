# Incident — SSL-spike measurement: pipeline-fidelity gap + confounded A/B

**Date:** 2026-07-06 · **Area:** eval / methodology · **Severity:** near-miss (caught before any claim shipped)
**Trigger:** Building the CP-1 SSL-front-end ceiling spike harness against the committed TORGO protocol.

## Summary

Two measurement errors, both caught before any number was banked, in the CP-1 spike
(`docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`):

1. **Fidelity gap (~15 min).** The first Python MFCC-DTW harness scored F01 rank-1 **37.5%** vs the
   committed **68.8%**, with *inverted* separability (OOV closer than the true word, AUC 0.39). Cause: it
   ran MFCC on the **whole wav**; the committed pipeline **VAD-trims** (`EnergyVad.trim`) both enrollment
   and query audio before MFCC. Untrimmed TORGO head-mic silence dominated the DTW. After replicating the
   VAD trim, the harness reproduced the committed report **to the decimal** (F01 68.8%, F03 53.5%, F04
   54.0%, ALL 55.4%). Two earlier fixes (orthonormal DCT scaling; first-order `(next-prev)/2` delta) were
   necessary but *not sufficient* — they changed distance scale without fixing ranking; only VAD did.

2. **Confounded A/B (caught by advisor).** The headline first compared MFCC-**DTW** vs WavLM-**pooled-
   cosine** — two variables (representation *and* matcher) moved together. The sharper decomposition
   (representation × matcher 2×2) shows the win is the **matcher/embedding interaction**, not the
   front-end: WavLM-under-DTW *ties* MFCC-DTW; MFCC-under-pooling *drops* to 39.3%. Publishing "swap the
   MFCC front-end" would have been a wrong causal claim.

## Root Cause

1. Reproducing a headline metric by re-implementing only the *named* stage (MFCC + DTW) instead of the
   **whole committed pipeline** (VAD-trim → MFCC → CMN → DTW). Silence handling is invisible in the
   headline yet dominant in the result.
2. Attributing an end-to-end delta to one factor when the change moved **two** factors at once — the
   classic confound. The rank-1 lift was real; the *cause* was mis-assigned until the 2×2 isolated it.

## Rerun Analysis

- **What caught #1:** a pre-declared **fidelity gate** (reproduce the committed number within a few
  points before trusting any comparison). 37.5% ≠ 68.8% failed it loudly; the inverted separability
  (AUC<0.5) was the diagnostic that pointed at silence/trimming, not features.
- **What caught #2:** the advisor call *before* writing the claim; and the tell was already in the data
  (WavLM `frames_norm`-under-DTW ≈ MFCC-DTW on F01), unread until the 2×2 was run.

## Prevention

- **Reproduce the whole pipeline, gate on the committed number.** Any off-device re-implementation of an
  in-repo metric must reproduce the committed value (±few pts) before its *deltas* are trusted. Make the
  fidelity check the first output, not an afterthought.
- **Change one variable per comparison; decompose confounds with the full factorial corner.** When a win
  moves both representation and matcher, run the missing 2×2 cell before assigning cause. → **EVAL-004**.
- **Separability AUC<0.5 is a silence/trimming smell**, not a weak-feature result — check the front-end
  pipeline (VAD, endpointing) first.

## Guardrail Updates

- New rule **EVAL-004** added to `docs/ai/ACTIVE_DEV_RULES.md` (decompose confounded representation×matcher
  comparisons; reproduce-the-pipeline fidelity gate).
- Reference implementation of the fidelity gate + 2×2 decomposition:
  `scripts/eval/ssl_frontend_spike/harness.py` (VAD trim = `energy_vad_trim`) and
  `scripts/eval/ssl_frontend_spike/matcher2x2.py`.
- `scripts/eval/ssl_frontend_spike/README.md` documents "reproduce the committed baseline to the decimal"
  as the DoD-1 fidelity gate.

## Planning Integration

The spike plan (`docs/plans/2026-07/cp1-ssl-frontend-ceiling-spike.md`) already carried DoD-1 as a
fidelity gate and (post-advisor) the 2×2 decomposition — both are now standing template items for any
future "new front-end / new matcher" measurement plan.

## Shift-Left Decision

- **Rule:** add — **EVAL-004** ("reproduce the whole pipeline and hit the committed number within a few
  points before trusting any delta; change one variable per comparison and close the 2×2 before assigning
  cause"). Both errors were caught in-spike (before banking), so this is a **near-miss**, not a regression.
- **Guardrail/automation:** skip a new script — a `[measure-only]` scratch harness (TORGO uncommitted) is
  off the CI path, so a lint has no durable target. The rule + the reference implementations are the
  durable artifacts; the enforcement is the advisor-gate + fidelity-gate steps in the spike/planmax loop.
- **Automation Links:** `scripts/eval/ssl_frontend_spike/harness.py` (`energy_vad_trim` + decimal
  fidelity reproduction) and `scripts/eval/ssl_frontend_spike/matcher2x2.py` (the representation×matcher
  decomposition) — the reference implementations EVAL-004 points at.

## Automation Follow-Up

None mechanized (measure-only harness, not on the CI path — TORGO is uncommitted). EVAL-004 is advisory,
enforced by the reference implementations above and the advisor-gate step in the spike/planmax loop.
