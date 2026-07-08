# N+4 — Dual-cascade control-speaker verification (2026-07-08)

**Stage:** CP-2 roadmap N+4 (`docs/plans/2026-07/cp2-sota-roadmap-n4-to-n12.md`).
**Purpose:** de-risk the banked dual-cascade (N+3) on **control** speakers — confirm it introduces no
false-negatives on typical speech before it ships. Seeded as experiment #2 of
`docs/research/experiments/NEXT30.md`.

## Pre-registered hypothesis

**H1:** the dual-cascade (distance AND duration-ratio cross-verify AND margin-ratio) does **not** regress
on control speakers — FRR at ≤0.5 FA/hr ≤ single-threshold FRR, with zero false-negatives
(`b(single-only)=0` in the paired McNemar), on FC01/FC02/FC03.

## Protocol

- Command: `research/.venv/bin/python3 scripts/eval/ssl_frontend_spike/dual_cascade_verify.py FC01,FC02,FC03 60`
- Model: `microsoft/wavlm-base-plus` L12, mean-pooled cosine (CPU).
- Data: TORGO controls at `~/torgo/FCX/`; 60 min (1.01 h, 6067 windows) LibriSpeech background at
  `~/picovoice-benchmark/prepared/librispeech`.
- Adjudication: 3D grid (distance × duration × margin) at matched ≤0.5 FA/hr; paired McNemar + exact
  binomial per speaker and aggregate. Runtime 740 s.

## Results

| Speaker (n) | Single det / FRR | Dual det / FRR | FA/hr | b(single-only) | c(dual-only) | McNemar p |
|---|---|---|---|---|---|---|
| FC01 (34) | 88.2% / 11.8% | 97.1% / **2.9%** | 0.00 | **0** | 3 | 0.25 |
| FC02 (323) | 95.4% / 4.6% | 95.4% / 4.6% | 0.00 | **0** | 0 | 1.00 |
| FC03 (383) | 83.6% / 16.4% | 83.6% / 16.4% | 0.00 | **0** | 0 | 1.00 |
| **Aggregate (740)** | — | — | 0.00 | **0** | 3 | 0.25 |

## Verdict — DoD MET (no regression), improvement underpowered

- **`b(single-only)=0` on every control speaker and aggregate.** The dual-cascade rejects **no** query the
  single-threshold baseline accepts → **zero collateral damage on typical speech**. The banked CP-2 lever
  is safe for the full user population, not just dysarthric speakers.
- **FC01** is directionally better (FRR 11.8% → 2.9%, 3 dual-only wins) but **underpowered** (n=34, McNemar
  p=0.25) — not banked as an improvement, only as "no harm."
- **FC02/FC03 tie exactly** (b=c=0): the grid selects an operating point where the single distance
  threshold already reaches ≤0.5 FA/hr, so the duration filter is inactive there. On well-separated
  typical speech the cascade is a no-op, which is the desired safety property.

## Secondary observation (feeds W1)

**FC03 is a *control* speaker at 16.4% FRR** with 383 utterances / a large vocabulary — elevated vs FC02's
4.6%. This echoes the vocabulary-size binding constraint (W1 in `NEXT30.md`) on **typical** speech too:
large vocabularies erode detection regardless of speaker condition. Reinforces N+7 (vocab-optimized
enrollment) as the #1 next experiment.

## Reproduce

```sh
research/.venv/bin/python3 scripts/eval/ssl_frontend_spike/dual_cascade_verify.py FC01,FC02,FC03 60
```

Discipline: pre-registered single hypothesis, fidelity-shared harness with N+3, McNemar + exact binomial
at matched FAR, replicated across 3 control speakers (EVAL-002/003/004/005).
