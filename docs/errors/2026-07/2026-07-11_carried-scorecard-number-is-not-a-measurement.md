# Incident — a carried / hard-coded scorecard number was ranked as a composite blocker

**Date:** 2026-07-11 · **Area:** EVAL / SOTA scorecard · **Severity:** diagnosis error (no shipped-code
impact; corrected before it drove a lever) · **Rule:** EVAL-004 (extended, point 3).

- **Trigger:** a composite `min()` table ranked D5-reverb (81.4 %) and D3-ambient (~800) as 800-floor
  co-blockers alongside D2 — but grepping the producing harness showed D5 was TORGO **n=3** and D3 was a
  **hard-coded literal** (`typical_composite.py:137` prints `"~800 (dual-cascade, off-encoder)"`), i.e.
  neither was a measurement of the current wavlm-large few-shot config.
- **Automation Links:** `docs/ai/ACTIVE_DEV_RULES.md` (EVAL-004 pt 3), `scripts/audits/verify-sota-measurement.mjs`
  (candidate "no un-reconciled cross-basis ranking" check), harnesses `scripts/eval/ssl_frontend_spike/t4_gsc_channel.py`
  + `t5_gsc_ambient_fahr.py`.

## Summary

The committed typical composite reported an **800 floor as a three-way tie**: D2 (~5.6 % FRR, robust
GSC-19), **D5-reverb (81.4 %)**, and **D3-ambient (~800)**. Two of the three legs were **not comparable
measurements**: D5/D4/D6 were TORGO **control n=3** (`typical_composite.py`), and **D3 was a hard-coded
literal** — `typical_composite.py:137` prints `"D3 ambient: ~800 (dual-cascade, off-encoder)"` and the
composite injects the constant `800` (`allb = bands + [d2, 950, 800]`). Ranking these as 800-floor
co-blockers alongside the robust D2 was a **cross-corpus confound**: we had already rejected TORGO-n3 for
D2's own old 13.8 %. Re-measured on the robust basis this session, **D5 = 95.8 % (band 900)** and **D3 =
0.07 FA/hr over a real 6 h stream (band 900)** — *both legs were artifacts, not blockers.* The composite
stayed 800, but the diagnosis collapsed from "fix three domains" to "fix one un-walled domain (D2)."

## Root Cause

A scorecard aggregates per-domain bands, but **not every band is a fresh measurement of the current
config.** Some are *carried* from prior work on a different corpus/encoder, and one (D3) was a **literal
constant** never measured for the wavlm-large few-shot recognizer at all. The composite's `min()` and the
prose ranking treated all legs as equally trustworthy. A tie between domains on **different measurement
bases is uninterpretable as a ranking** — you cannot distrust a corpus for one domain and trust it for
another in the same table.

## Rerun Analysis

Reproduced by re-measurement, not by re-running the flawed path:
- **D5/D4/D6** (`t4_gsc_channel.py`): augmentation + scoring imported verbatim from `typical_composite.py`
  (fidelity gate near-automatic), applied to GSC-19. Paired within-corpus (McNemar) — reverb Δ = +2.4 pp
  (p=2.7e-5) but absolute 95.8 % → band 900. GSC clean anchor 98.2 % vs TORGO-n3 89.9 % confirms the
  corpus, not reverb, drove the old 81.4 %.
- **D3** (`t5_gsc_ambient_fahr.py`): real 6 h DEMAND+LibriSpeech at the gate + per-speaker FAR≤5 %
  threshold → 0.07 FA/hr mean (band 900); worst-of-19 at the 0.5 bar; 0 FA from noise, 8 from speech.
- **Composite coherence:** D2 recomputed at L15 (5.5 %) to match D3/channels — band 800 either way.

## Prevention

Before a scorecard ranks a domain as a/the blocker: (1) grep the producing harness for a **literal** or
the words `carried` / `off-encoder` / `~`; (2) confirm each ranked leg was measured with the **current
encoder on the same corpus** at the **same threshold**; (3) treat an un-reconciled cross-basis tie as a
**confound to resolve**, never a ranking to act on. Resolve on a **paired within-corpus** delta (absolutes
across corpora are not comparable — GSC is systematically easier than TORGO n=3).

## Guardrail Updates

- **Extended `docs/ai/ACTIVE_DEV_RULES.md` EVAL-004 with point 3** ("a carried / hard-coded / off-corpus
  scorecard number is not a measurement — re-measure every co-blocker leg on the same basis before
  ranking"), citing this note.
- Candidate automation (not yet built): a `scripts/audits/` check that flags a composite/scorecard doc
  whose per-domain table mixes corpora/encoders without a same-basis reconciliation line — the analogue of
  EVAL-004 check 3 for **ranking** rather than **delta** claims. Filed under Automation Follow-Up.

## Planning Integration

The banked verdict + next levers are in `docs/testing/2026-07-11_d5d3-gsc-confound-resolution.md` and the
plan status update (`docs/plans/INDEX.md`). The typical-900 journey is re-pointed at D2's hard-voice tail
(the sole un-walled blocker), with real-RIR (D5) and single-continuous-room (D3) as low-priority fidelity
levers.

## Shift-Left Decision

**Decision: update** (extend EVAL-004 now; a new blocking gate is future work). Shift-left to a
scorecard-authoring check, not a runtime gate: the failure is in how a *measurement doc* ranks domains,
so the cheapest catch is at doc-authoring time (grep for carried/literal legs in the composite table) —
the same tier as EVAL-004 check 3. The rule extension lands this session; the verifier check is filed
under Automation Follow-Up. No product-code change is warranted.

## Automation Follow-Up

Build `verify-sota-measurement.mjs` "check N: no un-reconciled cross-basis ranking" — a composite table
that names a blocker must either (a) show all ranked legs at one corpus+encoder+threshold, or (b) carry an
explicit same-basis-reconciliation caveat. Tracked against SOTA domain 15 (EVAL guardrail ladder).
</content>
