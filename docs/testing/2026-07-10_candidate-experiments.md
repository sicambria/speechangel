# Candidate experiments campaign — §13 of the SOTA-950 report

**Started:** 2026-07-10 · **Harness:** `scripts/eval/ssl_frontend_spike/` (cached embeddings + TORGO + Picovoice ambient)
**Source list:** `docs/research/2026-07-10_sota-950-innovation-report.md` §13 (30 candidates A1–F30, NOT pre-registered).
**Discipline:** EVAL-003 — each experiment gets ONE a-priori hypothesis + a FAR-matched adjudication gate *before* it runs;
survivors need fresh confirmation before banking. Dead-ends are first-class results.

## Environment reality (bounds what is runnable)

- **CPU-only torch** (`torch 2.13+cpu`, `cuda False`) → GPU-day encoder training (C16–C21) is infeasible on this host.
- **Corpora present:** TORGO (dys F01/F03/F04 + control FC01/02/03), Picovoice benchmark (LibriSpeech test-clean =
  other-speaker English; common-voice = multilingual OOV; DEMAND = real ambient noise; wake-word streams).
- **Absent:** MSWC, UASpeech, a typical word-repeat corpus → A5, C16–C22, D23, F30 are corpus-blocked (proxies noted).
- **Cached embeddings:** `wavlm-large` (25×1024, unit, 2217 utts), `wavlm-base-plus` (13×768), `distilhubert` (3×768),
  `large_frames_L14` (frame-level, 267 dys utts), distill teacher set.

## Banked baselines this campaign measures against

- D2 (dysarthric, held-out FRR@FAR≤5%, in-vocab OOV negatives): ~50–55% → the "0.70 AUC wall".
- D2 (typical/control, held-out distinct-slice + few-shot + margin): **13.8%** → band 800.
- Central lever under scrutiny: min-over-K few-shot aggregation; the K-curve K=4 ≤15% structural claim.

---

## Status table (updated live)

| ID | Title | Runnable? | Status | Headline result |
|----|-------|-----------|--------|-----------------|
| A1 | Fixed-subset K-curve | ✅ cached | **done** | Lever real (K4=11.1% ≤15%, band-800 holds); variable curve inflated +23pp by word selection |
| A2 | Deployment-real negatives vs dys wall | ✅ cached+embed | **done** | ⭐ 0.70 wall is negative-set artifact: dys AUC 0.68(confusors)→0.99(ambient); problem is in-vocab confusion only |
| A3 | FAR%→FA/hr bridge (+A3b) | ✅ PV ambient | **done** | ⭐ base+ (94MB, band-800 on GSC-24) → 0 FA/hr on real ambient (pt est; UB~6) — coherent on-device band-800; A3b |
| A4 | Severe-dys scatter decomposition | ✅ cached | **done** | Structured: dys scatter dominated by duration(F03 r=.80)/loudness(F04 r=.66) axis → F29/F28 motivated |
| A5 | K-curve replication, 2nd corpus | ✅ GSC (downloaded) | **done (24 spk)** | ⭐ ROBUST: GSC-24 K4=8.2% monotone; the ONE lever that replicated across corpora/populations |
| B6 | Aggregation-rule sweep | ✅ cached | **done** | Conditional (not ⭐): mean2 helps high-variance (TORGO/dys) but −2.5pp on clean GSC-24; variance-dependent |
| B7 | KDE likelihood-ratio scoring | ✅ cached | **done** | Null as gate (monotone→same ROC); useful only as fusable feature |
| B8 | First-attempt-as-template retry | ✅ cached | **done** | +19pp task-FRR; attempt-correlation is exploitable signal (small n=26) |
| B9 | SPRT sequential protocol | ✅ cached | **done** | Best 2-attempt: 34.6%→7.7% task-FRR at matched task-FAR; controls both by construction |
| B10 | Margin-zone width optimization | ✅ cached | **done** | +11.5pp task-FRR (δ≈0.05), retry only near-misses |
| B11 | Per-command-set confusability shaping | ✅ cached | **done** | Negative (−1.9pp) as pre-registered (tighten-only) |
| B12 | Environment-conditioned conformal calib | ✅ cached+ambient | **protocol** | Deferred: A3 shows ambient FA≈0 at global threshold → no headroom to beat here; value only under harder ambient (D23) |
| B13 | Conformal validity engineering | ◐ partial | **done (partial)** | Coverage robust to block (4.7%<5%) & contamination (tightens not loosens); temporal drift queued |
| C14 | Frozen-feature episodic-head ceiling | ◐ CPU proxy | **done** | Dead-end: head degrades transfer (TORGO 13.8→53.7%); frozen features already near-optimal, I1 premise unsupported |
| C15 | Learned layer-mix probe | ✅ cached | **done** | Mix fails; L21 win REFUTED on GSC-24 (layer choice flat 7.5–9.0%) — was n=3 artifact |
| C16 | Architecture bake-off @1% MSWC | ⛔ no MSWC + no GPU | **protocol** | GPU-gated; protocol documented for a GPU+MSWC session |
| C17 | Asymmetric clean-support/noisy-query | ◐ sim proxy | **done** | Matched-noisy support helps only +3pp (only when adding budget) |
| C18 | Relational KD | ◐ CPU proxy (cached teacher) | **done** | ⭐ RKD nearly doubles student QbE: 19.7→35.0% rank-1 (+15.3pp); distance-structure is what QbE consumes |
| C19 | MSWC domain-gap audit | ◐ GSC proxy | **done** | Student excels at isolated words (GSC 85.7% vs TORGO 19.7%); citation-domain shift helps (vocab-size confound noted) |
| C20 | Phrase-length generalization | ◐ TORGO multi-word | **protocol** | Real test needs encoder retrain; thin proxy only, protocol documented |
| C21 | Deployable-gap decomposition (+C21b) | ✅ cached | **done** | 94MB base+ IS band-800 (skip distillation); but "beats 316MB ceiling" REFUTED on GSC-24 (large 7.5% < base+ 10.3%) |
| C22 | D10 multilingual pilot | ◐ CV proxy (no MSWC) | **protocol** | Language-independence architecturally guaranteed; per-lang rank-1 needs MSWC (protocol documented) |
| D23 | Power-compliant ambient corpus | ⛔ corpus assembly | **protocol** | A3/A3b cover the point estimate (0 FA/hr); ≥60h certification for UB<1 documented |
| D24 | Stage-correlation audit | ✅ PV streams | **done** | Stages correlated ~2.2× (conditional≫marginal FAR2); compound-FAR independence optimistic — inflate 950 stage-2 budget |
| D25 | Other-speaker FA measurement | ✅ cached | **done** | other-same-word FA 31%! speaker gate justified; severe dys more speaker-dependent (F01=0.9%) |
| E26 | D5 loss decomposition by RT60 | ◐ sim | **done** | Reverb loss intrinsic-dominated (aug recovers <50%); dereverb I10 has a role at mild RT60 |
| E27 | K-budget allocation factorial | ◐ sim | **done** | ⭐ At FIXED K=4, {4 clean} BEATS mixed allocations — multi-condition additive only when it ADDS templates |
| F28 | Multimodal enrollment | ✅ cached | **done** | Dead-end (−0.029): discrete clustering hurts → corroborates A4 continuous scatter |
| F29 | Query-side rate normalization | ◐ re-embed | **done** | 🔴 REFUTES A4: rate-norm HURTS dys AUC 0.68→0.45; duration axis is symptom not lever |
| F30 | UASpeech block-drift | ◐ TORGO session proxy | **done** | Dys plateau = within-session variability not drift (ratio 1.15<ctl 1.84); relax dys re-enroll cadence |

Legend: ✅ runnable on this host · ◐ proxy/partial only · ⛔ blocked (corpus/GPU) — documented with the protocol for when unblocked.

---

## Executive synthesis (the campaign's through-line)

**26 of 30 candidates executed** (25 with results + D23 partial) (real runs or CPU/GSC/ambient proxies); 4 documented with protocols (C16
GPU-gated, C20/C22 corpus-gated, B12 no-headroom-here). The dominant finding is methodological and it
**vindicates EVAL-003**: *raw frozen SSL + few-shot enrollment is the robust core, and most proposed
refinements do not survive independent-corpus replication.*

**🟢 ROBUST — replicated across corpora/populations (bank-candidates, still need fresh pre-registered confirm):**
- **The few-shot K-curve (A1 + A5).** Real on TORGO-control fixed subset (K4=11.1%) AND GSC-24 (K4=8.2%,
  monotone). The one lever that held across corpus, population, and scale. Band-800-typical survives the
  confound repair.
- **Relational KD (C18).** Distance-structure distillation nearly doubles the `<2 MB` student's QbE
  (19.7→35.0% rank-1) vs the two failed feature-copy attempts — the report's hypothesis, confirmed.

**🟢 EVIDENCE-BASE UPGRADES (the A-series mandate — three caveats resolved *favorably*):**
- **A2 — the "0.70 dys wall" is largely a hard-negative-set artifact.** Against real deployment negatives
  dys AUC is 0.89 (other-speaker) / 0.99 (ambient); the wall is *only* same-speaker in-vocab confusion.
  Materially upgrades the dysarthric outlook: the problem is command-set design (D14), not a separability ceiling.
- **A3 + A3b — the FAR%/trial vs FA/hr mismatch reconciles favorably, on ONE coherent encoder.** wavlm-base+
  (94 MB, band-800 on GSC-24) yields **0 FA/hr** on real ambient (point est; 95% UB ~6 on 0.5 h → D23 tightens)
  — a coherent 94 MB-on-device band-800 claim. In-vocab confusors ≫ real ambient as negatives (the
  per-trial-FAR extrapolation was wrong). NB the specific base+ *L10* pick was an n=3 artifact (C21b); the
  94 MB *encoder* being band-800 survives on GSC-24 (deep layers 10–12%).
- **C21 (softened by C21b) — a 94 MB on-device encoder reaches band-800.** wavlm-base+ (94 MB) is band-800
  typical on GSC-24 (deep layers 10–12%), so the lossy <2 MB distillation is unnecessary. The stronger TORGO
  reading — "base+ L10 *beats* the 316 MB ceiling" — was an **n=3 artifact, refuted on GSC-24** (there
  wavlm-large 7.5–8.2% beats base+ 10.3%). Deployment story survives; "beats the ceiling" does not.

**🔴 REFUTED / DEAD-ENDS (each a first-class result; several caught by GSC-24 replication):**
- **C15 L21 layer win** — REFUTED on GSC-24 (layer choice flat 7.5–9.0%); was an n=3 TORGO artifact.
- **B6 mean-of-best-2** — does NOT generalize (−2.5 pp on clean GSC); variance-dependent, not universal.
- **C14 episodic head** — degrades transfer (TORGO 13.8→53.7%); frozen features already near-optimal.
- **F29 rate-norm** — HURTS dys (AUC 0.68→0.45); A4's duration axis is a symptom, not a lever.
- **F28 discrete-variant enrollment** (−0.03), **B7 KDE-LR** (null), **B11 confusability-tighten** (−1.9 pp).

**🟡 PROMISING BUT UNDERPOWERED / CONDITIONAL (need bigger n before banking):**
- **B8/B9/B10 sequential 2-attempt** — SPRT cuts task-FRR 34.6→7.7% at matched task-FAR, but n_g=26.
- **B6 mean2 / softmin** — genuinely helps high-variance speech (TORGO-control, dysarthric) at FAR≈5%.

**🔵 DIAGNOSTICS (design guidance, not levers):**
- **D25** — other-same-word FA 31% ⇒ a personal-VAD/speaker gate is justified (severe dys self-protects, F01=0.9%).
- **F30** — dys plateau is within-session variability, not drift ⇒ relaxed re-enrollment cadence for dys.
- **B13** — conformal coverage robust to block structure (4.7%<5%) and to genuine contamination (tightens, not loosens).
- **A4** — dys scatter is structured (duration/loudness axis) but not actionably so (see F28/F29).

**One-line takeaway for the SOTA-950 report:** the campaign strengthens the *typical* band-800 story on two
independent axes (K-curve replicated on GSC-24; coherent 0-FA/hr at 94 MB) and **sharpens the *dysarthric*
picture** (A2: the *idle-reject* axis is band 900, not a hard ceiling) — while retiring six proposed
refinements that looked good on n=3 but failed to replicate.

**▶ Round-2 (dysarthric → 800):** the dysarthric composite was **re-scored with deployment-real negatives**
and a 30-experiment Round-2 plan drafted — see **`docs/testing/2026-07-10_dysarthric-800-rescore-and-plan.md`**.
Key result: idle-reject is solved (band 900 vs ambient) but the composite stays bound at **~500** by
**in-vocab command confusion (68%)** and **other-speaker-same-word (87%)**; the lead scout (G3
nuisance-subspace removal) **refuted under honest fold-held-out evaluation** (a leak artifact — the 5th such
catch). Dysarthric-800 remains open research with a now well-characterized wall.

---

## Blocked / GPU-gated experiments — pre-registered protocols (for when unblocked)

These cannot be honestly *banked* on this host (no CUDA; MSWC/UASpeech absent). Documented so a GPU+corpus
session runs them without re-deriving the design. Partial CPU proxies attempted where cheap (noted).

- **C16 — architecture bake-off @1% MSWC.** Needs MSWC (CC-BY, ~GB/lang) **and** a GPU (BC-ResNet vs
  ECAPA-lite vs tiny-conformer training). Protocol: 1% MSWC-en episodes, matched ~250 k params, episodic
  metric loss, eval rank-1/AUC on held-out GSC. On CPU a single epoch of any of these is hours → **⛔ GPU**.
- **C18 — relational KD.** Distill the teacher's *pairwise distance structure* (RKD) not features/logits.
  The cached `distill_teacher_6000.npz` (6000 episodes) + `distill_student.py` exist → an **RKD loss on
  cached teacher features is CPU-feasible** (no teacher forward). **Attempted as a proxy** (see log).
- **C19 — MSWC domain-gap audit.** Core question ("does the student generalize from forced-aligned MSWC to
  isolated citation words?") is now testable: validate cached `student.pt` on **GSC** isolated words vs its
  training-domain metric. **Attempted as a proxy** (GSC now downloaded).
- **D23 — power-compliant ambient corpus (≥60 h).** Full 60 h household assembly is out of scope, but A3's
  streamer runs on all of DEMAND + LibriSpeech (several hours). **Attempted as a multi-hour extension** to
  tighten A3's FA/hr 95% upper bound below 5 (see log). True 60 h + power profiling remains ⛔.
- **C20 — phrase-length generalization.** Needs concatenated-word / multi-word episodes. TORGO's normalizer
  keeps ≤2-word prompts, so a *thin* proxy (2-word vs 1-word command rank-1) is possible, but the real test
  (random-crop multi-word training + multi-word phrase eval) needs an encoder retrain → **◐ thin proxy only**;
  protocol: train student with concatenated 1 s single-word crops, evaluate on 2–3-word phrases from a
  self-recorded command set. Deferred as low-value vs the confirmed levers.
- **C22 — D10 multilingual pilot.** Language-independence is **architecturally guaranteed** (QbE matches
  acoustic templates; there is no language model, lexicon, or ASR anywhere in the pipeline — see CLAUDE.md §4
  hard constraints). The *empirical* question is whether the frozen SSL encoder's representation quality is
  uniform across languages — which needs MSWC (isolated words, matched vocab, per language). CommonVoice is
  present but is continuous sentences (no per-speaker word repeats) → no clean per-language rank-1. **⛔ needs
  MSWC** for the real pilot; protocol: frozen wavlm-large QbE rank-1/AUC per language on MSWC, 5 typologically
  diverse languages, matched vocab. A CV same-clip-vs-augmentation retrieval proxy is too weak to bank.
- **B12 — environment-conditioned conformal calibration.** Cluster the ambient pool by running noise-floor
  state, calibrate a per-state conformal threshold, switch deterministically. Runnable in principle by binning
  A3's ambient stream by energy, but A3 already showed ambient FA ≈ 0 at the single global threshold → the
  per-state refinement has **no headroom to demonstrate on this ambient** (you cannot beat 0 FA/hr). Value
  reappears only under a harder ambient distribution (TV-on, babble) → documented, deferred to the D23 corpus.

## Log (chronological — insights, dead-ends, wins)

### B6/B7/B11 — single-attempt decision-layer variants · ✅ DONE · `b_single.py` (wavlm-large L15, typical)

Harness validates itself: **min-agg reproduces the banked 13.8%** exactly (@FAR 4.6%).

| Arm | Rule | FRR @ matched FAR≈4.5% | Δ vs min |
|---|---|---|---|
| B6 | min (banked) | 13.8% | — |
| **B6** | **mean-of-best-2** | **9.4%** | **+4.4 pp** ⭐ |
| B6 | softmin (T=0.05) | 10.0% | +3.7 pp |
| B6 | mean | 11.3% | +2.5 pp |
| B6 | median | 11.9% | +1.9 pp |
| B7 | KDE likelihood-ratio | 13.8% | +0.0 pp |
| B11 | confusability shaping | 15.6% | −1.9 pp |

**BIG WIN (B6, exploratory):** **mean-of-best-2 aggregation → typical D2 13.8%→9.4%** at matched FAR, from a
one-line decision-rule change. Mechanism: `min` over K templates is a noisy extreme order statistic
(one unlucky template dominates); averaging the two nearest denoises genuine scores while impostors' 2nd-
nearest stays far → better separation. Softmin (logsumexp, T=0.05) confirms the same denoising direction.
→ **A1's finding that K=3 already floors min-agg is consistent**: the gain now comes from the *aggregator*,
not more templates. Per EVAL-003 this is NOT banked — needs a fresh, pre-registered, FAR-matched
confirmation (queued below: dys population + FAR-sensitivity robustness).

**Dead-ends (honest nulls):**
- **B7 KDE-LR** adds nothing as a standalone threshold (monotone transform of d1 ⇒ same ROC ⇒ same FRR@FAR).
  Its real role is a continuous *fusable feature* for the dual-cascade (B9/verifier), not a gate. Confirmed.
- **B11 confusability shaping** (tighten-only per-command threshold) trades FRR for FAR the wrong way
  (−1.9 pp). A symmetric loosen+tighten variant might recover, but as pre-registered it loses.

**B6 CONFIRMATION (FAR-sensitivity + dys) — mean-of-best-2 is operating-point-specific:**

| population | FAR≤5% | FAR≤2% | FAR≤1% |
|---|---|---|---|
| typical: Δ(mean2 vs min) | **+4.4 pp** | −3.7 pp | −1.9 pp |
| dysarthric: Δ(mean2 vs min) | **+4.3 pp** | +1.4 pp | +0.7 pp |

The win **replicates on the dysarthric population** at FAR≤5% (+4.3 pp — cross-population) but **reverses at
tighter FAR** for typical (averaging blurs the tail that low-FAR separation needs).

**🔴 DOES NOT REPLICATE ON GSC-24 (2026-07-10):** on clean isolated citation words, mean-of-best-2 is
**−2.5 pp WORSE** than min (L15: min 8.2% vs mean2 10.7%). So the B6 win is **NOT a universal aggregator
improvement** — it is **variance-dependent**: mean-of-best-2 denoises only when within-word variability is
high (TORGO-control spontaneous speech, dysarthric) and *hurts* on low-variability clean speech (GSC). The
mechanistic story is coherent (you can only denoise noise), and the deployment population (real users,
spontaneous/impaired speech) is closer to TORGO than to GSC citation words — so it *may* still help in
deployment — but it is now a **conditional, unconfirmed** lever, not the headline win first recorded.
Downgraded from ⭐. Only the K-curve (A5) survived independent-corpus replication.

---

### B8/B9/B10 — sequential 2-attempt protocols · ✅ DONE · `b_seq.py` (wavlm-large L15, typical, matched task-FAR≤5%)

| Protocol | task-FRR | task-FAR | Δ vs single |
|---|---|---|---|
| P1 single (ref) | 34.6% | 2.8% | — |
| B10 margin-zone retry (δ≈0.05) | 23.1% | 1.1% | +11.5 pp |
| B8 attempt-1-as-template | 15.4% | 2.0% | +19.2 pp |
| **B9 SPRT (Wald bounds)** | **7.7%** | 3.1% | **+26.9 pp** |

**WIN (exploratory):** all three 2-attempt protocols cut task-FRR at matched task-FAR; **B9 SPRT** is best
and, crucially, controls task-FRR *and* task-FAR by construction — the principled artifact §7.2 (X3) was
missing. B8 confirms attempt-correlation is exploitable *as signal* (adding attempt-1 as a temporary
template beats vanilla margin-zone retry by ~8 pp) — the exact opposite of treating attempts as i.i.d.

**Honest caveats (weighting down the magnitude):** (1) n_g = 26 genuine tasks → coarse resolution
(each task ≈3.8 pp), wide CIs; (2) P1 here = 34.6% is a *harder* paired-rep task construction, **not** the
banked 13.8% per-trial D2 — so read these as a *relative* protocol ranking, not a new absolute D2;
(3) in-sample threshold (consistent across arms). Confirmation queued: dys (F03 has more reps) + held-out θ.

---

### C14 — frozen-feature episodic-head ceiling probe · ✅ DONE (proxy) · `c14_episodic.py` (train head on GSC-24, eval held-out GSC + TORGO)

| config | held-out GSC D2 | TORGO-control D2 |
|---|---|---|
| raw wavlm-large L15 cosine (no head) | 7.1% | 13.8% |
| + trained episodic metric head | 11.3% (−4.2 pp) | **53.7%** (−39.9 pp) |

**Dead-end (gate FAIL, decisively).** A prototypical metric head over frozen L15 *degrades* QbE — mildly on
held-out GSC and catastrophically on TORGO transfer (13.8→53.7%). The head overfit the GSC training
distribution and destroyed the raw representation's cross-corpus transfer. **I1's premise ("the objective,
not encoder capacity, is the gap → a learned head recovers it") is NOT supported here**: the frozen SSL
representation is already near-optimal for cosine QbE, and a small head trained on limited episodes is a
liability. Reinforces the campaign's dominant theme — **raw frozen SSL + few-shot enrollment (the K-curve
lever) is robust; bolt-on learned refinements (C15 layer-mix, B6 mean2-on-clean, C14 head) overfit or fail
to transfer.** (Caveat: a heavily-regularized head with far more data/augmentation might differ; as
pre-registered on this data scale it fails clearly.)

---

### C18 + C19 — relational KD + domain-gap audit · ✅ DONE (proxy) · `c18_c19_distill.py` (CPU, cached teacher/student)

**C18 — relational KD is a WIN (PASS):**

| student | TORGO control rank-1 |
|---|---|
| feature-copy (MSE to teacher emb, the banked attempts) | 19.7% |
| **relational KD (RKD-D, match pairwise distance structure)** | **35.0%** (+15.3 pp) |

**Distance-structure distillation nearly doubles the `<2 MB` student's QbE quality** vs feature-copy. The
report's hypothesis is confirmed: *the pairwise distance structure — not raw features/logits — is what QbE
consumes*, and the two prior failed distillation attempts were feature-copy. This materially de-risks the X1
deployable-encoder build. (Both numbers are over TORGO's ~90-word vocab, so absolute rank-1 is low; the
RKD-vs-feature-copy *delta* at matched vocab is the robust result. Still below the wavlm-large teacher ~74%
— RKD helps a lot but doesn't fully close the gap; confirm on GSC + tune RKD-angle term next.)

**C19 — domain-gap audit (GSC proxy):** feature-copy student rank-1 = **85.7% on GSC** isolated citation
words vs **19.7% on TORGO** control. The feared MSWC-forced-aligned→citation-word shift does **not** hurt —
the student is *strongest* on clean isolated words, which is exactly the deployment command type. **Confound
flagged:** GSC here is 8-way vs TORGO ~90-way, so the 66 pp gap is partly vocabulary size, not pure domain;
the honest read is "the tiny student is viable for small-vocab isolated-command QbE (its intended use)."

---

### C21 — deployable-gap decomposition · ✅ DONE · `c21_deployable_gap.py` (typical D2, held-out, cached ladder)

| encoder | size | typical D2 FRR (min) | (mean-of-best-2) |
|---|---|---|---|
| wavlm-large L15 | 316 MB | 13.8% | 9.4% |
| **wavlm-base+ L10** | 94 MB | **12.0%** | 12.0% |
| wavlm-base+ L12 | 94 MB | 17.2% | 16.0% |
| distilhubert L2 | 23 MB | 21.7% | 21.7% |

**Decomposition (min-agg):** total deployable gap **+7.9 pp** = capacity (large→base) +3.4 + distillation
(base→distil) +4.5 (+INT8 residual ~1-2 pp, unmeasured). The real bottleneck is distilhubert's shallow
3-layer depth (21.7%), not parameter count.

**⚠️ TORGO-n3 CLAIMS PARTLY REFUTED by C21b (GSC-24, advisor catch):** the on-TORGO reading "**base+ L10
(94 MB) beats the 316 MB ceiling** (12.0% vs 13.8%)" was a **single-layer pick on 3 speakers** — the same
methodology as the refuted C15/L21. On GSC-24 (`c21b_base_layers.py`): base+ L10 = 11.7%, **L12 = 10.3%**
(L12 better, not L10), and **wavlm-large (7.5–8.2%) actually beats base+ (10.3%)** — so "base+ beats the
ceiling" and "L10 specifically" are **REFUTED** cross-corpus. **What SURVIVES:** base+ (94 MB) *is* band-800
typical on GSC-24 (deep layers L9–L12 = 10–12% ≤ 15%), so **a 94 MB on-device encoder reaches band-800 and
the lossy <2 MB distillation is unnecessary** — the deployment recommendation holds in softened form (serve
a 94 MB encoder; wavlm-large stays marginally better if the extra ~220 MB is affordable). See C21b + A3b.

---

### C21b — cross-corpus confirmation of the base+ deployment layer · ✅ DONE · `c21b_base_layers.py` (GSC-24, base+ all layers)

Triggered by the advisor catch that C21/A3b's headline used a base+ L10 pick on n=3 TORGO speakers (the same
methodology as the refuted C15/L21). base+ layer sweep, GSC-24, K=4 held-out FRR@FAR≤5%:

| layer | GSC-24 D2 | | layer | GSC-24 D2 |
|---|---|---|---|---|
| L9 | 11.3% | | **L10** (deploy pick) | 11.7% |
| **L11** | 10.6% | | **L12** | **10.3%** |

**Result:** L10 does **not** keep its edge — L12 (10.3%) beats L10 (11.7%) on GSC-24 (TORGO-n3 had the
opposite, L10=12.0 ≪ L12=17.2). And wavlm-large on GSC-24 (7.5–8.2%, from A5) **beats** base+ (10.3%). So
the C21 claims "L10 specifically" and "base+ beats the ceiling / skip distillation because it's *better*"
are **n=3 artifacts, refuted cross-corpus.** **What holds:** base+ (94 MB) is comfortably band-800 on GSC-24
(every deep layer 10–12% ≤ 15%) — so the *94 MB-on-device-band-800* deployment story (with A3b's 0 FA/hr)
**survives**, just not the "beats the ceiling" framing. Net: use a 94 MB encoder for band-800 on-device;
wavlm-large is marginally better if you can afford it. This is the third n=3 layer-pick the GSC-24
replication corrected — the campaign's consistency check working as intended.

---

### F29 — query-side rate normalization · ✅ DONE · `f29_rate_norm.py` (dys, wavlm-large L15)

| variant | dys AUC | FRR@FAR5% |
|---|---|---|
| baseline (VAD-trim) | 0.682 | 66.7% |
| F29 (warp to canonical 1.0 s) | **0.450** | 84.6% |

**🔴 A4's PREDICTION REFUTED (gate FAIL, Δ AUC = −0.232):** naive rate normalization *destroys* dys
separability, not improves it. Warping every utterance to a fixed duration (a) removes duration information
that *discriminates command words* (different words have different natural lengths) and (b) injects
resampling artifacts SSL embeddings are sensitive to. ⇒ **the duration axis A4 found (F03 r=0.80) is a
*symptom* of within-word variability, not a causally exploitable lever** via time-warping.

**Honest close of the dysarthric-mechanism arc (A4→F28→F29):** the severe-dys in-vocab scatter is structured
(A4) but neither discretely clusterable (F28, −0.03) nor compressible by rate-norm (F29, −0.23). The simple
normalization levers fail. The reassurance is external: **A2 showed the in-vocab wall is not the
deployment-binding problem** (dys vs real ambient AUC = 0.99). So the dysarthric path forward is
command-set/vocab-distinct design (attack in-vocab confusion) + the speaker gate (D25), not scatter-flattening.

---

### F30 — TORGO session-drift proxy (UASpeech block-drift stand-in) · ✅ DONE · `f30_session_drift.py`

| speaker | within-session med dist | cross-session med dist | cross/within ratio |
|---|---|---|---|
| F03 (dys) | 0.046 | 0.053 | **1.15** |
| FC03 (ctl) | 0.013 | 0.024 | 1.84 |

**Finding:** the severe-dys plateau is **within-session variability, not temporal drift** — dys cross/within
ratio (1.15) is small *and below* control's (1.84). Dys within-word distances are ~3.5× larger absolutely
(0.046 vs 0.013), so short-term scatter dominates and session drift adds little → **re-enrollment cadence
can be relaxed for dys**; I2's conformal pool does not need heavy recency weighting for this population.
Conversely typical speakers *do* drift session-to-session (1.84 vs a tight 0.013 baseline) → multi-session
enrollment (D13) is genuinely worth more for **typical** users. Consistent with A4 (intrinsic scatter).
**Caveat:** only F03 (dys) + FC03 (ctl) have multi-session cache coverage → directional, small-n; UASpeech
B1/B2/B3 remains the proper test (license-gated, protocol documented for when available).

---

### F28 — multimodal (per-variant) enrollment · ✅ DONE · `f28_multimodal.py` (dys, wavlm-large L15)

| speaker | flat AUC | per-variant (k=2) AUC | Δ |
|---|---|---|---|
| F03 | **0.841** | 0.812 | −0.029 |

**Dead-end (predicted by A4):** discrete-variant KMeans enrollment is **worse** than flat few-shot (−0.029),
gate FAIL. This **corroborates A4**: severe-dys scatter is *continuous* (a duration/loudness axis), not
discrete categorical variants — so clustering fragments templates without denoising. The correct lever is
**F29 continuous rate/gain normalization**, not per-cluster enrollment. Clean scientific chain: A4 diagnosed
→ F28 falsified the discrete hypothesis → F29 tests the continuous one.
**Side-finding:** F03 *alone* reaches 0.841 AUC vs in-vocab confusors with few-shot enrollment — far above
the aggregate "0.70 wall"; the wall is driven by the most-severe speakers (F01/F04), not F03. (Feeds A2.)

---

### B13 — conformal validity engineering · ✅ DONE (partial) · `b13_conformal.py` (cached negative-side; ambient/temporal = queued)

- **(a) Exchangeability:** realized held-out FAR — i.i.d. split 2.5%, **block split 4.7%** (target 5%). Block
  structure inflates realized FAR but stays under target → conformal coverage is **robust** on the in-vocab
  negative distribution; exchangeability risk mild. (Ambient-stream autocorrelation is the harder case —
  needs the A3 streamer, queued.)
- **(b) Contamination:** injecting genuine into the calibration pool does **not** inflate FAR — it *tightens*
  the α-quantile threshold (realized FAR 5.2%→1.8%→1.0%→0.4% at 0/5/10/20% contamination), trading to an FRR
  cost. ⇒ the **security guarantee (FAR) is robust to user-speech leakage**; the price is availability, not
  false-accepts — a milder failure mode than I2 assumed. Good news for the conformal rejection design.
- **(c)** day-1→day-7 coverage drift: PARTIAL — needs the A3 ambient streamer over time; protocol queued.

---

### E26 + E27 + C17 — channel decomposition, K-budget allocation, asymmetric episodes · ✅ DONE · `e_channel.py` (typical, wavlm-large L15)

**E26 — D5 reverb loss decomposition** (clean ceiling 87.3%):

| RT60 | clean-enroll rank-1 | +reverb-aug enroll | gap | aug recovers |
|---|---|---|---|---|
| 0.15 s | 82.3% | 83.9% | 5.0 pp | 32% |
| 0.30 s | 77.8% | 80.3% | 9.5 pp | 26% |
| 0.60 s | 60.0% | 74.5% | 27.3 pp | 53% |

Reverb loss is **intrinsic-smearing-dominated** (mean recovery <50%, gate says INTRINSIC) — enrollment
augmentation helps but leaves most of the mild/moderate-RT60 gap → **dereverb (I10) has a real role**,
especially at low-moderate RT60 (where aug recovers only 26–32%); heavy reverb is more mismatch-fixable (53%).

**E27 — K-budget allocation at FIXED K=4 (adverse rev30 query) — the non-obvious result:**

| allocation (4 templates) | rank-1 |
|---|---|
| **{4 clean}** | **97.2%** |
| {2 clean + 2 reverb} | 91.7% |
| {1 clean + rev + noise + band} | 91.7% |
| {2 clean + 2 noisy} | 88.9% |

**At a fixed rep budget, all-clean templates BEAT every mixed-condition allocation** — spending slots on
degraded templates *hurts* (−5 to −8 pp). **C17** confirms the mechanism: adding *matched*-noisy templates
(clean-support/noisy-query → +noisy-support) helps only +3.0 pp, i.e. only when it *increases* budget.

**Reconciliation / refinement of the banked lever:** multi-condition enrollment (the banked D4/D5/D6 lever)
is additive **only when it adds templates** — at a *fixed* K (the real product constraint, D13), clean
anchors are higher-quality and win; do NOT trade clean templates for degraded ones. This meaningfully
refines the "multi-condition enrollment is additive" assumption used in `typical_composite.py` (which used
K=99, i.e. added rather than replaced).

---

### D24 — stage-correlation audit · ✅ DONE · `d24_stage_corr.py` (distilhubert L2, 0.3 h real ambient, 2126 windows)

At the deployed FAR≤5% threshold ambient stage-2 accepts = 0 (nothing to correlate), so probed at looser
operating points where stage-2 FAR is nonzero:

| target marginal FAR2 | marginal | conditional \| stage-1 survivor | ratio |
|---|---|---|---|
| 30% | 30.0% | 60.1% | 2.00× |
| 20% | 20.0% | 44.8% | 2.24× |
| 10% | 10.0% | 22.8% | 2.27× |
| 5% | 5.0% | 11.5% | 2.29× |

**Finding (confirms I4's concern, quantified):** stages are **positively correlated ~2.2×** — VAD survivors
(speech-like windows) are ~2.2× more likely to be recognizer-accepted than random windows. So the
compound-FAR independence assumption (stage1_rate × marginal_stage2_FAR) is **optimistic by ~2.2×**; any 950
claim that multiplies marginal cascade FARs must instead use the **conditional** stage-2 FAR (inflate the
stage-2 budget ~2.2×). Moderate, not catastrophic (not 10×) — the cascade still reduces FA, but the
arithmetic needs the correction. (At the actual deployed 0-FA operating point the correlation is moot; this
is the general cascade-design number and the one that bites under harder ambient — TV/babble.)

---

### D25 — other-speaker false-accept measurement · ✅ DONE · `d25_other_speaker.py` (wavlm-large L15, cached)

At each user's FAR≤5% threshold (fit on their own in-vocab confusors):

| user | other-**same-word** FA | other-OOV FA |
|---|---|---|
| FC01 / FC02 / FC03 (typical) | 23.8% / 46.2% / 44.8% | ~1% |
| F01 (severe dys) | **0.9%** | 0.0% |
| F03 / F04 (dys) | 47.5% / 24.5% | ~1–4% |
| **mean** | **31.3%** | 1.4% |

**Finding:** the embedding encodes *what* was said ≫ *who* said it. Another person speaking the user's
command word is accepted ~1-in-3 (31.3%); a different word is reliably rejected (1.4%). ⇒ **speaker-
dependence is weak for same-word utterances → a personal-VAD / speaker-verification gate (I-series) earns
its complexity** (the threat is household members saying the command words, not random ambient — which A3
already showed is ~0 FA). **Silver lining:** severe dysarthria *increases* speaker-dependence — F01's
idiosyncratic productions give 0.9% other-same-word FA (hard to impersonate). Nuance for the threat model:
this vulnerability only bites if non-users say the exact enrolled words.

---

### A2 — dysarthric wall vs deployment-real negatives · ✅ DONE · `a2_negatives.py` (wavlm-large L15)

| impostor / negative set | dys pooled AUC | F01 | F03 | F04 |
|---|---|---|---|---|
| in-vocab OOV confusors (banked, hardest) | **0.682** | 0.727 | 0.668 | 0.789 |
| other-speaker (LibriSpeech) | 0.892 | 0.961 | 0.867 | 0.892 |
| multilingual (CommonVoice) | 0.915 | 0.958 | 0.890 | 0.918 |
| **real ambient (DEMAND)** | **0.989** | 1.000 | 0.985 | 0.983 |

**BIG FINDING (PASS, gate AUC≥0.85 vs ambient):** the severe-dys "0.70 wall" is **largely a hard-negative-set
artifact.** It exists only against same-speaker in-vocab confusors (AUC 0.68); against the negatives that
actually cause deployment FAs — other speakers (0.89), other languages (0.92), ambient noise (**0.99**) —
dys separability is excellent. ⇒ the dysarthric failure mode is **narrow in-vocab confusion (D14)**, not
general false-accept. §7.2(b) ("reject ambient, not confusors") is now evidence-backed. Couples with A3
(ambient trivially rejected) and A4/F28 (the residual in-vocab wall is continuous within-word scatter).
**This materially upgrades the dysarthric outlook**: the deployable problem is command-set confusability
(attack via B11-done/vocab-distinct selection), a far more tractable target than a 0.70 separability ceiling.

---

### C15 — learned layer-mix probe · ✅ DONE · `c15_layermix.py` + proper-harness confirmation

Learned SUPERB-style mix **failed the gate** (10.2% vs best-single-layer 7.1%) — my margin-proxy loss overfit
and collapsed to a single deep layer (24). **But the single-layer sweep surfaced a confirmed lever:**

| layer | typical D2 (min) | (mean-of-best-2) |
|---|---|---|
| L15 (banked) | 13.8% | 9.4% |
| L19 | 9.9% | 10.5% |
| L20 | 9.1% | 10.3% |
| **L21** | **7.0%** | 7.0% |

**Deep layers (L19–L21) roughly halve typical D2 vs the banked L15** (proper held-out harness). The two levers
are partly redundant: mean-of-best-2 helps at L15 (→9.4%) but not at L21 (min=mean2=7.0%) — the deep layer
already captures the denoising. Best single config = **L21 min-agg = 7.0%**.
**⚠️ Forking-paths caveat (EVAL-003):** this is layer-mining on **n=3 control speakers** — post-hoc best-layer
selection is precisely the risk the pre-registration discipline exists to prevent. NOT banked. Adjudicator:
does the deep-layer advantage replicate on GSC (A5's speakers)?

**🔴 REFUTED by A5-24 (2026-07-10):** on the independent 24-speaker GSC corpus, the K=4 layer sweep is flat
(L10=8.1, L12=7.5, L15=8.2, L19=8.1, **L21=8.7**, L23=9.0) — **L21 is not special; layer choice barely matters.**
The dramatic L15→L21 halving was an **n=3 TORGO-control artifact.** "L21→7%" is dead as a general lever. This
is the campaign's cleanest demonstration of why single-population layer-mining must be replicated before use.

---

### A5 — GSC K-curve replication · ✅ DONE (8 spk; scaling to 24) · `a5_gsc_kcurve.py` (wavlm-large L15)

| K | GSC held-out FRR@FAR≤5% | per-speaker (8) |
|---|---|---|
| 1 | 26.6% | 4·71·8·10·27·60·0·31 |
| 2 | 15.9% | 2·44·4·6·17·44·0·10 |
| 3 | 12.0% | 2·38·0·6·8·33·0·8 |
| 4 | **8.3%** | 2·25·0·2·6·27·0·4 |

**BIG WIN (PASS — the load-bearing replication):** the few-shot K-curve **replicates on an independent typical
corpus** (GSC, 8 real speakers): monotone K=1→4, K=4 = 8.3% ≤ 15%. A1's fixed-subset finding was **not**
TORGO-specific — the structural lever is real across corpora and populations.

**SCALED TO 24 SPEAKERS (confirmed + two refutations):** K=1→21.8%, K=2→14.1%, K=3→10.4%, **K=4→8.2%**,
monotone, PASS. The K-curve is now solidly replicated at real speaker-n. Two bonus adjudications from the
all-layer re-embedding:

- **Layer-generalization sweep (K=4, per layer):** L10=8.1 · L12=**7.5** · L15=8.2 · L19=8.1 · L21=8.7 · L23=9.0.
  **Layer choice barely matters on GSC-24 (all within 7.5–9.0%); L21 is middling.** ⇒ **the C15 "L21 halves
  typical D2" finding is REFUTED** as a general lever — it was an n=3 TORGO-control artifact (see C15 update).
- **B6 cross-corpus (min vs mean-of-best-2, K=4):** L15 min **8.2%** vs mean2 10.7% (−2.5 pp); L12/L19 similar.
  **mean-of-best-2 is WORSE on GSC** ⇒ the B6 win does NOT generalize to clean citation-word speech (see B6
  update). It is a **variance-dependent** lever, not universal.

⭐ **Net:** the few-shot K-curve is the ONE lever that robustly replicated across corpora, populations, and
scale. The two decision-layer "wins" (L21, mean2) did not survive the independent corpus — a direct
vindication of the EVAL-003 pre-registration/replication discipline.

---

### A3 — FAR%/trial → FA/hr bridge · ✅ DONE · `a3_far_bridge.py` (T via VAD, FA/hr via distilhubert L2, 0.5 h real ambient)

**Measured:** trigger rate **T ≈ 1842 windows/hr** on real ambient (DEMAND noise 1182/hr, LibriSpeech speech
3156/hr). Ambient false-accepts at the banked FAR≤5%-confusor threshold = **0 / 922 → 0 FA/hr**.

**The bridge, two ways (the point of A3):**

| per-trial FAR (on in-vocab confusors) | typical D2 FRR | naive FA/hr if ambient≈confusors (×T) |
|---|---|---|
| 5.00% (banked) | 13.8% | 92 FA/hr |
| 1.00% | 38.1% | 18 FA/hr |
| 0.27% (naive target for ≤5 FA/hr) | **61.9%** | 5 FA/hr |

**BIG FINDING (resolves the §2 operating-point mismatch — favorably):** the naive extrapolation says "to
reach ≤5 FA/hr you must tighten to FAR≤0.27%/trial, where FRR balloons to 61.9%" — catastrophic. But that
extrapolation is **wrong**: it assumes real ambient is accepted at the same rate as *in-vocab OOV confusors*
(the banked hard negative set). Streaming real ambient shows it is **not** — at the exact banked threshold
(FRR=13.8%) real ambient yields **0 accepts / 922 → 0 FA/hr** (rule-of-three 95% UB ≈ 6 FA/hr on 0.5 h).
⇒ **qualitatively, the per-trial-FAR→FA/hr extrapolation wildly overstates deployment FA because in-vocab
confusors are far harder negatives than real ambient; per-trial FAR≤5% corresponds to ~0 FA/hr, not 92.**
(Reconciles the old "~82 FA/hr" worry — that figure = T × naive-5%, i.e. the *wrong* branch.)

**⚠️ ENCODER-MISMATCH CORRECTION (advisor catch, do not overclaim):** the FRR=13.8% (band 800) is
**wavlm-large L15**, but the ambient-FA=0 was measured on **distilhubert L2** (switched for streaming speed)
— which C21 shows is band-700 (21.7% FRR), *not* 800. So that run certified the FA axis and the FRR axis on
**different encoders**. Resolved by A3b ↓.

**✅ A3b — SINGLE-ENCODER CERTIFICATION (`a3b_base_ambient.py`, wavlm-base+ L10 = C21's 94 MB band-800
encoder):** streamed the same 0.5 h real ambient → **0 / 922 accepts → 0 FA/hr** at that encoder's own
FAR≤5% threshold (T=1842/hr). **Now ONE coherent encoder delivers both FRR = 12.0% (band 800) AND ~0
ambient FA/hr → the band-800-at-94 MB deployment claim is properly supported.** The qualitative resolution
(in-vocab confusors ≫ real-ambient hardness) holds across all three encoders tested (large, base+, distil).
**Caveat:** 0.5 h → 95% UB ≈ 6 FA/hr; **D23 (≥60 h)** is the remaining certification to push the UB < 1.
Bug fixed en route: part-3 FRR-vs-FAR curve was flat (Python default-arg capture) — now threads `target`.

---

### A1 — Fixed-subset K-curve · ✅ DONE · `a1_kcurve.py` (wavlm-large L15)

**Result (typical/control, held-out FRR@FAR≤5%):**

| K | FIXED (7 words, ≥5 rep) | VARIABLE (≥K+1 rep) | word-selection gap |
|---|---|---|---|
| 1 | 19.4% | 42.7% (91 words) | +23.3 pp |
| 2 | 16.7% | 30.1% (70 words) | +13.4 pp |
| 3 | 11.1% | 16.6% (20 words) | +5.5 pp |
| 4 | **11.1%** | 11.1% (7 words) | +0.0 pp |

**BIG FINDING (mixed — one win, one correction):**
- **WIN:** the few-shot lever is *genuinely real*. On a fixed word set it drops FRR 19.4%→11.1% (−8.3 pp) as
  K goes 1→4, and **K=4 = 11.1% ≤ 15% → the band-800 typical claim survives the confound repair.**
- **CORRECTION (dead-end for the steep-curve story):** the banked variable-subset K-curve (42.7%→11.1%)
  overstates the few-shot effect ~3×. At K=1, +23.3 pp of the apparent gap is *word selection* (the ≥5-rep
  filter keeps only 7 easy words), not template count. Any §3 projection that leaned on "few-shot alone buys
  ~30 pp" must re-base to the true **~8 pp** fixed-subset effect.
- **Gate:** clause 1 (K=4 ≤15%) PASS; clause 2 (K=2 gap <5 pp) FAIL at 13.4 pp — the fail *is* the measured
  confound magnitude, exactly what A1 was built to surface.

**Insight:** K=3 already reaches the K=4 floor (11.1%) on the fixed subset → the marginal value of the 4th
template is ~0; the enrollment-UX cost of K=4 vs K=3 buys nothing here. Feeds B6 (aggregation) and D13
(rep budget).

**Dead-end/limitation:** dysarthric speakers have <3 words with ≥5 reps in TORGO → no clean fixed-≥5 dys
curve (data-sparsity, not a method failure). Dys D2 is disorder-capped separately (A2/A4).

---

### A4 — Severe-dys within-word scatter decomposition · ✅ DONE · `a4_scatter.py` (wavlm-large L15)

**Result (within-word residual PCA):**

| Speaker | n | effective rank (PR)/1024 | top-3 PC var | max \|corr\| w/ duration | max \|corr\| w/ loudness |
|---|---|---|---|---|---|
| F03 (dys) | 73 | 17.4 | 32% | **0.80** (duration) | 0.24 |
| F04 (dys) | 18 | **3.4** | 74% | 0.49 | **0.66** (loudness) |
| FC02 (ctl) | 205 | 40.6 | 19% | 0.12 | 0.15 |
| FC03 (ctl) | 267 | 15.3 | 35% | 0.26 | 0.16 |

**BIG FINDING (win for the I11/F28/F29 mechanism):** the severe-dys wall is **NOT isotropic noise**. Each
dys speaker's within-word scatter is dominated by an **interpretable physical axis** — F03 by *duration*
(|r|=0.80), F04 by *loudness* (|r|=0.66) with a strikingly low effective rank (PR=3.4). Typical speakers
show none of this (|r| ≤ 0.26, higher PR). → there IS a mechanism to exploit: **F29 query-side rate/gain
normalization should compress these axes and lift dys D2** (a falsifiable prediction A4 hands to F29), and
F28 per-variant enrollment is motivated.

**Honest caveat on the gate:** the pre-registered `top3≥55% AND |r|≥0.35` gate *technically fails* (dys mean
top3 = 53%, script printed "ISOTROPIC"). That is a **poorly designed operationalization** on my part — the
top-3-variance clause rewards low-rank-ness but penalizes the interpretable-but-spread F03 case (duration
axis 0.80 yet top3 only 32%). The interpretable-axis clause (|r|≥0.35) passes decisively for BOTH dys
speakers. Per EVAL-003 I record the gate as-written failed, and let F29's actual FRR delta be the real
adjudicator rather than move the goalpost. F04's n=18 is small (weight F03's duration result more).

**➡️ ADJUDICATED by F29 (below): the duration axis is a symptom, NOT a lever.** A4 predicted rate
normalization would compress the axis and help; F29 *refuted* it (dys AUC 0.68→0.45). So A4's correct final
reading is: "the scatter is structured/interpretable, but that structure is not actionable via the obvious
normalization" — the honest, chain-completed conclusion.

---

