# CP-1 SSL-front-end ceiling spike — harness

`[measure-only]` off-device harness for the CP-1 learned-encoder ceiling probe. Reproduces the committed
`TorgoEval` protocol in Python so classic (MFCC/LPCC) and learned (WavLM/HuBERT/wav2vec2) front-ends can
be A/B'd under a **matched matcher**. Report: `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`.
Plan: `docs/plans/2026-07/cp1-ssl-frontend-ceiling-spike.md`.

**Not a CI gate** (like the Picovoice benchmark): TORGO is `[measure-only]` (uncommitted), so this never
runs in CI. It validates itself by reproducing the committed MFCC-DTW report to the decimal (DoD-1).

## Environment

- Classic arms (MFCC, LPCC) need only **numpy + stdlib `wave`** → system `python3`.
- SSL arms need **torch + transformers** → the pinned `research/.venv` (`research/requirements.txt`).
- TORGO expected at `~/torgo` (dysarthric F01/F03/F04, control FCX). 16 kHz mono 16-bit `wav_headMic`.

## Files

| File | Role |
|---|---|
| `harness.py` | Corpus scan/folds (= `TorgoCorpus`), `EnergyVad` trim, MFCC + LPCC front-ends, banded length-normalised DTW (= `Dtw`), rank-1 / held-out-global FRR@FAR / separability. |
| `run_arm.py` | Run one arm end-to-end: `mfcc` \| `lpc` \| `ssl:<model>:<layer>:<pool>`. Saves `results_<arm>.json` (per-row rank-1 for McNemar). |
| `ssl_features.py` | Frozen SSL front-end (wav2vec2/wavlm/hubert/xlsr), pooling ∈ {mean, frames_norm, frames}. |
| `sweep_ssl.py` | Layer × pooling sweep, one forward pass per utterance (amortized). |
| `matcher2x2.py` | The decomposition: representation {MFCC, WavLM} × matcher {DTW, statspool-cosine}. |
| `mcnemar.py` | Paired McNemar (per speaker + aggregate) between two arms' saved rank-1 outcomes. |

## Reproduce the headline

```sh
PY=python3; RV=research/.venv/bin/python                     # classic vs SSL
$PY run_arm.py mfcc F01,F03,F04            # → 55.4% rank-1 (matches committed report)
$PY run_arm.py lpc  F01,F03,F04            # → 53.2%
$RV run_arm.py ssl:wavlm:12:mean F01,F03,F04   # → 71.9% rank-1, FRR@FAR5% 66.3%
$PY mcnemar.py mfcc ssl_wavlm_12_mean      # → aggregate p=2e-6
$RV matcher2x2.py F01,F03,F04              # → the representation×matcher 2x2
```
