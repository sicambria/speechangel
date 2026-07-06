# Realistic-condition simulation + rejection-scoring — TORGO (shipped static front-end)

Produced by the new `core:eval` simulation harness (`AudioAugment`, `Conditions`, `ConditionEval`,
`AmbientFar`) and rejection-scoring machinery (`RejectionScore`, `RejectionEval`, `SimReport`) over the
real TORGO corpus. Everything here is measured on the **shipped** static-MFCC front-end
(`MfccConfig(deltaOrder=NONE)`), not `TorgoEval`'s `delta_delta` default — so the numbers are for the
config the product actually ships. Held-out (leave-one-fold-out), matched FAR (EVAL-002).

> **Provenance:** `./gradlew :core:eval:test --tests "*TorgoEvalTest*" -Dtorgo.dir=<root>
> -Dtorgo.reject=true [-Dtorgo.conditions=true] [-Dambient.wav=<file>] -Dtorgo.sim.report=<file>`.
> Dysarthric = `~/torgo` (F01/F03/F04); control = `~/torgo/FCX` (FC01/FC02/FC03). TORGO is
> `[measure-only]`, never committed; the harness is committed and `:core:eval:test` stays green with the
> corpus absent. Plan: `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md`.

## Verdict

1. **The pre-registered accuracy hypothesis (H1 = common-mode rejection normalization) is REFUTED** — an
   honest negative result, the twin of the earlier per-command-calibration (D1) finding. It does not
   help; on control it *significantly hurts* (below). No runtime change is made. **Knowing this fix
   doesn't work is the Part-2 deliverable** — it saves building the wrong thing.
2. **The realistic-condition simulation harness works and produces the numbers the project lacked:** a
   condition-degradation grid (real speech, simulated channel) and the **first ambient FA/hour proxy**.
   The headline finding — **additive noise is the dominant degrader; reverb and mic band-limiting are
   mild** — is now measured, not assumed.
3. **The always-on rejection gap is starkly visible:** even the *optimistically-biased* ambient proxy
   false-fires **~82 times/hour** at the FRR≤5%-per-utterance operating point — ~160× the ≤0.5 FA/hr
   Phase-0 budget. This quantifies, on real audio, exactly the "it fires on the TV" problem.

## Baseline (shipped static front-end) — cross-checked

| Path | Rank-1 (HO) | FRR @ FAR≤5% (global, HO) | realized FAR |
|---|---:|---:|---:|
| Trusted `TorgoEval` (pooled threshold) | 59.2% | 75.7% | 4.6% |
| New `RejectionEval` (per-speaker threshold, `raw`) | — | **75.7%** | 4.6% |

The new per-speaker rejection machinery reproduces the trusted `TorgoEval` pooled-threshold path
**exactly** (75.7% / 4.6%) on the shipped front-end — so the scorer deltas below are trustworthy.
(Note: 75.7% static is nominally better than the old `delta_delta` headline of 78.3% — the shipped
front-end was never the config the first report headlined; this aligns the number to what ships, the D3
static-MFCC direction now serving as the baseline.)

## Part 2 — pre-registered rejection adjudication (H1 = common-mode), REFUTED

`s = d1 − median{d_c : c ≠ winner}` (winner = argmin d1 unchanged; rank-1 invariant). McNemar on the
positive trials at approximately-matched FAR. **Only H1-vs-raw is significance-tested**; the rest of the
family is exploratory / **not banked** (the D3/EVAL-002 anti-selection-bias rule).

| Corpus | raw FRR | H1 FRR | McNemar (rescued / regressed) | χ²(cc) | p | verdict |
|---|---:|---:|---|---:|---:|---|
| Dysarthric (F01/F03/F04, n=267) | 75.7% @ 4.6% | 79.4% @ 5.3% | 16 / 26 | 1.93 | 0.165 | not supported (worse) |
| Control (FC01/FC02/FC03, n=740) | 61.9% @ 4.9% | 73.5% @ 4.8% | 48 / 134 | **39.7** | **<0.001** | **REFUTED (significant regression)** |

Common-mode normalization is a **significant regression** on control and directionally worse on
dysarthric. The mechanism it was meant to remove (per-trial "far-from-everything" distance inflation)
is, on this corpus, dominated by **vocabulary confusability** — `median(other-command distances)` is
small precisely when the true command has acoustically-close neighbours, so subtracting it penalizes
correct-but-confusable matches instead of removing a common-mode offset. (Candidate mechanism, **not
established** — the per-speaker pattern is mixed: FC01 barely moved, F01/FC02 moved a lot.)

### Exploratory family (NOT banked — a hypothesis, not a result)

| Scorer | Dysarthric FRR | Dysarthric FAR | Control FRR | Control FAR |
|---|---:|---:|---:|---:|
| `raw` (baseline) | 75.7% | 4.6% | 61.9% | 4.9% |
| `common_mode` (H1) | 79.4% | 5.3% | 73.5% | 4.8% |
| `margin(λ=1)` | 71.2% | 4.8% | 60.0% | 5.4% |
| `ratio` | 73.0% | 4.8% | 66.5% | 5.0% |

`margin` (runner-up-gap penalty) is directionally better than `raw` on **both** sets — but it was **not
pre-registered**, and on control its apparent gain rides a **higher** FAR (5.4% vs 4.9%), so at truly
matched FAR the control gain likely shrinks. Per the pre-registration discipline this is recorded as a
**future pre-registered, FAR-matched test on fresh data** — the exact treatment D3 gave the static-MFCC
direction — and is emphatically **not** adopted here. (Both family tables were seen while forming this
note, so there is no clean TORGO holdout left to confirm it on.)

## Part 1 — realistic-condition grid (real speech, SIMULATED channel)

Deployment-slice speakers (≤25 commands: F01+F04), queries degraded / enrollment clean, held-out,
matched FAR≤5%. **A controlled robustness probe, NOT a field far-field measurement.**

| Condition | Rank-1 | FRR (raw) | FAR |
|---|---:|---:|---:|
| `clean` | 64.6% | 68.3% | 4.7% |
| `noise_20dB` | 56.1% | 80.5% | 4.7% |
| `noise_10dB` | 34.1% | 91.5% | 5.2% |
| `noise_5dB` | 8.5% | 97.6% | 4.2% |
| `reverb_small` | 64.6% | 73.2% | 4.7% |
| `reverb_medium` | 69.5% | 65.9% | 4.7% |
| `bandlimit_tel` | 65.9% | 63.4% | 6.3% |
| `living_room` | 46.3% | 81.7% | 4.7% |

**Reading:** additive noise is the dominant degrader — rank-1 falls 64.6%→56.1%→34.1%→8.5% at
20/10/5 dB SNR, and by 5 dB the matcher is near chance. Reverb is mild (medium-room rank-1 is within
noise of clean); telephone band-limiting barely dents rank-1 (speech energy sits in-band). The combined
"living room" (mild reverb + 15 dB noise + small-speaker band) lands at rank-1 46.3%. (`common_mode` was
worse in every condition — omitted here; it is in the raw sim report — consistent with the refutation.)
This says the highest-value robustness work is **noise handling**, not dereverberation.

## Part 1 — ambient FA/hour proxy (the always-on number the harness could not measure before)

Speaker F01 (15 commands), templates enrolled clean; ambient = that speaker's real OOV utterances +
silence gaps + 20 dB white noise, sliding 1500 ms / 500 ms windows, debounced. Operating threshold
16.44 (raw, calibrated in-sample to ≤5% per-utterance OOV FAR — the proxy operating point).

- Simulated listening ≈ **2.2 min**; **3 false accepts → ~82 FA/hour.**
- **Honesty:** concatenated isolated OOV words with gaps are *less* command-like than continuous
  TV/dialogue, so this is **optimistically biased** — a real living room would fire more. This proxy
  does **not** retire the Phase-0 ≤0.5 FA/hr exit; a dropped-in real recording (`-Dambient.wav`) turns
  it into a genuine (single-room) measurement.

Even optimistically biased, 82 FA/hr is ~160× the budget — the quantitative statement of the always-on
rejection problem on real audio.

## What this does and does not measure

- **Measures:** on real TORGO speech — held-out discrimination/rejection on the shipped front-end;
  degradation under *simulated* noise/reverb/band-limit; a first ambient FA/hour *proxy*.
- **Does NOT measure:** field far-field acoustics (the channel is simulated), or a real continuous
  ambient stream (the proxy is concatenated isolated speech, optimistically biased). Both remain
  **Bucket B**, gated on real recordings — no field numbers are claimed.
- **No runtime change:** H1 refuted → the matcher's decision rule is unchanged. `margin` is a documented
  future pre-registered hypothesis, not an adopted lever.
</content>
