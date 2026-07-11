# SOTA toward 900 — the honest population split: typical at the 900 doorstep, dysarthric voice-only walled

**Date:** 2026-07-11 · **Journey:** "continue towards SOTA 900" · **User decision:** report the composite
as an explicit **population split** (typical vs dysarthric), not a single laundered number.
**Corpora:** GSC-24 (typical, robust word-repeat corpus, n≈19) + TORGO (dysarthric moderate/severe, n=8).
**Binding metric (EVAL-007):** D2 = FRR @ FAR≤5%, held-out global threshold (leave-one-fold-out),
FAR-matched (realized held-out FAR printed on every verdict).

> **Headline.** The two populations are on opposite sides of a real line, and this session moved the
> typical picture. **Typical:** on the robust GSC-19 corpus, D2 is at the **top edge of band 800** —
> K5/L12 = **5.6% FRR @ FAR 4.2%**, AUC 0.988, a monotone few-shot curve that **plateaus at ~5%** (K6=5.2,
> K7=5.0) gated by a 2–3-speaker hard tail. It does **not** clear band 900 by few-shot alone, but it is
> genuinely **un-walled** — and it is far better than the fragile TORGO-n3 13.8% that had made D2 look like
> the worst typical domain. Net: **typical D2 is still band 800, but now sits at the 800 floor _tied_ with
> D5-reverb (81.4%) and D3-ambient (carried), instead of being the single worst domain.** Composite-900
> needs **all three** at 900 — and D5/D3 were only measured on the same **TORGO-n3** basis that inflated
> D2's old 13.8%, so they are **candidate** co-blockers pending robust-corpus re-measurement, not confirmed
> ones (deferred here under host load). **Dysarthric:** voice-only D2 is a **confirmed information-theoretic wall** — 12 dead levers
> across Rounds 4–5, AUC ~0.65, encoder/matcher/score-map invariant. The dysarthric route to a usable
> product is **not a scorecard-900**; it is Tier-A reframe + Tier-E modality (documented as the ship route,
> explicitly NOT banked as composite-900 — the fallback modality's reliability is not a SpeechAngel
> voice-recognition capability).

---

## 1. Typical population — the un-walled front (experimental track)

### 1.1 Where typical D2 sits (the binding domain at 800)

Few-shot enrollment is the one robustly-replicated lever (A1/A5). Extending it at the best layer (L12,
per the a5 layer sweep) on GSC-19, held-out global threshold @FAR≤5%:

| K (reps) | FRR | realized FAR | AUC | band | source |
|--:|--:|--:|--:|:--:|---|
| 1 | 23.1% | 4.5% | 0.943 | 700 | T2 (enriched neg) |
| 2 | 15.4% | 3.7% | 0.959 | 700 | T2 |
| 3 | 11.3% | 4.0% | 0.972 | 800 | T2 |
| 4 | 7.5% | 4.0% | 0.984 | 800 | T2 |
| 5 | **5.6%** | **4.2%** | 0.988 | **800** | T2 |
| 6 | _[T3]_ | | | | T3 |
| 7 | _[T3]_ | | | | T3 |

- **Monotone, still dropping** (K4→K5 = −1.9pp) — the opposite of the dysarthric K-curve (flat, memory
  [[sota-d2-round5-30exp]] #22). Typical D2 is enrollment-sparsity-limited, not variability-walled.
- **AUC 0.988 at K5** — the genuine/impostor geometry is separable (cf. dysarthric AUC ~0.65).
- **The residual is a 3-speaker tail:** per-speaker K5 FRR is 0–6% for 16/19 speakers; three hard
  speakers (19%, 19%, 31%) carry the 5.6% aggregate.
- **FAR headroom recovered honestly (T2):** enriching the negative-calibration pool 32→89 samples/speaker
  (deployment calibrates the threshold on a large negative corpus, not ~25 samples) moved realized FAR
  3.8→4.2% and FRR 5.8→5.6% — a protocol fix, not a test-mined lever.

### 1.2 T3 — does the curve cross band 900 (≤5%) at a deployable rep count? **No — it plateaus AT ~5%.**

Extending the fixed-8-command curve to K6/K7 on the 9 GSC speakers with ≥8 same-speaker reps
(enriched neg, L12, realized FAR 3.2–3.9% throughout):

| K | 4 | 5 | 6 | 7 |
|--:|--:|--:|--:|--:|
| FRR | 9.2% | 6.8% | **5.2%** | **5.0%** |
| per-K Δ | — | −2.4 | −1.6 | **−0.2** |

- **The curve flattens at ~5%** (K6→K7 = −0.2pp) — few-shot does **not** plunge below the band-900
  line; it asymptotes right at it. Monotone but plateaued.
- **The plateau is a 2-speaker tail:** per-speaker K7 FRR = `22 3 3 12 2 0 2 0 2` — two hard speakers
  (22%, 12%) carry the entire residual; the other seven are ≤3%.
- **This n=9 subset is the harder speakers** (they qualified by rep count, not by ease): its K5 = 6.8%
  vs the full GSC-19 K5 = 5.6% (T2). So the population number is the T2 5.6%, and the *shape* here shows
  reps hit diminishing returns before clearing 5%.

**The threshold is already per-speaker.** `held_out_frr_far` fits the @FAR≤5% accept threshold on each
speaker's *own* held-out folds (the correct deployment model — each user's threshold is calibrated on
their own enrollment). So the 2 hard speakers' 12–22% FRR is **not** a global-calibration/T-norm artifact
— it is genuine within-speaker genuine/impostor overlap at their own optimal operating point. A
per-speaker calibration lever is therefore already in play and does not rescue them.

**Verdict (adjudicated on FRR@matched-FAR, EVAL-007):** typical D2 sits at the **top edge of band 800
(~5.0–5.6% FRR @ FAR ≤4.2%)** and **does NOT clear band 900 by few-shot alone** — the residual is a
genuinely-hard-speaker tail (2–3 of 19) that survives both more reps (plateau K6→K7 = −0.2pp) and
per-speaker thresholding. This is still categorically **un-walled** (AUC 0.988, steep K-dependence,
16/19 speakers ≤3%) — unlike the dysarthric information-theoretic wall — but **band-900-typical is not
reached this session**; closing it needs better representation for the hard-voice tail (a mild,
localized analogue of the dysarthric variability problem), not a cheap calibration fix. Honest typical-D2
band = **800 (upper edge).**

### 1.3 Typical composite (per-domain) — D2 improves to the 800 floor; D5/D3 are *candidate* co-blockers

Carried from the committed 2026-07-10 typical composite (wavlm-large L15, few-shot + multi-condition
enrollment; `2026-07-10_ssl-ceiling-and-d2-wall.md` §RESOLUTION). **Not re-run this session** — host was
under heavy load from unrelated work, and the D1/D4/D5/D6 encoder+condition config is unchanged; only D2
was re-measured (on a better corpus).

| Domain | TYPICAL (control) | band | note |
|---|---:|:--:|---|
| D1 rank-1 (clean) | 89.9% | 900 | |
| **D2 FRR@FAR≤5%** | **~5.6% (GSC-19)** / 13.8% (TORGO-n3) | **800 (upper edge)** | **↑ this session — see below** |
| D4 noise @20 dB | 88.5% | 900 | |
| D5 reverb rt60≈250 ms | **81.4%** | **800** | needs ≥85% for 900 (already has reverb-aug enroll) |
| D6 bandwidth 300–3400 Hz | 86.9% | 900 | |
| D3 ambient FA/hr | ~800 (carried) | **800** | known-weak axis; needs real ambient re-validation |
| D13 enrollment efficiency | ~950 (carried) | 950 | |
| **Composite (min)** | | **800** | gated by D2/D5/D3 |

**The key reframe this session:** the committed typical-D2 was **13.8% on TORGO-control (n=3)** — a fragile
number that made D2 look like the single worst typical domain. On the **robust GSC-19 word-repeat corpus**
typical D2 is **~5.6% (K5), plateauing at ~5%** — i.e. at the **top edge of band 800.** So D2 is **no longer
the single worst domain**, but it is **still band 800**, now sitting at the 800 floor **tied with D5-reverb
(81.4%) and D3-ambient (carried 800)**. Reaching composite-900 requires **all three** to cross to 900.

**Cross-corpus caveat (EVAL-004 — don't launder the ranking):** D2 above is GSC-19 (n=19, L12); D5/D1/D4/D6
are TORGO-control (n=3, L15); D3 is carried from a separate dual-cascade path. We cannot distrust TORGO-n3
for D2's old 13.8% and simultaneously trust TORGO-n3 for D5=81.4% to crown it "the" blocker. So **D5-reverb
and D3-ambient are _candidate_ co-blockers pending robust-corpus re-measurement**, not confirmed ones. Both
are plausibly un-walled channel-robustness problems (not information-theoretic), which makes them the honest
next levers (§5) — but the ranking is provisional until they are re-measured on GSC-scale data (deferred
here only to avoid re-running the heavy encoder under host load).

---

## 2. Dysarthric population — the confirmed voice-only wall (banked negative)

This half is **not a new result** — it is the banked verdict of Rounds 4–5, restated here as the
population-split's lower half. **The negative is bankable now on the TORGO data in hand; UASpeech (#24)
gates the positives, not the negative.**

- **Voice-only moderate/severe D2 is information-theoretic.** 12 dead tail-direct levers across Rounds 4–5
  (Round-4 P1/P2/P3/N1; Round-5 #6 maha −9.5 / knn −0.1, #8 fusion −3.4, #9 QMF −8.0, #10 per-confusor
  FAR-invalid, #12 duration −26.5, #7 scatter-gate non-predictive, #13/#14 refuted). Unbiased AUC ~0.65
  everywhere, monotone-invariant to score maps; representation axis prior-closed (frame-DTW lowers
  separability). Root cause = severe within-word acoustic variability (genuine repeats ≈ as far apart as
  different words). See `2026-07-11_d2-wall-30-experiment-program.md`.
- **K-curve is flat for moderate** (65→63% for K=1→4) — more enrollment reps do NOT help; do not burden
  dysarthric users. (Contrast §1: typical is steeply K-dependent.)
- **The honest product route (NOT a scorecard-900):** Tier-A reframe (SPRT k=2 / confirm+retry) lifts
  moderate single-shot task-success 33–37% → **~65–73%** at ~2.3 turns / decision-FAR ≤5% (optimistic
  upper bound — independent-retry assumption, teacher embeddings, pooled threshold), short of the 85%
  shippable bar; the residual is the rejection tail. **Tier-E** (confidence-gated voice fast-path on the
  ~16% high-confidence turns + a reliable switch/dwell/gaze fallback) is what makes the *product* usable —
  but a ~97%-reliable fallback's task-success is attributable to the **fallback modality, not to
  SpeechAngel's voice recognition**, which the composite bands. So Tier-E ships an AAC system despite the
  wall; it is not a voice-quality 900.
- **Banking the positives needs a graded cohort:** the +5.4pp vocab co-design (held-out, cross-speaker,
  sub-8pp) and the Tier-A operating points are **NOT-BANKED pending UASpeech (#24)** — see
  `docs/plans/2026-07/uaspeech-acquisition.md` (user-initiated).

---

## 3. The population-split scorecard (the deliverable)

| Population | Composite | Binding domain(s) | Status |
|---|:--:|---|---|
| **Typical** | **800** | three-way tie at the 800 floor: **D2 ~5.6% (GSC-19), D5-reverb 81.4% (n=3), D3-ambient (carried)** | **un-walled**; this session cut D2 from a fragile n=3 13.8% to a robust ~5.6% (no longer the single worst), but all three must reach 900 for composite-900; D5/D3 are *candidate* blockers pending robust re-measurement |
| **Dysarthric (moderate/severe)** | **~600** | D2 within-word variability | **voice-only wall confirmed (information-theoretic)**; product = Tier-A+E |

**Honesty contract.** The split is reported because the user authorized it (define-the-win). Neither
number is laundered: the dysarthric wall is not dodged by re-scoping the population, and the typical
number is not inflated by the modality fallback. The typical claim is at the wavlm-large ceiling encoder
(deployable behind the VAD gate on a 2026 phone, [[constraint-validity-check]]); INT8 student ≈ 1–2pp.

## 4. Method integrity

- **FAR-matched** on every verdict (realized held-out FAR printed); the FAR headroom was recovered by a
  *protocol* fix (bigger negative set), not by test-mining a threshold.
- **Robust corpus for the typical claim** — GSC-19 (real same-speaker word repeats), not TORGO n=3.
- **Vocab held fixed at 8 commands** across the T3 K-curve so the only variable is K (no vocab-size
  confound).
- **Adjudicated on FRR@FAR, AUC diagnostic only** (EVAL-007).
- **NOT-BANKED** — the typical band-900 read (if T3 crosses) still needs a fresh pre-registered
  confirmation on an independent typical cohort; the dysarthric positives need UASpeech.

## 5. Next levers (hypotheses, not results)

1. **Re-measure D5-reverb and D3-ambient on the robust corpus first (removes the cross-corpus confound).**
   They are the *candidate* typical 800→900 co-blockers (D5 81.4% on n=3; D3 carried), but until they are
   measured on GSC-scale data like D2 was, the ranking is provisional. If they confirm at band 800, typical
   800→900 is a **channel-robustness** problem (un-walled): lever for D5 = stronger/real-RIR multi-condition
   enrollment (current reverb-aug already gives 81.4%); for D3 = a real ≥6 h ambient recording to replace
   the carried proxy. Re-run under normal host load (deferred this session to avoid instability).
2. **Typical D2 tail (lower priority — D2 is off the binding path):** the 2–3 hard GSC speakers survive
   more reps AND per-speaker thresholding, so the residual is genuine hard-voice within-word overlap — a
   mild, localized analogue of the dysarthric problem. Not worth chasing until D5/D3 clear 900.
3. **Dysarthric:** acquire UASpeech (#24, `docs/plans/2026-07/uaspeech-acquisition.md`) to bank the
   Tier-A/vocab positives on a graded cohort and measure the real retry-correlation; Tier-E needs a real
   switch/dwell/gaze stream to test late fusion.
