# Plan: SOTA roadmap — Experiments E1 through E10

- **Date:** 2026-07-08
- **Phase:** CP-2 (deployability) + CP-1 (accuracy) + CP-3 (device)
- **Status:** active — E1 executing now
- **Worktree:** n/a (Python measure-only spikes + design docs)
- **Plan quality:** 92/100

## Goal

Execute 10 experiments that close the remaining gaps to SOTA across all binding axes: noise
robustness (25/100), efficiency (65/100 unmeasured), language independence (95/100 claimed,
unevidenced), atypical-speaker robustness (40/100), and maturity (15/100). Deliver a concrete
CP-1 distillation architecture plan and a three-scenario SOTA scorecard update by experiment end.

## Context & Constraints

- **Starting point (N+1–N+9, banked):** DistilHuBERT (23.5M, 2 layers) + dual-cascade (distance +
  duration-ratio cross-verify) achieves SOTA-level CP-2 on dysarthric speakers: F01 0.0%, F03 2.2%,
  F04 ~2.0% FRR at ≤0.5 FA/hr on 1.01h LibriSpeech clean background. Energy-ratio provides
  additional +91.7% relative FRR reduction on F04. Zero regression on control (b=0).
- **Binding axes remaining:** (1) all numbers on clean LibriSpeech — real ambient unmeasured;
  (2) noise robustness completely unevidenced with DistilHuBERT; (3) language independence
  unevidenced; (4) on-device size/latency unmeasured; (5) encoder distillation target not specified.
- **All experiments use existing infrastructure:** TORGO @ `~/torgo/`, LibriSpeech @
  `~/picovoice-benchmark/prepared/librispeech/`, venv @
  `~/git/speechangel/research/.venv/`, harness under `scripts/eval/ssl_frontend_spike/`.
- **EVAL-002..005 discipline** — held-out threshold selection, one pre-registered hypothesis per
  experiment, fidelity-check baseline before deltas, replicate on ≥2 speakers, McNemar + exact
  binomial at matched FAR.

## Approach

Ten experiments organized in three waves. Wave 1 (E1–E4, immediate) consolidates the DistilHuBERT
baseline, attacks noise, tests the parent encoder, and quantifies vocabulary difficulty. Wave 2
(E5–E8, next) gates language independence, tests augmentation, benchmarks on-device feasibility,
and measures real ambient. Wave 3 (E9–E10, synthesis) produces the CP-1 distillation architecture
and the three-scenario SOTA scorecard update.

Key design decisions:
- **E3 is pre-registered as a single-model test** (HuBERT-base L6, not a grid search) to avoid
  selection-on-test. Exploratory variants (L1, PCA) are NOT-banked family.
- **E5 is the highest-strategic-value experiment** — it either confirms or refutes our #1
  differentiator. LOW confidence, MAX value regardless of outcome.
- **E8 (real ambient) is the deployment wall that matters** — all CP-2 numbers to date are
  on clean LibriSpeech and are optimistically biased.
- **E10 includes full scenario analysis** — best/most-likely/worst-case paths with concrete
  next actions per scenario.

## Steps

1. **E1:** DistilHuBERT control + energy combo — run on FC01/FC02/FC03 + F04
2. **E2:** Noise robustness — MUSAN mixing at 20/10/5 dB SNR, SNR-adaptive thresholds
3. **E3:** HuBERT-base L6 test + PCA probe (exploratory L1, PCA 256-dim)
4. **E4:** Per-word FRR breakdown + vocabulary recommendation rules
5. **E5:** Language-independence gate — Common Voice 6 languages
6. **E6:** Data augmentation enrollment — speed/pitch perturbation
7. **E7:** DistilHuBERT ONNX export + inference benchmark
8. **E8:** Real ambient FA/hr measurement — ≥6h household audio
9. **E9:** CP-1 distillation architecture design (synthesis of E3+E4+E7)
10. **E10:** SOTA scenario analysis & scorecard update

## Stages

### E1 — DistilHuBERT consolidation & control sweep

- **H1:** DistilHuBERT + dual-cascade transfers to control (FC01/FC02/FC03) with b(single-only)=0.
  DistilHuBERT + energy-ratio cascade brings F04 below 2% FRR at ≤0.5 FA/hr.
- **Protocol:** `distilhubert_spike.py FC01,FC02,FC03 60` (existing script, different speakers).
  Combine with `energy_ratio_spike.py` (swap model ID to DistilHuBERT) for F04.
- **DoD:** McNemar FRR FAR per control speaker. Fidelity: reproduce N+9 F01 (0.0% FRR)
  before measuring controls. F04 with DistilHuBERT + energy-ratio: FRR <2%.
- **If refuted:** b>0 on any control → duration filter too strict for typical speech →
  recalibrate θ_dur per-speaker-population. F04 not <2% → energy-ratio less effective
  with DistilHuBERT than WavLM → set threshold cascade priority accordingly.
- **Confidence: HIGH** (N+9 confirmed dysarthric; FC01 already +75% with WavLM; F04 got
  +91.7% from energy with WavLM — should transfer)
- **Cost:** 0 (existing scripts)

### E2 — Noise robustness: DistilHuBERT at SNR

- **H1:** DistilHuBERT + dual-cascade at 10 dB SNR retains ≥50% of clean detection
  (FRR ≤2× clean — i.e. F03 ≤5%, F04 ≤4% FRR). SNR-adaptive threshold with multi-condition
  enrollment improves to FRR ≤1.3× clean.
- **Protocol:** MUSAN babble/cafeteria/kitchen at 20/10/5 dB SNR mixed into TORGO test queries.
  Enrollment kept clean. Fidelity: reproduce clean DistilHuBERT baseline first. McNemar
  at matched 0.5 FA/hr per SNR condition. SNR estimation via VAD energy ratio.
  Multi-condition test: add noise-augmented templates at 15 dB SNR to enrollment pool.
- **DoD:** FRR at 10 dB SNR ≤2× clean on ≥2 of F01/F03/F04.
- **If refuted:** DistilHuBERT is noise-sensitive → need front-end noise reduction
  (spectral subtraction in `MfccConfig.noiseReduction` seam) OR switch to noise-robust
  encoder (data2vec pre-trained with noise augmentation) OR fall back to MFCC-DTW
  (which at least has documented noise degradation to plan around)
- **Confidence: MEDIUM** (MFCC collapsed at 10 dB SNR. DistilHuBERT speech-representation
  pretraining may generalize better, but unevidenced)
- **Cost:** ~1.5h (noise mixing + SNR estimation + adaptive sweep)

### E3 — Pre-registered HuBERT-base test + PCA probe

- **H1 (PRE-REGISTERED):** HuBERT-base L6 mean-pooled cosine (94M params, 6 transformer layers,
  frozen) with dual-cascade achieves FRR at ≤0.5 FA/hr ≤ DistilHuBERT's on F01+F03
  (i.e., F01 ≤0%, F03 ≤2.2% FRR). EVAL-003: ONE model pre-registered, not a grid.
  If confirmed, test PCA 768→256-dim retention as NOT-banked exploratory.
- **Rationale:** DistilHuBERT is distilled from HuBERT-base. The parent might retain
  discriminative power. L6 is mid-stack phonetically-richest (per CP-1 spike HuBERT sweep).
  Negative result = distillation IMPROVED encoder for our task (ML finding).
- **Exploratory (NOT-banked):** HuBERT-base L1 single-layer (~8M params from first transformer)
  + PCA 768→128/256-dim on the best model.
- **DoD:** McNemar F01+F03 FRR FAR. Fidelity: reproduce DistilHuBERT baseline before comparison.
  PCA: FRR retention ≥90% at 256-dim for ≥2 speakers.
- **If refuted (HuBERT > DistilHuBERT):** Distillation acted as regularizer — keep DistilHuBERT.
  If HuBERT L1 works: single-layer encoder viable → major efficiency win for CP-1 distillation.
- **Confidence: MEDIUM** (CP-1 spike: HuBERT rank-1 67.8% vs DistilHuBERT 65.9%; but CP-2 axis
  rewards invariance, not discrimination — may invert the ranking)
- **Cost:** ~1.5h

### E4 — Per-word FRR breakdown & vocabulary recommendation

- **H1:** The worst 15 of F03's 77 commands account for ≥50% of false-reject errors. Removing
  them brings remaining 62-command FRR ≤4% at 0.5 FA/hr (from 2.2%). Pairwise cosine confusion
  correlates with per-word FRR at Spearman r ≥ 0.7.
- **Protocol:** Per-word FRR at DistilHuBERT's global 0.5 FA/hr threshold. Rank words.
  Iteratively remove worst word, recompute aggregate FRR. Confusion matrix from pairwise
  centroid cosine distances. Fit: per_word_FRR ≈ f(mean_confusion, n_templates, template_var).
  Output UX rule: "this command is confusable with X → substitutions: [Y, Z]."
- **DoD:** Worst-15-words-removed FRR ≤4%. Spearman r reported. Confusable-pair recommendations
  produced for top-10 most-confused pairs.
- **If refuted (FRR evenly distributed):** All words similarly hard → binding constraint is
  embedding quality per speaker, not vocabulary composition → CP-1 distillation is the path
- **Confidence: HIGH** (N+7 proved vocab matters +50% relative; this quantifies WHICH words)
- **Cost:** ~30 min (analysis on existing DistilHuBERT embeddings)

### E5 — Language-independence gate

- **H1:** Non-English OOV (Common Voice CC0: fr, de, zh, hi, ar, ja — 3 single-speaker
  clips of ~10 min each, ~3h total background) is no closer to English TORGO templates
  than English LibriSpeech — FA/hr at DistilHuBERT's clean-English 0.5 FA/hr threshold
  degrades ≤2× for ≥5 of 6 languages. Cross-speaker scenario: French speaker (FC01 proxy)
  enrolling English words tested against French background — FRR at ≤0.5 FA/hr degrades
  ≤3× vs English-English baseline.
- **Protocol:** Download Common Voice CC0 clips at 16kHz mono. Scan with identical
  LibriSpeech protocol. For cross-speaker: use TORGO FC01 as the "non-English speaker"
  and each language as background. Re-calibrate threshold per language for fair comparison.
- **DoD:** FA/hr at English-calibrated threshold ≤2× English-only for ≥5 languages.
  Cross-speaker FRR ≤3× English-English baseline. If any language >3× → flag as
  "language-dependent for this family."
- **If refuted (language-dependent):** Critical finding. DistilHuBERT leaks English
  phonotactics → need multilingual encoder (XLSR, HuBERT multilingual) or language-agnostic
  encoder (phoneme-supervised ZP-KWS-class). Redirects CP-1 encoder choice entirely.
  The 95/100 score would need downward revision to ~60.
- **Confidence: LOW** (zero prior evidence for this specific encoder on this specific task).
  HIGH strategic value regardless of outcome — both confirmation and refutation redirect
  the roadmap.
- **Cost:** ~2h (corpus download + scan)

### E6 — Data augmentation enrollment

- **H1:** Speed perturbation (0.9×, 1.1×) + pitch shift (±2 semitones) on enrollment
  templates reduces FRR at matched 0.5 FA/hr by ≥15% relative vs clean-only enrollment
  on F03+F04 with DistilHuBERT + dual-cascade.
  Reference: LRDWWS'24 winner reported TTS augmentation + MUSAN improved Score from
  0.048→0.025 (48% relative improvement); this tests the signal-processing subset only.
- **Protocol:** Create 3 variants per TORGO utterance: 0.9× speed, 1.1× speed, +2 st pitch
  (librosa). Add to enrollment. Re-run dual-cascade. Monte Carlo 5 iters.
- **DoD:** McNemar FRR reduction ≥15% relative vs clean enrollment on ≥2 of F03/F04.
- **If refuted:** Signal-processing augmentation too simple → TTS dysarthric synthesis
  (LRDWWS recipe) or multi-session enrollment (N+2) needed instead
- **Confidence: MEDIUM** (48% gain in LRDWWS from full recipe; signal-only is subset)
- **Cost:** ~1h

### E7 — DistilHuBERT ONNX export + inference benchmark

- **H1:** DistilHuBERT exports to ONNX at <60 MB, runs a 2s utterance in <200ms on
  single-core x86 (proxy for mid-range ARM), and peak memory <300 MB. A 256-dim PCA
  projection reduces these to <25 MB / <50ms / <100 MB while retaining ≥90% of
  full-dim FRR performance.
- **Protocol:** `torch.onnx.export` with dynamic batch. Measure: file size, inference
  time for 2s/5s/10s utterances (100-run average, warm-start), peak memory via
  `tracemalloc`. Test onnxruntime compatibility. PCA projection from E4/E3.
- **DoD:** All three metrics pass/fail: ONNX <60 MB, <200ms 2s-inference, <300 MB memory.
  PCA-256: <25 MB, <50ms, <100 MB. Any failure → documented as blocker.
- **If refuted (too large/slow):** Cannot ship DistilHuBERT on-device → must train
  smaller student (E9) OR use HuBERT-L1 single-layer (~8M) OR fall back to MFCC-DTW
  + longer enrollment
- **Confidence: HIGH** (23.5M-param fp32 ≈ 94 MB raw; ONNX optimization ≈ 45-60 MB.
  2 layers × 768-dim × ~100 frames/2s ≈ 50-100ms forward pass on modern CPU)
- **Cost:** ~1.5h

### E8 — Real ambient FA/hr measurement

- **H1:** DistilHuBERT + dual-cascade on ≥6h of real household ambient audio achieves
  FRR ≤2× LibriSpeech FRR at re-calibrated 0.5 FA/hr threshold (F01 ≤0%, F03 ≤5%,
  F04 ≤5%). The duration-ratio cross-verify rejects ≥80% of background FAs passing
  the distance gate on real ambient.
- **Protocol:** Acquire ≥6h of continuous household ambient (Common Voice background
  segments, Freesound CC0 household clips, or self-recorded). Scan with identical
  LibriSpeech protocol. Measure raw FA/hr at LibriSpeech-calibrated threshold.
  Re-calibrate thresholds and measure FRR. Duration filter rejection rate.
- **DoD:** Raw FA/hr at LibriSpeech threshold reported (expected >0.5). Re-calibrated
  FRR at ≤0.5 FA/hr within 2× of LibriSpeech baseline for ≥2 speakers. Duration
  filter rejection rate ≥80%.
- **If refuted (real ambient >> LibriSpeech):** CP-2 numbers optimistically biased →
  need Stage-0 VAD gate before encoder OR real-ambient-calibrated thresholds OR
  a better rejection model (E8 from original roadmap: MLP verification)
- **Confidence: MEDIUM** (clean LibriSpeech is best-case; real ambient includes TV,
  conversation, kitchen — these will be harder for any embedding-based gate)
- **Cost:** ~2h (corpus acquisition + scan)

### E9 — CP-1 distillation architecture design

- **Not a hypothesis — a design deliverable.** Synthesize E3 (encoder model choice),
  E4 (PCA compressibility), E7 (ONNX feasibility) into a concrete CP-1 build plan.
- **Contents:** (1) Student architecture spec from E3+E4 (dimensions, layers, pooling).
  (2) Training data requirements (hours, languages). (3) Training recipe (distillation
  loss, LR schedule, data augmentation). (4) Expected FRR at 0.5 FA/hr from PCA retention
  curve. (5) On-device resource budget from E7. (6) Integration surface:
  `class DistilHubertStudentEncoder : QbeEncoder`. (7) Decision: if E7 shows DistilHuBERT
  already fits on-device → CP-1 build DE-PRIORITIZED. If not → CP-1 build is critical path.
- **DoD:** Document answers: what is the minimum viable student? What FRR can it achieve?
  Is it worth building? This gates the CP-1 checkbox in ROADMAP.md.
- **Cost:** ~1h (writing, no new measurements)

### E10 — SOTA scenario analysis & scorecard update

- **Not a hypothesis — a decision document.** Three scenarios mapped from experiment outcomes:
  - **Best case (all H1 confirmed):** Noise 55, Efficiency 90, Atypical 65, Maturity 55,
    Lang-indep evidenced, Overall ~72. CP-2 fully solved. CP-1 de-prioritized
    (DistilHuBERT fits on-device). Product ready for alpha release. Next: CP-0 SAP DUA.
  - **Most likely (mixed — E5 partial, E2 moderate, E7 passes):** Noise 40, Efficiency 75,
    Atypical 50, Lang-indep 85 (3-4 of 6 languages pass), Overall ~65. CP-2 solved for
    clean conditions. CP-1 distillation needed for noise robustness. Product alpha with
    "experimental" labelling.
  - **Worst case (E5 refuted, E2 bad, E7 fails):** Lang-indep drops to 60, overall 52
    (below Howl). Need multilingual encoder + noise-robust front-end + smaller student.
    CP-2 wall partially re-opens if on-device infeasible. 6-12 month recovery path.
- **DoD:** Each scenario has concrete next actions. Scorecard updated per-scenario.
  CP-0 (SAP DUA) and CP-3 (physical device) integrated into path.
- **Cost:** ~30 min

## Sequencing

```
WAVE 1 — IMMEDIATE (same venv, ≤4h total):
  E1: DistilHuBERT control + energy combo
  E2: Noise baseline
  E3: HuBERT-base L6 + PCA probe
  E4: Per-word FRR breakdown

WAVE 2 — NEXT (needs corpus/infrastructure, ≤7h):
  E5: Language-independence gate
  E6: Data augmentation enrollment
  E7: DistilHuBERT ONNX export
  E8: Real ambient measurement

WAVE 3 — SYNTHESIS (builds on wave 1+2 results):
  E9: CP-1 distillation architecture
  E10: SOTA scenario analysis & scorecard update
```

## Definition of Done

- [ ] **E1:** FRR FAR on FC01/FC02/FC03 with DistilHuBERT dual-cascade. F04 <2% FRR with energy.
- [ ] **E2:** FRR at 10/20/5 dB SNR with fixed + SNR-adaptive thresholds. McNemar per condition.
- [ ] **E3:** HuBERT-base L6 FRR FAR vs DistilHuBERT. PCA 256-dim retention ≥90%. L1 exploratory.
- [ ] **E4:** Worst-15-removed FRR ≤4%. Confusable-pair recommendations produced.
- [ ] **E5:** FA/hr degradation ≤2× for ≥5 languages. Cross-speaker FRR ≤3× baseline. Evidence for 95/100 score.
- [ ] **E6:** FRR reduction ≥15% relative from augmentation on ≥2 speakers. McNemar.
- [ ] **E7:** ONNX <60 MB, inference <200ms, memory <300 MB. PCA-256 passes/fails.
- [ ] **E8:** Real ambient FA/hr measured. Re-calibrated FRR within 2× LibriSpeech. Duration rejection ≥80%.
- [ ] **E9:** CP-1 distillation architecture document. Build/no-build decision gated on E7 result.
- [ ] **E10:** Three-scenario SOTA scorecard. Product alpha path per scenario.
- [ ] Testing reports for E1–E8 in `docs/testing/2026-07-08_*.md`
- [ ] Updated `docs/plans/INDEX.md` and `docs/ROADMAP.md` CP-2 status

## Risks & Mitigations

- **E5 refutes language independence (LOW confidence, MAX impact):** Mitigation — this is the whole
  point of the experiment. A refutation redirects strategy but prevents shipping a false claim.
  Plan B: multilingual encoder survey.
- **E7 shows DistilHuBERT too large/slow:** Mitigation — E3 tests single-layer HuBERT (~8M) as
  fallback. If that also fails, MFCC-DTW remains the shipped baseline with documented accuracy
  trade-off.
- **E8 shows real ambient >> LibriSpeech (2-5× degradation):** Mitigation — Stage-0 VAD gate
  before encoder, stricter cascade thresholds, pre-screen enrollment for ambient robustness.
- **Selection-on-test in E3 exploratory family:** Mitigation — H1 is pre-registered on ONE model
  (HuBERT-base L6). L1 and PCA are NOT-banked, labelled as such, with losing cells included.
  Per EVAL-003, adoption requires fresh pre-registered confirmation.
- **Curriculum risk — E2/E3/E6/E7/E8 all depend on E1:** Mitigation — E4 is independent and can
  run in parallel. E5 (language) only depends on E1 for encoder choice, not results.

## Test & Verification

- All wave 1 experiments run with `~/git/speechangel/research/.venv/bin/python3` on this host.
- EVAL-002: held-out threshold selection (leave-one-utterance-out)
- EVAL-003: one pre-registered hypothesis per experiment
- EVAL-004: fidelity-check baseline before measuring deltas
- EVAL-005: ≥2 speakers per experiment, McNemar + exact binomial at matched FAR
- Fidelity check: reproduce E1 DistilHuBERT F01 baseline (0.0% FRR) before each protocol change
- Reports in `docs/testing/2026-07-08_*.md`
- **Corpus:** `[measure-only]` — never committed. Scripts are committed.
- **Benchmark impact:** Not applicable — measurement-only, no matcher/DSP changes.
