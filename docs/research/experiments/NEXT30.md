# Next 30 Experiments Toward SOTA

**Compiled:** 2026-07-08
**Supersedes as the forward plan:** `docs/research/experiments/TOP30_EVAL.md` (that doc reports the
*already-run* 14; this doc is the *next* 30, re-prioritized from the current frontier).
**Basis:** `docs/research/OVERALL.md`, `docs/testing/2026-07-07_journey-cp2-summary.md`,
`docs/research/experiments/SCORES.md`, `docs/plans/2026-07/cp2-sota-roadmap-n4-to-n12.md`.

> **Seeded result — N+4 executed 2026-07-08 (experiment #2 below).** The one host-runnable stage that
> needed no new code was run to seed a real number. **DoD met: the banked dual-cascade causes zero
> regression on control speakers** — b(single-only)=0 on FC01/FC02/FC03 and aggregate (n=740, 60-min
> LibriSpeech background). It rejects no query the single-threshold baseline accepts, de-risking the
> banked CP-2 lever for the full population. FC01 is directionally better (FRR 11.8%→2.9%) but
> underpowered (n=34, McNemar p=0.25); FC02/FC03 tie (controls are already well-separated at 0 FA/hr, so
> the duration filter is inactive at the operating point). Notably FC03 — a *control* speaker with a
> 383-utterance / large vocabulary — sits at 16.4% FRR, echoing the vocabulary-size finding (W1) on
> typical speech too. Full log: `docs/testing/2026-07-08_n4-dual-cascade-control-verification.md`.

> **Framing (EVAL-003 discipline).** Every item below is a **proposed experiment** — a pre-registered
> hypothesis + Definition-of-Done, **not** a claimed gain. No number here is "banked" or a "win";
> expected magnitudes are targets to be confirmed at matched FAR, held-out, with a paired test. IDs
> reuse the existing `E##-##` suite and the `N+#` CP-2 roadmap stages for traceability.

---

## 1. Where we are now — the frontier delta since the 200-suite was scored

The 200-experiment suite (`README.md`/`SCORES.md`) and the CP-2 journey moved the frontier. What is
**new** since those scores, and what it changes:

1. **A CP-2 lever is banked: the dual-cascade (distance + duration-ratio cross-verify).** 49.5%
   relative FRR reduction on F03 (McNemar p<0.001, strict domination), 28.6% on F04 (directional).
   Mechanism: background windows have ~8× larger median duration mismatch than positives
   (|log ratio| 0.88 vs 0.11). This is the cheapest, most language-invariant CP-2 lever found.
   *Consequence:* the cascade family is validated → energy-ratio, learned-verifier, and product-impl
   follow-ups rise in priority; the still-unrun N+4/N+5/N+7/N+9/N+10 stages inherit it.
2. **Vocabulary size is the binding constraint, quantified.** F01 (15 cmds) → **3.1% FRR** @0.5 FA/hr
   (SOTA-level) vs F03 (77 cmds) → **25.4% FRR** with the *same* WavLM embedding + dual-cascade — an
   **8× gap at fixed embedding**. This reframes CP-2: for large vocabularies the ceiling is
   per-command acoustic distinctness, not the gate. The single most decisive open question is whether
   that gap is **vocabulary confusion** (→ invest in distinctness optimization) or **embedding
   quality** (→ redirect to CP-1 distillation). That fork (N+7) is #1 below.
3. **CP-1 ceiling is a GO but the build has not started.** WavLM-L12 pooled-cosine 71.9% rank-1 vs
   static MFCC-DTW 59.2% (McNemar p=2×10⁻⁶). The lever is a fixed-dim **QbE embedding + cosine**, not a
   front-end swap. No distillation to a deployable ~1–2M student exists yet; the size floor is unknown.
4. **Dead-ends are now confirmed** (excluded from ranking, §2): per-command calibration, cosine DTW,
   common-mode rejection, noise-reduction-on-clean, margin-ratio, per-template in-class calibration,
   multi-template-as-a-primary-lever.
5. **Two differentiators remain unmeasured and unfalsified:** language-independence beyond English
   (TORGO is English-only) and every real-device number (latency, battery, real-ambient FA/hr).
6. **Host capability (2026-07-08):** the CP-2/CP-1 SSL spikes are **runnable here** — WavLM-base-plus via
   `transformers`, TORGO at `~/torgo`, LibriSpeech background at
   `~/picovoice-benchmark/prepared/librispeech`, venv at `research/.venv` (CPU-only; `torchaudio` absent
   but unused — audio loads via `soundfile`/`wave`). **Absent:** MUSAN, Common Voice, GPU, physical
   device, SAP DUA. This gates which of the 30 can run today (see §6).

**Current honest numbers (context, not targets):** static MFCC-DTW rank-1 59.2% dysarthric (F01 71.9% /
F03 56.8% / F04 60.0%); FRR 75.7% @ FAR ~5% held-out; ~82 FA/hr synthetic ambient; WavLM ceiling 71.9%
rank-1; CP-2 dual-cascade FRR @0.5 FA/hr F01 3.1% / F03 25.4% / F04 20.0%. **SOTA bar:** FRR <5% @
≤0.5 FA/hr, language-independent, 1-shot, on real dysarthric audio.

---

## 2. Settled — excluded from the ranking

These are **done** or **confirmed dead-ends**; they do not consume a slot. Do not re-run without new
evidence.

| Item | Verdict | Source |
|---|---|---|
| E01-02 Delta-order sweep | Static MFCC wins +3.8pp — **done** | `RESULTS.md` |
| E02-01 Cosine DTW | Worse than Euclidean −0.8pp — **dead-end** | `TOP30_EVAL.md` |
| E03-01 Enrollment count | Saturates at k≥3 templates — **done** | `TOP30_EVAL.md` |
| E06-01 Per-severity | **done** (vocab confounds severity) | `RESULTS.md` |
| E08-01 Vocab size curve | ~5–8pp/doubling — **done** | `RESULTS.md` |
| E09-01 Global threshold sweep | **done** (DET via Picovoice) | `RESULTS.md` |
| E09-02 Per-command calibration | Non-improvement (FAR 24–34%, sparse negatives) — **dead-end until CP-0** | `TOP30_EVAL.md` |
| E10-06 McNemar standard | **done** (adopted) | `RESULTS.md` |
| Noise reduction on clean speech | Harmful −4.1pp — **dead-end** (only SNR-adaptive survives, → E05-07) | `RESULTS.md` |
| Common-mode rejection (H1) | NOT SUPPORTED (p=0.17) — **dead-end** | `2026-07-06_...rejection-scoring.md` |
| Margin-ratio filter | Optimal θ≈1.0 (inactive) across two experiments — **dead-end** | `2026-07-07_journey-cp2-summary.md` |
| N+1 Per-template in-class calibration | Regression on all 3 speakers (p<0.0001) — **dead-end** | journey summary |
| N+2 Multi-template as primary lever | Second-order (≤5.4% rel, single-session=0) — **not a priority** | journey summary |
| N+3 Dual-cascade (dist+dur) | **BANKED** — the CP-2 lever (prior work; its follow-ups are ranked below) | journey summary |

---

## 3. The binding constraints (the organizing frame)

Every one of the 30 attacks one of six walls. Priority follows the wall's proximity to the SOTA bar.

- **W1 — Vocabulary distinctness** (the binding ceiling for large-vocab speakers). *8× FRR gap.*
- **W2 — Always-on FA/hr (CP-2)** — dual-cascade banked; F03/F04 still 4–5× from <5% FRR.
- **W3 — Embedding quality / CP-1 build** — WavLM ceiling proven; deployable student not built.
- **W4 — Language-independence** — the #1 differentiator, never measured beyond English.
- **W5 — Noise robustness** — scored 25/100; needs augmentation corpora.
- **W6 — Real-device & production (CP-3)** — no latency/battery/real-ambient number exists.

**Constraint-preservation gate (governs all).** An experiment that erodes **language-independence +
1-shot arbitrary-word enrollment + determinism** is out regardless of its FRR (the CP-1 gate). This is
scored as the "Constraint Fit" axis (0–200) from `SCORES.md`.

---

## 4. The Next 30 — ranked

Scoring rubric (from `SCORES.md`, 0–1000): **Impact** (0–400, FRR/FAR magnitude) · **Feasibility**
(0–300, ease on existing infra) · **Constraint Fit** (0–200, preserves lang-indep + on-device +
determinism) · **Evidence** (0–100, literature/prior-result backing). `RH` = runnable on this host today.

### Tranche A — Decisive & runnable-here (WavLM/CP-2 spikes + the strategic fork)

**1. N+7 / E08-11 — Vocabulary-optimized enrollment (the strategic fork). Score 870. `RH`. [W1]**
- **H1:** Reducing F03's 77 commands to the k=15 most acoustically-distinct (greedy max-min pairwise
  WavLM-cosine) brings FRR @0.5 FA/hr from 25.4% to ≤10% (≥60% relative), vs a random-15 Monte-Carlo
  baseline (10 iters).
- **Protocol:** pairwise cosine confusion matrix on F03 → greedy diversity selection → re-run
  dual-cascade on the reduced vocabulary. Script: extend `dual_cascade_verify.py`.
- **DoD:** optimized-15 vs all-77 vs random-15 FRR @0.5 FA/hr. **optimized-15 ≤10% ⇒ vocabulary
  confusion is binding** (invest in distinctness optimization); **≈25% ⇒ embedding quality is binding**
  (redirect to CP-1). Decisive either way.
- **Why #1:** it is the fork that decides whether W1 or W3 gets the next quarter of effort.

**2. N+4 — Dual-cascade control-speaker verification. Score 770. `RH`. ✅ RUN 2026-07-08. [W2]**
- **H1:** the banked dual-cascade does **not** regress on control speakers — FRR @0.5 FA/hr ≤
  single-threshold FRR with zero false-negatives (b(single-only)=0).
- **Protocol:** `dual_cascade_verify.py FC01,FC02,FC03 60` (script exists, no new code).
- **DoD:** McNemar at ≤0.5 FA/hr per control speaker; b>0 ⇒ collateral damage on typical speech.
- **Result (2026-07-08):** **DoD MET.** b(single-only)=0 on all three control speakers + aggregate
  (n=740). FC01 FRR 11.8%→2.9% (directional, p=0.25, n=34); FC02/FC03 tie (b=c=0). No collateral damage.
  The one banked CP-2 lever is safe on typical speech. `docs/testing/2026-07-08_n4-dual-cascade-control-verification.md`.

**3. N+5 / E02-11 — Energy-ratio cross-verify (3rd cascade stage). Score 740. `RH`. [W2]**
- **H1:** adding |log(q_rms / t_rms)| ≤ θ as a third cascade stage reduces FRR @0.5 FA/hr by ≥10%
  relative vs the 2-stage (dist+dur) cascade.
- **Protocol:** extend `dual_cascade_verify.py` with an RMS-energy feature; 4D grid (dist, dur, enr,
  margin) at matched FA/hr.
- **DoD:** McNemar p<0.05 on ≥2/3 dysarthric speakers, or an honest negative. Energy = no VAD, so it is
  even cheaper than duration if it helps.

**4. N+10 / E09-11 — Learned verification MLP. Score 760. `RH`. [W2]**
- **H1:** a logistic-regression / small-MLP on (min_dist, dur_ratio, enr_ratio, 2nd_dist, n_templates)
  beats the hand-crafted dual-cascade by ≥20% relative FRR at matched FA/hr (k-fold CV).
- **Protocol:** extract the cascade features per query → k-fold CV logistic/MLP → compare vs dual-cascade
  decision boundary.
- **DoD:** held-out FRR @0.5 FA/hr vs dual-cascade. Constraint check: all features are **relative**
  (ratios / rank), so the boundary stays language- and speaker-agnostic.

**5. N+9 / E07-11 — DistilHuBERT CP-2 calibration (the student size floor). Score 760. `RH`. [W3]**
- **H1:** DistilHuBERT-L2 mean-pooled cosine (~23M, 2 layers) with dual-cascade reaches ≥50% of
  WavLM-L12's CP-2 performance — FRR @0.5 FA/hr ≤40% on F03, ≤30% on F04.
- **Protocol:** compute DistilHuBERT embeddings for TORGO + LibriSpeech (transformers download) → full
  dual-cascade protocol → compare vs WavLM-L12.
- **DoD:** per-speaker FRR @0.5 FA/hr. **F03 ≤40% ⇒ a small encoder is viable**; **>50% ⇒ a 1–2M student
  needs a fundamentally different (phoneme-supervised) approach, not distillation.** Informs the CP-1
  architecture floor.

**6. E07-02 — WavLM layer-selection sweep for dysarthric QbE. Score 720. `RH`. [W3]**
- **H1:** a layer L≠12 maximizes dysarthric rank-1 / CP-2 separability (mid-network layers often carry
  the most phonetic content).
- **Protocol:** pooled-cosine rank-1 + FRR @0.5 FA/hr across hidden layers 6–14; pick best; McNemar vs L12.
- **DoD:** the best-layer curve + a paired test vs the current L12 default. Feeds N+9/E07-12/distillation.

**7. E07-08 — Embedding + DTW score fusion. Score 730. `RH`. [W3]**
- **H1:** late fusion of z-normalized WavLM-cosine ⊕ MFCC-DTW scores beats either alone in rank-1 and
  FRR @ matched FAR — they err differently (WavLM-under-DTW *ties* MFCC; MFCC-under-pooling *drops* to
  39.3% → complementary error).
- **Protocol:** weighted score-level fusion sweep (α∈[0,1]) on TORGO; McNemar vs each single system.
- **DoD:** fused vs WavLM-only vs MFCC-only. Constraint: fusion **adds** an encoder (CP-1 tension) — keep
  it as a candidate, not a mandate; the 1-shot + language-independence gate still applies to the encoder.

**8. N+12 / E07-12 — WavLM PCA → low-dim separability retention probe. Score 710. `RH`. [W3]**
- **H1:** projecting WavLM 768-dim → 64-dim (PCA) preserves cosine separability within ≤10% relative
  FRR drop → sets the student output dimension.
- **Protocol:** fit PCA on background/enrollment embeddings → FRR @0.5 FA/hr at dims {768,256,128,64,32}
  → find the knee.
- **DoD:** the dim-vs-FRR curve; the smallest dim within the ≤10% band is the student head target.

### Tranche B — MFCC-DTW product-config wins (Gradle `TorgoEval`, runnable-here)

**9. E01-11 — Confirm the combined 30 ms-frame + 30 %-band + static-MFCC config (paired, FAR-matched). Score 760. `RH`. [W1/W3]**
- **Context:** the mined best is 65.2% rank-1 (+6.0pp; F04 +16pp) but EVAL-003 forbids adopting a
  best-of-grid pick without a fresh **paired** confirmation. This is that confirmation.
- **H1:** the combined config beats the shipped baseline by a significant margin under paired McNemar at
  matched FAR, held-out.
- **Protocol:** `:core:eval` `TorgoEval` grid at frame=30ms, band=30%, delta=NONE vs shipped defaults;
  held-out folds; McNemar.
- **DoD:** p<0.05 held-out ⇒ adopt as the shipped default (a 3-line config change). Otherwise keep 25ms/10%.

**10. E06-05 — Rate-adaptive / per-command DTW band width. Score 710. `RH`. [W1]**
- **H1:** setting the Sakoe–Chiba band per-command from enrollment temporal variability beats a global
  30% band — severe-dysarthric commands need wider warping; consistent commands narrower (which also
  cuts FA).
- **Protocol:** derive band width from intra-command DTW-path variance at enrollment; sweep; McNemar.
- **DoD:** rank-1 + FRR/FAR vs the fixed-band baseline, per severity.

**11. E02-08 — Dual-filter (path-length) cascade FRR/FAR evaluation. Score 810. `RH`. [W2]**
- **Context:** `Dtw.withPath()` + `MatcherConfig.dualFilterTolerance` are **built** but only shown to
  leave *rank-1* unchanged; the threshold-level FRR/FAR effect is unmeasured. This is the missing eval.
- **H1:** path-length rejection cuts FAR ≥30% relative at matched FRR — the MFCC-DTW analog of the
  WavLM duration cross-verify win (same domain-invariant signal).
- **Protocol:** FRR/FAR sweep with vs without the dual-filter on TORGO + OOV negatives.
- **DoD:** FAR reduction at matched FRR; McNemar. If it mirrors the WavLM duration result → ship it.

**12. E09-08 + E02-05 — Hysteresis + k-NN threshold-level FRR/FAR eval. Score 670. `RH`. [W2]**
- **Context:** `MatcherConfig.hysteresisZone` and `MatcherConfig.kNN` are **built**; both leave rank-1
  unchanged. Their only possible value is at the acceptance/rejection level — untested.
- **H1:** 3-zone hysteresis and k-NN distance averaging reduce spurious rejects/accepts (FRR or FAR) at a
  fixed operating point vs 1-NN hard threshold.
- **DoD:** FRR/FAR at matched point. Honest negative acceptable (retires two built-but-unproven knobs).

**13. E13-08 / E03-09 — Pitch-shift + time-stretch enrollment augmentation. Score 760. `RH`. [W1/W5]**
- **H1:** augmenting each enrollment template with ± pitch / ± rate synthetic variants
  (`AudioAugment.pitchShift`/`timeStretch`, built at `core/eval/AudioAugment.kt:198`) improves rank-1 /
  FRR on cross-session queries.
- **Protocol:** enroll on {clean} vs {clean + augmented}; TORGO held-out; McNemar; watch FAR inflation.
- **DoD:** rank-1 + FRR at matched FAR. Free (no corpus). Constraint-clean (derived from the user's audio).

**14. E06-09 — Personalized per-speaker feature z-scoring (CMVN++). Score 720. `RH`. [W1]**
- **H1:** per-speaker mean/variance normalization of MFCC (beyond per-utterance CMN) shrinks within-speaker
  distance spread → higher rank-1, especially for severe dysarthric.
- **Protocol:** fit per-speaker feature stats from enrollment; normalize queries; rank-1 + FRR per severity.
- **DoD:** McNemar vs the CMN baseline.

**15. E12-09 — Runtime-synthesized negative templates. Score 710. `RH`. [W2]**
- **H1:** synthesizing per-command "near-miss" negatives at enrollment (time-warped / pitch-shifted copies
  of the *other* commands) improves the reject boundary → lower FAR at fixed FRR **without any corpus**.
- **Protocol:** generate negatives from the user's own enrolled set; use as anchors in the reject test;
  FRR/FAR vs baseline.
- **DoD:** FAR reduction at matched FRR. Constraint-clean (all audio is the user's own).

**16. E08-03 — Greedy command-set selection on TORGO (the MFCC-DTW analog of N+7). Score 740. `RH`. [W1]**
- **H1:** choosing the k most-separable commands (greedy max-min DTW distance) yields higher rank-1 than a
  random k-subset at fixed k → operationalizes the `VocabularyDistinctness` advisor into a recommender.
- **Protocol:** greedy-k vs random-k Monte-Carlo at k∈{15,25} on F03's 77 commands (MFCC distances).
- **DoD:** rank-1 delta greedy-vs-random; cross-check against N+7's WavLM-cosine selection (do the two
  metrics pick the same commands?).

### Tranche C — Wake/FAR + evaluation methodology (runnable-here)

**17. E04-06 — Multi-frame wake persistence FA/hr eval. Score 860. `RH`. [W2]**
- **Context:** `WakeGatedRecognizer.onFrame()` is per-frame; adding `consecutiveWakeCount ≥ N` is ~5 LOC.
- **H1:** requiring N≥2 consecutive wake frames cuts ambient FA/hr ≥80% at ≤2pp wake-FRR cost.
- **Protocol:** FA/hr + wake-FRR across N∈{1,2,3} on LibriSpeech ambient + TORGO wake positives.
- **DoD:** the FA/hr-vs-wake-FRR frontier; pick N. Highest-scored built-but-unmeasured wake lever.

**18. E04-02 + E04-01 — Per-speaker wake calibration + wake template count sweep. Score 810. `RH`. [W2]**
- **H1:** a per-speaker wake threshold (+ 2–3 wake templates) reduces wake-FRR 5–15pp at fixed FA/hr.
- **Protocol:** `ThresholdCalibrator` on wake templates; sweep template count; hold FA/hr fixed.
- **DoD:** wake-FRR @ fixed FA/hr across counts + calibration on/off.

**19. E04-08 — Negative (background) template enrollment for the wake gate. Score 760. `RH`. [W2]**
- **H1:** enrolling a few ambient/background snippets as explicit reject anchors cuts FA/hr at fixed
  wake-FRR (a corpus-free, on-device rejection prior).
- **Protocol:** add background anchors to the wake matcher; FA/hr vs baseline on LibriSpeech ambient.
- **DoD:** FA/hr reduction at matched wake-FRR. Constraint-clean (ambient captured on-device, not other users).

**20. E10-07 — Open-set OOV evaluation standard (truth=null split). Score 750. `RH`. [W2/eval]**
- **H1:** reporting FRR/FAR on an explicit in-vocab vs OOV split (EasyCall-style, simulated by holding
  out TORGO words as OOV) gives an honest deployment number the current closed-set rank-1 hides.
- **Protocol:** partition each speaker's words into in-vocab / OOV; measure FRR (in-vocab miss) + FAR
  (OOV accept) at the operating point; DET.
- **DoD:** open-set FRR/FAR + DET adopted as the standard reporting split in `TorgoEval`.

**21. E10-03 + E10-05 — Bootstrap CI + statistical-power reporting. Score 760. `RH`. [eval]**
- **H1:** with n=267 utterances / 3 speakers, single-run deltas carry wide CIs; quantifying them prevents
  over-reading mined margins (the EVAL-003 failure mode).
- **Protocol:** bootstrap 95% CI (≥1000 resamples) on rank-1 / FRR / FAR for every headline number;
  power analysis for the minimum detectable effect at this n.
- **DoD:** CIs attached to all headline metrics; a "minimum detectable effect" line in every report.

**22. E10-01 — DET curve + Cllr/Cdet reporting standard. Score 730. `RH`. [eval]**
- **H1:** operating-point-agnostic detection metrics (DET, min-Cllr, Cdet) complement EER / FRR@FAR and
  match NIST detection-eval norms → externally comparable numbers.
- **Protocol:** render DET curves (`lets-plot` Apache-2.0 or the Python spike's matplotlib) + compute Cllr
  per speaker; fold into the `TorgoEval` report.
- **DoD:** DET + Cllr in the standard report; retires the ambiguity of single-threshold FRR headlines.

**23. E19-01 — Three-stage cascade (energy → MFCC-DTW → WavLM verify). Score 740. `RH` (accuracy) / device (latency). [W3/W6]**
- **H1:** routing only DTW-borderline queries to the expensive WavLM verify recovers most of WavLM's
  accuracy at a fraction of the compute → a deployable accuracy/latency tradeoff.
- **Protocol:** accuracy sim on TORGO — rank-1/FRR vs WavLM-always and DTW-always; report % queries
  escalated; estimate latency (real latency needs CP-3 device).
- **DoD:** accuracy within X pp of WavLM-always at ≤Y% escalation. Feeds the on-device deployment story.

### Tranche D — Blocked on an external asset (pre-registered; flag the blocker)

**24. N+8 / E07-10 — Language-independence gate (Common Voice multilingual OOV). Score 710. Blocked: Common Voice CC0 (~2h download/build — then `RH`). [W4]**
- **H1:** non-English OOV is no closer to English templates than English OOV — FRR @0.5 FA/hr degrades
  <10% relative vs an English-only background.
- **DoD:** FRR @0.5 FA/hr, English-bg vs multilingual-bg. **Decisive either way** — confirms or refutes
  the #1 differentiator (language-independence, the 95/100 axis). The maximal-impact gate.

**25. N+6 / E05-07 — SNR-adaptive accept threshold + noise baseline. Score 750. Blocked: noise corpus (MUSAN/DEMAND subset, ~1h build). [W5]**
- **H1:** an SNR-adaptive threshold reduces FRR @0.5 FA/hr by ≥30% relative at ≤10 dB SNR vs a fixed
  clean threshold (WavLM + dual-cascade). `StreamingEnergyGate`'s running noise floor gives the SNR.
- **DoD:** FRR @ matched FA/hr across SNR bins with adaptive vs fixed threshold. Attacks noise=25/100.

**26. E05-04 — MUSAN noise-augmented enrollment. Score 760. Blocked: MUSAN corpus (~30 GB or a subset). [W5]**
- **H1:** multi-condition enrollment (clean + MUSAN-mixed templates) cuts FRR ≥10–20% relative at
  ≤10 dB SNR. `AudioAugment.addNoise()` is ready.
- **DoD:** FRR at ≤10 dB SNR vs clean-only enrollment; check no clean-speech regression.

**27. E05-05 / E05-06 — RIR far-field convolution (+ MUSAN combined). Score 710. Blocked: OpenSLR RIR + MUSAN. [W5]**
- **H1:** RIR-augmented enrollment recovers the far-field FRR loss already measured in the condition-sim
  grid (reverb is a top degrader there).
- **DoD:** far-field-condition FRR vs baseline; combined RIR+MUSAN vs each alone.

**28. E07-05 / E07-03 / E07-06 — QbE student distillation (WavLM → ~1–2M, phoneme-supervised ZP-KWS-class). Score 680 (feasibility-capped; highest ceiling). Blocked: GPU + CC-BY training data (MSWC / Speech Commands v2). [W3]**
- **H1:** a ~1–2M-param student preserves ≥90% of WavLM's dysarthric separability at ≤2 MB / <10 ms per
  frame, **while staying language-independent + 1-shot** (the CP-1 gate).
- **DoD:** student rank-1 / FRR @0.5 FA/hr vs the WavLM ceiling; on-device size/latency; a Common-Voice
  language-independence pass (→ N+8). The CP-1 build itself; N+9/E07-02/E07-12 set its architecture.

**29. N+11 / E17-01 + E17-03 — Duration cross-verify product impl + real-ambient FA/hr + audio watchdog. Score 730. Blocked: physical device / ≥6 h real household ambient. [W6]**
- **H1:** the banked duration cross-verify holds on **real** household audio (TV, conversation, kitchen)
  — not just LibriSpeech — and an `AudioRecord` watchdog auto-restarts silent-mic failures.
- **DoD:** real-ambient FA/hr with vs without duration cross-verify; watchdog recovers an injected silent
  stream; crash-loop backoff triggers at the configured rate. Ships the one banked CP-2 lever.

**30. CP-0 / E10-02 — SAP corpus re-measurement (larger, digital-assistant-commands split). Score 630 (gate-capped; foundational). Blocked: SAP DUA (longest lead — start now). [all walls]**
- **H1:** with dense negatives (SAP has a "digital-assistant commands" category, 959 speakers), (a)
  per-command calibration flips from non-improvement to a real FAR reduction, and (b) dysarthric FRR/FAR
  becomes deployment-trustworthy at n≫267.
- **DoD:** the E09-02 calibration re-test on dense negatives + cross-corpus (TORGO→SAP) FRR/FAR. Without
  it, every dysarthric number rests on 3 TORGO speakers. **Start the DUA immediately — lead time is the cost.**

---

## 5. Recommended execution order

```
NOW (this host, no new assets — the ≤1-day tranche):
  1. N+7   Vocabulary-optimized enrollment      ← THE FORK: run first, it redirects W1 vs W3
  2. N+4   Dual-cascade control verification     (cheapest; script exists; de-risks the banked win)
  3. E02-08 Dual-filter FRR/FAR eval             (highest-scored built-but-unmeasured MFCC lever)
  4. E04-06 Multi-frame wake persistence          (highest-scored wake lever, ~5 LOC)
  5. N+5   Energy-ratio cross-verify
  6. E01-11 Confirm 30ms/30%/static config (paired)  ← unlocks a free +6pp if it survives the paired test
  7. N+9   DistilHuBERT size floor  ·  8. N+10 Learned MLP  ·  9. E07-02 layer sweep  ·  10. E07-08 fusion

NEXT (this host, small build each):
  E10-03 bootstrap CI · E10-07 open-set OOV · E10-01 DET/Cllr   (measurement rigor — do alongside)
  E13-08 aug · E06-09 z-score · E12-09 synth-negatives · E06-05 rate-adaptive band · E08-03 greedy select
  E04-02/01 wake calib · E04-08 neg templates · E09-08/E02-05 hysteresis+kNN · N+12 PCA probe · E19-01 3-stage

GATED (acquire the asset first — start in parallel, longest-lead first):
  CP-0/SAP DUA  (start immediately — weeks of lead)
  N+8 Common Voice  (~2h build)      →  language-independence gate
  N+6/E05-04/E05-05  noise corpora   →  W5 noise robustness
  E07-05 QbE distillation (GPU)      →  W3 the CP-1 build
  N+11 product impl + real-ambient (device)  →  W6 ship the banked lever
```

**Decision gate at N+7:** if optimized-15 ≤10% FRR → the next tranche is W1 (distinctness optimization:
E08-03, E06-05, the `VocabularyDistinctness` recommender). If ≈25% → redirect to W3 (E07-02 → N+9 →
E07-12 → E07-05 distillation). Do not commit the CP-1 GPU spend before N+7 answers this.

---

## 6. Scoring + runnable-here matrix

| # | ID | Wall | Score | Runnable here? | Blocker |
|---|---|---|---|---|---|
| 1 | N+7 / E08-11 | W1 | 870 | ✅ | — |
| 2 | N+4 | W2 | 770 | ✅ **RUN** (DoD met, b=0) | — |
| 3 | N+5 / E02-11 | W2 | 740 | ✅ | — |
| 4 | N+10 / E09-11 | W2 | 760 | ✅ | — |
| 5 | N+9 / E07-11 | W3 | 760 | ✅ | model download |
| 6 | E07-02 | W3 | 720 | ✅ | — |
| 7 | E07-08 | W3 | 730 | ✅ | — |
| 8 | N+12 / E07-12 | W3 | 710 | ✅ | — |
| 9 | E01-11 | W1/W3 | 760 | ✅ | — |
| 10 | E06-05 | W1 | 710 | ✅ | — |
| 11 | E02-08 | W2 | 810 | ✅ | — |
| 12 | E09-08+E02-05 | W2 | 670 | ✅ | — |
| 13 | E13-08 / E03-09 | W1/W5 | 760 | ✅ | — |
| 14 | E06-09 | W1 | 720 | ✅ | — |
| 15 | E12-09 | W2 | 710 | ✅ | — |
| 16 | E08-03 | W1 | 740 | ✅ | — |
| 17 | E04-06 | W2 | 860 | ✅ | — |
| 18 | E04-02+E04-01 | W2 | 810 | ✅ | — |
| 19 | E04-08 | W2 | 760 | ✅ | — |
| 20 | E10-07 | W2/eval | 750 | ✅ | — |
| 21 | E10-03+E10-05 | eval | 760 | ✅ | — |
| 22 | E10-01 | eval | 730 | ✅ | — |
| 23 | E19-01 | W3/W6 | 740 | ◑ | accuracy ✅ / latency needs device |
| 24 | N+8 / E07-10 | W4 | 710 | ◑ | Common Voice download |
| 25 | N+6 / E05-07 | W5 | 750 | ◑ | noise corpus build |
| 26 | E05-04 | W5 | 760 | ✗ | MUSAN corpus |
| 27 | E05-05/E05-06 | W5 | 710 | ✗ | RIR + MUSAN |
| 28 | E07-05/03/06 | W3 | 680 | ✗ | GPU + CC-BY data |
| 29 | N+11 / E17-01/03 | W6 | 730 | ✗ | physical device / real ambient |
| 30 | CP-0 / E10-02 | all | 630 | ✗ | SAP DUA |

**Summary:** 22 fully runnable on this host today, 3 semi-runnable (need a bounded download/build), 5
blocked on an external asset (MUSAN, RIR, GPU, device, SAP DUA). The `NOW` tranche (10 experiments) needs
zero new assets.

---

## 7. Reproduce

- **WavLM / CP-2 spikes (N+4/5/7/9/10/12, E07-02/08):** `research/.venv/bin/python3
  scripts/eval/ssl_frontend_spike/dual_cascade_verify.py <SPEAKERS> <BG_MIN>` (extend per stage). Data:
  `~/torgo`, `~/picovoice-benchmark/prepared/librispeech`. CPU-only; WavLM-base-plus via `transformers`.
- **MFCC-DTW config (E01-11, E02-08, E06-05, E06-09, E08-03, E13-08, E09-08, E02-05):**
  `./gradlew :core:eval:test -Dtorgo.dir=$HOME/torgo -Dtorgo.grid=true` (with the JDK-21/`ANDROID_HOME`
  env from `CLAUDE.md` §1.2).
- **Wake/FAR (E04-06, E04-02/01, E04-08):** `AmbientFar` + `WakeGatedRecognizer` in `:core:eval` /
  `:core:enrollment`; LibriSpeech ambient.
- **Discipline (every run):** pre-register one hypothesis, fidelity-check the baseline, McNemar / exact
  binomial at matched FAR, replicate on ≥2 speakers, bank only what replicates (EVAL-002/003/004/005).
