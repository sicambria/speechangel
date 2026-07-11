# Typical D2 → 900: the layer route is closed (measured negative) — but D2 is *not* walled

**Date:** 2026-07-11 · **Journey:** "toward SOTA 900 — close typical D2's hard-voice tail" (the next
lever hypothesis banked at the end of the D5/D3 confound-resolution journey). · **Corpus:** GSC-19
(typical, robust word-repeat; wavlm-large, all-layers cache). · **Binding metric (EVAL-007):** D2 =
FRR @ FAR≤5%, held-out global threshold (LOFO), FAR-matched (realized held-out FAR printed).

> **Headline.** With D5/D3 off the floor, the typical composite is band **800, gated by D2 alone**. The
> stated next lever was *"better representation for the 2–3 hard-voice speakers."* This journey ran the
> **cheapest representation axis first — layer selection** — because the all-layers wavlm-large cache was
> already on disk (no re-encode). The result is a **measured negative: no deployable wavlm-large layer
> lever clears band 900.** The best single layer (L12) is 5.81%; a **held-out per-speaker layer
> selection lands at 6.80% — *worse* than the single-layer baseline**; mean-cosine fusion is 5.59–6.14%.
> An *oracle* per-speaker-best-layer reaches 4.06% (band 900) but that is **selection-on-test noise** — it
> harvests isolated FRR dips over ~15 layers on 48 test-queries/speaker, and the honest held-out version
> reverses it. **Scope, precisely:** this closes the **layer axis**, not typical D2. Typical D2 has **AUC
> 0.988** and a genuinely-hard (clean-audio) 2–3-speaker tail; only *one* representation axis is closed
> here — this is **not** an information-theoretic wall (contrast the dysarthric D2, earned over 12 dead
> levers across representation + matcher + score + calibration).

---

## 1. Definition of the win (pre-registered)

- **Baseline (fidelity-anchored):** typical D2 = **5.81% FRR @ FAR 3.9%** at the deploy layer **L12**,
  K=5 few-shot, GSC-19, **npos = 912** (19 spk × 8 words × 6 reps). Reproduces `t1`/`t6` to the decimal
  (EVAL-004 gate — see §5). *(The population-split doc's 5.6% is the enriched-negative T2 variant; the
  un-enriched a5 code path used throughout this journey is 5.81%.)*
- **Band 900 cutoff — verified from the Kotlin source of truth**, not inferred: `DomainBands.kt` spec 2
  `FRR @ FAR≤5%` → `900 to 0.05` (950 = ≤0.02, 1000 = ≤0.005). So **band 900 = FRR ≤ 5% = ≤ 45.6 of 912
  false rejects**; the current 51 FR must drop to ≤45 — **a ~6-flip gap.**
- **Why an aggregate line-cross is NOT the win (EVAL-005):** those ~6 flips are carried by a **2–3
  speaker hard tail** (per-speaker FRR 12–31%). A metric moved by ~6 of 912 events, concentrated in 2–3
  speakers, is a curve-extreme knife-edge. **Pre-registered win = a lever robustly helps the hard
  speakers, with ≥2 of them improving in direction at matched FAR** — not the aggregate crossing ≤5%.

## 2. The discriminating diagnostic — per-speaker × per-layer FRR map (`t6`, free from cache)

Before committing any lever, the advisor-prescribed free experiment: is the tail hard at *every* layer
(intrinsic → bank the negative) or only at L12/L15 (layer selection becomes a mechanism-backed lever)?

| Finding | Result |
|---|---|
| **Best single deployable layer** @K5 | **L12 = 5.81%** — the aggregate FRR is bowl-shaped (L6=8.9%, L11–12≈6%, L24=9.0%); **no other single layer beats L12.** Single-layer selection is closed. |
| **The 2 hardest speakers** | walled at **every** layer: `98ea0818` never below **23%** across all 19 layers; `2aca1e72` flat **19–29%** everywhere. No layer rescues them. |
| **Oracle** per-speaker-best-layer | **4.06% (band 900)** — but this is min-over-19-layers on 48 test queries/speaker; it harvests isolated dips (e.g. `c1d39ce8` 12% at **L24**, the globally-*worst* layer where the aggregate is 9%). **Selection-on-test.** |

**Read:** the tail is *partly* intrinsic (2 speakers no layer rescues) and *partly* layer-heterogeneous
(different speakers peak at different layers). The oracle band-900 is a mirage unless a **deployable**
(held-out) mechanism can capture it. §3 measures whether it can.

## 3. The measured negative (`t7`, all from cache, FAR-matched)

| Lever | FRR @ FAR≤5% | Realized FAR | Band | Verdict |
|---|--:|--:|:--:|---|
| L12 single-layer (**baseline**) | 5.81% | 3.9% | 800 | best single layer |
| **Deployable per-speaker layer** (held-out; layer picked on **train** folds by genuine/impostor d′) | **6.80%** | 3.4% | **800** | **WORSE than baseline — the deployable number** |
| Fusion, mean-cosine mid-band L9–16 | 5.59% | 3.7% | 800 | NOT-banked directional (~2 flips, never crosses ≤5%) |
| Fusion, mean-cosine all L6–24 | 6.14% | 3.4% | 800 | worse (blends → drags single-peak speakers down) |
| Full oracle per-speaker-best-layer | 4.06% | — | *900* | selection-on-test |
| De-noised oracle (excl. 4 globally-worst layers) | 4.50% | — | *900* | **still** selection-on-test (see §4) |

- **The load-bearing number is the deployable 6.80%.** Held-out per-speaker layer selection (each user
  picks their layer on their own enrollment folds by d′-separation, evaluated on the held-out fold)
  **regresses below the 5.81% single-layer baseline.** The per-speaker layer heterogeneity **does not
  survive held-out selection** — it is the selection-on-test noise the oracle harvested (EVAL-005).
- **Safety of the negative (why 6.80% is trustworthy):** a leakage bug would make held-out selection look
  *better* (inflate the apparent win); it came out **worse**. Realized FAR 3.4% ≤ 5% (no FAR-inflation).
  The L12 = 5.81% fidelity anchor validates the shared scoring primitives. So the regression is real.
- **Fusion blends, it does not select.** Mid-band fusion (5.59%) is ~2 flips under baseline at matched
  FAR but **never crosses ≤5%** — logged as a **NOT-banked directional** (EVAL-003), not a win. All-layer
  fusion (6.14%) is worse: averaging pulls single-peak speakers (e.g. `893705bb`, 10% @L12 but 30%+ at
  L6–L10) toward their mean. Mechanically, mean-of-unit-layer-cosines cannot select a speaker's best
  layer.
- **The tail is genuine hard voice, not a data artifact.** Audio probe of the 4 hardest speakers'
  clips: **0.0% clipping**, −19 to −28 dBFS RMS, 1.0 s, 65–80% voiced — clean recordings. `98ea0818`'s
  50–56% at L6–L8 is real difficulty, not a clipped/noisy file. So D2 is **not** secretly better than
  5.8%.

## 4. Honesty: the de-noised oracle clears 900 — and why that does not reopen the route

A pre-bank advisor forecast predicted the de-noised oracle (per-speaker best layer restricted to the
smooth mid-band, excluding the 4 globally-worst layers) would fall to ~5.4% (band 800), giving an
a-fortiori "even the optimistic bound stays 800." **Measurement refuted that specific claim: the
de-noised oracle is 4.50% (band 900).** The forecast was wrong; it is not load-bearing. The verdict
instead rests on the **deployable** number (§3): even the *test-picked* oracle clears 900 by only ~0.5pp
via noise-harvesting over ~15 layers on 48 queries/speaker, and the **honest held-out selection reverses
it to 6.80%.** So **no selection criterion — d′, or (equivalently, and closed here without a further run)
a train-FRR criterion — reliably clears 900**, because the signal it would select on is per-speaker
sampling noise, not stable per-speaker layer preference. This is EVAL-005 in a new guise: an *oracle over
many candidate layers* is a curve-extreme selection whose apparent lift is the multi-candidate analogue
of "the single nearest sample moves the tail."

## 5. Method integrity

- **EVAL-004 fidelity:** the scoring/threshold primitives (`score_query`, `global_threshold_accept`,
  `held_out_frr_far`) are reused **verbatim** from `cand_lib`; folds/K/min-agg are identical to
  `a5.kcurve_speaker`. `t6`/`t7` at L12/K5 reproduce `t1`'s 5.81% **to the decimal** — the anchor before
  any delta is trusted. Only the analysis (loop over layers, per-speaker breakout, held-out layer pick,
  fusion, audio probe) is new; **no re-encode** (all-layers cache on disk).
- **FAR-matched** on every row (realized held-out FAR printed); the deployable lever's FAR (3.4%) is
  *below* target, so its regression is not a threshold artifact.
- **Adjudicated on FRR@FAR (EVAL-007);** AUC (0.988) is diagnostic only and is what distinguishes this
  from the dysarthric wall (AUC ~0.65).
- **No variant mining (step 11 / EVAL-003):** n has answered the strategic question — the two hardest
  speakers are walled at every layer, so the ≥2-hard-speaker win criterion is unreachable by *any* layer
  lever. Additional layer-selection variants were **not** run; the deployable-vs-oracle contrast already
  closes the route.

## 6. What is banked, what is not, and scope

- **BANKED (measured negative):** typical D2 = band **800** (5.6–5.8% FRR @ FAR≤5%); **the layer route
  is closed** — no deployable wavlm-large layer lever (best-single, held-out per-speaker, or mean-cosine
  fusion) clears band 900. The residual is a **2–3-speaker hard-voice tail** that is **genuine** (clean
  audio) and **hard at every layer**.
- **NOT established — this is NOT a wall.** Typical D2 has **AUC 0.988** and only **one** representation
  axis (layer choice) closed this journey. It is **possibly a milder analogue** of the dysarthric
  within-word tail, but that is a hedged hypothesis, not a banked fact — the dysarthric "wall" was earned
  across 12 dead levers spanning representation + matcher + score + calibration (AUC ~0.65); typical D2
  has none of that evidence.
- **NOT-banked directional:** mid-band mean-cosine fusion 5.59% (~2 flips under baseline, never crosses
  the band) — reportable, not adoptable without a fresh pre-registered FAR-matched confirmation.

## 7. Next levers (hypotheses, not results — a fresh call after this bank)

1. **Open representation axes for typical D2** (untouched here): **pooling** (attentive / self-attentive
   vs mean; frame-level QbE-DTW instead of an utterance embedding), **enrollment augmentation**
   (speed / VTLP / room simulation on the 2–3 hard speakers), a **larger/different encoder**, or a
   **learned tail-verifier**. Each is a distinct axis; the layer axis being closed says nothing about
   them.
2. **C3 — student-fidelity confirm (honesty, not rescue):** the typical-800 numbers are all on the
   **wavlm-large teacher**; the deployable is a ≤150 MB student. Band 800 = ≤15% FRR with ~9pp of
   headroom, so a normal 1–3pp student penalty keeps it 800 — but the shipped number is currently
   **unmeasured on the student.** Measuring the composite on the student *confirms* 800; it is not
   expected to move the band. (N+12 — needs the student artifact.)
3. **Dysarthric positives** remain gated on **UASpeech (#24)** — unchanged.

**Artifacts:** harnesses `t6_perspeaker_layer_map.py`, `t7_layer_negative.py`; evidence
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t6_perspeaker_layer_map.json`,
`scripts/eval/ssl_frontend_spike/_ceiling_cache/t7_layer_negative.json` (measure-only, git-tracked).
Baseline anchor `t1_typical_d2_900.json`. Revises the typical axis of
`docs/testing/2026-07-11_population-split-800-900.md` §5 lever 2 (the layer sub-axis is now closed; the
tail is confirmed genuine).
