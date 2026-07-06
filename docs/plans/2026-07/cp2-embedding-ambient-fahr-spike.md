# CP-2 spike — Does the learned embedding cut FA/hour on real ambient? (the binding always-on axis)

- **Status:** active (spike; 2026-07-06 — single-keyword read strongly positive; full 6-keyword run pending).
- **Bucket:** measure-only (off-device Python; touches no app code, ships nothing).
- **Serves:** ROADMAP **CP-2 / R-SOTA-2** (the deployability wall — ~82 FA/hr today, ~160× budget) using
  the CP-1 embedding win ([[speechangel-cp1-ssl-ceiling]]).
- **Advisor-gated:** yes (2026-07-06 — the advisor's "measure CP-2 on the *ambient FA/hr* axis, not TORGO's
  per-utterance OOV FAR" correction is exactly this spike).

## Goal

The CP-1 spike showed a learned embedding cuts rank-1 error and improves separability — but on TORGO's
**per-utterance OOV FAR**, which is *not* the metric that kills always-on. The binding axis is
**false-fires per hour of continuous ambient audio**. Question: at a fixed **FA/hr**, does the WavLM
embedding detect more wake words than MFCC-DTW on a real background stream — i.e., does better
separability translate to the deployability axis? Baseline to beat: the committed Picovoice result
("0.1 FA/hr ⇒ 87.5% miss" — no viable point).

## Context & Constraints

- **Corpus:** Picovoice `wake-word-benchmark` mixed streams already on disk (`~/picovoice-benchmark/mixed`):
  6 keywords, ~20 min each (~2 h total), 40 labeled wake-word intervals per keyword; enrollment takes in
  `prepared/audio/<keyword>`.
- **Regime caveat (governs interpretation):** the benchmark has **no speaker labels**, so enroll-vs-stream
  is **cross-speaker** — out-of-design for a speaker-dependent matcher. So **absolute detection is an
  explicitly-labelled LOWER bound**; the honest comparison is **relative** (embedding vs MFCC on the same
  cross-speaker framing). The **FA/hr side is regime-independent** (background speech false-firing an
  enrolled template does not depend on speaker match), so FA/hr is the trustworthy half.

## Approach

A windowed streaming scanner (`ambient_scan.py`): enroll N=10 takes/keyword → templates; slide a 3 s
window (0.5 s hop) over each mixed stream; VAD-trim each window; feature → min distance to templates. A
firing inside a labeled interval (+guard) = detection; a firing in background (merged by a 1 s refractory)
= one FA event. Sweep the accept threshold → **detection-rate vs FA-events/hour** curve. Both arms
(MFCC-DTW, WavLM-L12 embedding-cosine) share identical enroll/window/detection logic — only feature +
distance differ.

## Steps

1. Scanner with per-window min-distance, interval-detection matching, refractory-merged FA events.
2. Single-keyword sanity (computer): MFCC vs WavLM.
3. Full 6-keyword run, both arms → aggregate detection @ {0.1, 1, 10} FA/hr + FA/hr @ 90% detection.
4. Report relative improvement; state the cross-speaker lower-bound caveat.
5. Decide: is a Stage-1 embedding wake-cascade worth building, or is rejection still the wall?

## Definition of Done

Reported as **miss-rate (FRR) at a matched false-accept-rate budget expressed as FAR = FA/hour** —
never a bare accuracy %:

- **Primary:** aggregate (6 keywords, ~240 intervals) **FRR at FA/hr ≤ 0.1** for MFCC vs WavLM; a win =
  materially lower FRR at the same (near-zero) FA/hr. Single-keyword read: MFCC FRR 0.60 → WavLM FRR 0.20
  at ~0 FA/hr (pending full aggregate).
- **Secondary:** the **FA/hour required to bring FRR below 0.10** (tail hardness) for both arms.
- **Honesty:** absolute FRR is a cross-speaker upper bound (detection lower bound); FA/hour is the
  regime-independent half; this does **not** claim a shippable always-on point (a deployable point needs
  FRR < 0.05 at FA/hr ≤ 0.5) — it measures whether the embedding *moves* the FRR-vs-FA/hour curve.
- **Outcome (pending full run):** if the FRR-halving at low FA/hour holds, a learned-embedding Stage-1
  cascade is a real CP-2 lever (feeds R-SOTA-2); if FRR stays high at low FA/hour, rejection needs a
  dedicated OOV/background model.

## Test & Verification

- **Fidelity anchor:** the MFCC arm must qualitatively reproduce the committed "no viable always-on point"
  (high FRR at low FA/hour). Single-keyword MFCC: FRR 0.60 at ~0 FA/hour ✓ (consistent with the committed
  "0.1 FA/hr ⇒ 87.5% miss", allowing for the different enrollment/window and single-keyword scope).
- **Same-scanner A/B:** MFCC and WavLM share enroll/window/detection logic, so any FRR-at-matched-FAR
  delta is attributable to the feature+distance only.
- **Metric:** FRR (miss) read at matched FA/hour for both arms; the deployable target (FRR < 0.05 @
  FAR ≤ 0.5 FA/hour) is stated as the bar this spike does *not* claim to clear.

## Risks & Mitigations

- **Cross-speaker regime** → report relative, not absolute; FA/hr is the regime-independent metric.
- **Protocol not byte-matching the JVM `PicovoiceBenchmark`** → both arms share the Python scanner, so the
  *comparison* is internally valid; anchor qualitatively to the committed "no viable point."
- **Cost** (windowed embedding over ~2 h audio) → cache one forward pass per window; 6 keywords in the
  background.
- **Detection/ FA definitions** (guard band, refractory) held identical across arms.
