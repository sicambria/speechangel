# Incident — a tail operating-point metric mis-headlined as "robust" before the control refuted it

**Date:** 2026-07-06 · **Area:** CP-2 in-regime ambient-FA/hr spike (`scripts/eval/ssl_frontend_spike/`)
· **Severity:** methodological (no shipped code touched; a near-banked claim was retracted before commit).
- **Trigger:** Cross-speaker control run (FC01) flipped the WavLM tail direction that F01 alone had
  suggested, catching the single-speaker headline before it was banked.
- **Automation Links:** `scripts/eval/ssl_frontend_spike/in_regime.py`,
  `scripts/eval/ssl_frontend_spike/inregime_paired.py`.

## Summary

Running the WavLM-embedding arm of the CP-2 in-regime spike on **one** speaker (F01) produced a striking
result: the tail wall — "FA/hr needed for 95% detection" — dropped from **~24 → 5.0** (≈5×), and
det@5FA/hr rose 87.5%→96.9%. This was written into the results table and initially framed (with advisor
concurrence) as the **robust, low-variance headline**, with the ~0-FA/hr point relegated to "knife-edge."
The control speaker (FC01) then **refuted** it: WavLM's tail *regressed* (95% det 3.0→6.0 FA/hr;
det@5FA/hr **100%→70.6%**). The tail effect does not exist in either direction as a general result. It was
retracted before banking.

## Root Cause

"FA/hr for 95% detection" and "det @ ~0 FA/hr" are both **single-threshold operating points at the
extreme of the curve**, pinned by the **1–2 hardest positives** (out of ~32) and the **single nearest
background window** in ~1 h. They are therefore **high-variance**, not low-variance — the opposite of the
intuition that "a tail metric averages over many events, so it's stable." The paired significance test
(EVAL-003) was correctly queued for the ~0-FA/hr point, but **no equivalent guard was applied to the tail
metric**, and a one-speaker read was treated as sufficient to headline it.

## Rerun Analysis

The control run (`in_regime.py ssl:wavlm:12 FC01 60`) was cheap (~8 min) and decisive: it flipped the tail
direction, proving the F01 tail gain was speaker-specific noise. The paired McNemar on F01's ~0-FA/hr point
(`inregime_paired.py F01`) returned b=1/c=3, p=0.617 — a 2-utterance move, confirming the extreme-point
fragility quantitatively. Had only F01 been run, a ≈5× "tail compression" win would have been banked.

## Prevention

Before headlining **any** operating-point metric read at a curve extreme (near-zero FAR, or the FAR
required to hit a high target detection), require **≥2 speakers/folds that agree in direction**, not just a
single-speaker significance test. Prefer a **curve-area / partial-AUC** summary (averages over the sweep)
as the primary, and report extreme single-threshold points only *with* their replication status. Small-n
significance being non-significant means **underpowered / not demonstrated**, never "no effect."

## Guardrail Updates

New rule **EVAL-005** in `docs/ai/ACTIVE_DEV_RULES.md` (extreme operating-point metrics are high-variance;
require cross-speaker replication + prefer curve-area, not a single-threshold read). Reference
implementations: `scripts/eval/ssl_frontend_spike/in_regime.py` (the tail/knife-edge points) and
`inregime_paired.py` (the paired McNemar + exact-binomial that quantified the fragility). Report with the
retraction: `docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md`.

## Planning Integration

The CP-2 plan (`docs/plans/2026-07/cp2-embedding-ambient-fahr-spike.md`) now carries the banked verdict
(encoder does not close the wall) and the retraction, so the next iteration inherits the corrected framing
and does not re-chase the phantom tail win.

## Shift-Left Decision

**Decision: add.** Cross-speaker replication of extreme operating points is now a **pre-headline**
requirement (EVAL-005), moved left of the write-up step — the same "confirm before banking" discipline as
EVAL-003, applied to the metric class it did not yet cover.

## Automation Follow-Up

`in_regime.py` / `inregime_paired.py` already emit both the extreme points and enough of the curve to
compute a partial-AUC; a future addition is a curve-area summary line so the stable metric is printed
alongside the fragile ones by default (advisory, not yet built).
