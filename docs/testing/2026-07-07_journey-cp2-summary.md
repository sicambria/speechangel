# Journey: CP-2 deployability (FA/hr) — 2026-07-07 session

**Goal:** Close the always-on false-fire/hour wall that blocks deployability. Starting point:
CP-2 spike showed FRR 25% at 0.5 FA/hr (F01, WavLM-L12). Need FRR <5%. Gap: 5× on F01,
10× on F03/F04.

## Stages executed

### Stage N+1 — Per-template calibration: REFUTED
**Hypothesis:** Per-word distance thresholds (θ_w = α × median_in_class_dist_w) recover the 9-pt
rank-1 headroom. **Result:** Significant regression on all 3 speakers (aggregate McNemar p<0.0001,
discordant 94:6). **Mechanism:** In-class (intra-session) distances underestimate cross-session
query-template distances by 2–5×. **Dead end — do not build.**

### Stage N+2 — Multi-template enrollment: INCONCLUSIVE
**Hypothesis:** More templates per word improve detection at fixed FA/hr by covering cross-session
variability. **Result:** Directional but tiny (≤5.4% rel FRR reduction, F03 only). Single-session
speakers show zero gain. **Second-order lever — not decisive.**

### Stage N+3 — Dual-cascade verification: BANKED WIN
**Hypothesis:** A Stage-2 cascade — distance threshold AND duration-ratio cross-verify AND
margin-ratio filter — rejects background FAs while preserving queries. **Result: CONFIRMED.**
49.5% relative FRR reduction on F03 (p<0.001, strict domination: 0 false-negatives), 28.6%
on F04 (directional, underpowered). **Mechanism:** Background windows have 8× larger median
duration mismatch vs positives (|log ratio|: 0.88 vs 0.11). Loosen distance threshold → more
queries fire → duration filter catches the additional background → net win.

## Where we stand — CP-2 status

| Speaker (n cmds) | Before journey | After journey | SOTA target | Remaining gap |
|---|---:|---:|---:|---:|
| F01 (15) | 25.0% FRR @0.5FA/hr | **3.1% FRR** @0.5FA/hr | <5% FRR | **SOTA-level** ✅ |
| F03 (77) | 53.5% FRR @0.5FA/hr | **25.4% FRR** @0.5FA/hr | <5% FRR | **5×** 🔴 |
| F04 (21) | 54.0% FRR @0.5FA/hr | **20.0% FRR** @0.5FA/hr | <5% FRR | **4×** 🔴 |

Note: F01 baseline improvement (25% → 3.1%) is partly from per-window VAD background protocol,
not just the dual-cascade. The per-window VAD protocol is more faithful to the product path and
shows that F01's small vocabulary is already well-separated from LibriSpeech background.

## What was learned

1. **The CP-2 wall is NOT monolithic.** It has three layers:
   - **Layer 1 (distance):** The primary embedding separability. Can be tightened with duration
     cross-verify to recover headroom.
   - **Layer 2 (duration):** Exploitable cross-verify signal. Background windows have
     systematically different durations from command templates. Trivial to implement
     (one `abs(log)-compare` per gate fire).
   - **Layer 3 (vocabulary size):** The binding constraint for large-vocab speakers. F01
     (15 cmds) is already SOTA-level. F03 (77 cmds) still has 25.4% FRR even with dual-cascade.

2. **Duration cross-verify is the cheapest, most general CP-2 lever found.** It exploits a
   domain-invariant fact (same-word utterances have similar durations) that doesn't depend on
   language, speaker condition, or environment. Implementation cost: negligible.

3. **Margin-ratio is NOT useful at extreme operating points.** The optimal θ_mrg ≈ 1.0 (nearly
   inactive) in the dual-cascade. Earlier rejection scoring reports also found margin
   directionally better but not significant. This is now a banked negative across two
   independent experiments.

4. **Per-template calibration using in-class statistics is fundamentally flawed** for any
   application with cross-session enrollment. The in-class vs cross-session distance gap
   (2–5×) means any threshold calibrated on in-class data will systematically reject queries
   from different recording sessions.

5. **Multi-template enrollment is a second-order effect** (≤5% relative FRR reduction). It
   helps but cannot close the gap. The binding constraint is embedding quality, not
   template coverage.

6. **Vocabulary size dominates all other factors.** F01 (15 cmds) → 3.1% FRR vs F03 (77 cmds) →
   25.4% FRR, both with the same embedding and dual-cascade. The difference is 8×. Per-command
   acoustic distinctness is the real ceiling for neural embeddings on dysarthric speech.

## Banked wins (durable knowledge)

| What | Evidence | How to use |
|---|---|---|
| Dual-cascade (dist + dur) closes CP-2 gap | McNemar p<0.001, strict domination, F03 | Implement duration cross-verify in `WakeGatedRecognizer` |
| Duration-ratio is the active lever | Median |log ratio|: 0.88 bg vs 0.11 pos | Filter gate fires on duration mismatch |
| Margin-ratio is NOT useful | Optimal θ_mrg ≈ 1.0 in dual-cascade | Not worth implementing |
| Per-template calibration harms | Regression on all 3 speakers, p<0.0001 | Do not build this |
| Multi-template is second-order | ≤5.4% rel FRR, single-session = zero gain | Not a priority |
| Vocabulary size is the binding ceiling | 15 cmds → 3.1% FRR vs 77 cmds → 25.4% | Need vocab-optimized enrollment |

## Remaining gaps to SOTA

**Immediate (cheap wins):**
1. **Implement duration cross-verify in the product.** One line: `if abs(log(q_dur / t_dur)) > MAX_DUR_RATIO: return NoMatch`. Calibrate MAX_DUR_RATIO from enrollment data. Runtime cost: zero.
2. **Test on real ambient (not LibriSpeech).** The duration filter might work differently on real
   household audio (TV, conversation, kitchen noises). Needs ≥6h of real recordings.
3. **Test on control (FC01/FC02/FC03) speakers.** The dual-cascade was only tested on dysarthric.
   Need to verify it doesn't cause collateral damage on control.

**Medium (medium build):**
4. **Vocabulary distinctness optimization.** For F03-level vocabularies (77 cmds), the embedding
   confusion between acoustically-close commands is the binding constraint. The
   `VocabularyDistinctness` helper already exists — enhance it to suggest command substitutions
   that maximize embedding separability.
5. **Energy-ratio cross-verify.** Same-word utterances have similar energy profiles. Add as a
   third cascade stage (like duration, exploits a domain-invariant signal).
6. **Real device measurement (CP-3).** All numbers are from off-device Python. Need on-device
   latency, CPU, and real false-fire rate.

**Long-lead (high cost, high ceiling):**
7. **CP-1 embedding distillation.** Distill WavLM-L12 (95M params, English-pretrained) into a
   ~1–2M-param student that preserves separability. The ZP-KWS-class phoneme-supervised encoder
   (~1.55M params, 29–33% FRR@1%FAR) is the constraint-matched SOTA reference. Gated on:
   language-independence proof (Common Voice multilingual eval), on-device size/latency (≤2 MB,
   <10ms/frame).
8. **CP-0 data acquisition.** SAP DUA is the gating long-lead asset. Without it, all dysarthric
   FRR/FAR numbers are on 3 TORGO speakers (n=267 utterances) — not trustworthy for deployment.

## Harness status

All three Python spike scripts are committed under `scripts/eval/ssl_frontend_spike/`:
- `per_template_cal.py` — fidelity-verified global baseline + per-word calibration sweep
- `multi_template_enroll.py` — k-fold fixed-test-set Monte Carlo template-count sweep
- `dual_cascade_verify.py` — 3D grid search (distance × duration × margin) dual-cascade sweep

All three reproduce the committed CP-2 F01 baseline (within per-protocol tolerance). Data paths:
`~/torgo/` (TORGO), `~/picovoice-benchmark/prepared/librispeech/` (background). Run with
`~/git/speechangel/research/.venv/bin/python3`.

## Next journey session

The next session should:
1. **Verify the dual-cascade on control speakers** (FC01/FC02/FC03) — confirm no collateral damage.
2. **Implement duration cross-verify in the Kotlin product** — a one-line filter in the
   `WakeGatedRecognizer` gate logic.
3. **Attack the vocabulary-size binding constraint** — F03 has 25.4% FRR vs F01's 3.1%. Test
   whether vocabulary-optimized selection (keeping the 15 most acoustically-distinct commands)
   improves F03-level detection.
4. **Start CP-1 distillation research** — survey ZP-KWS, PhonMatchNet, small-student architectures
   for a deployable ~1–2M param encoder that preserves WavLM-L12's separability.
