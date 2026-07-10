<!-- Innovation report: what algorithmic/methodological changes could push the core-USP composite over
     the 950 band, under the five-constraint admissibility filter. Forward-looking; every projected
     number is labeled PROJECTION (EVAL-003, NOT banked); every proposed experiment is pre-registered
     in §8 (EVAL-003). Scope: core USP only — no production/latency/battery/guardrail domains. -->

# Pushing past the 950 band — innovation report (core USP only)

**Date:** 2026-07-10 · **Owner:** SOTA journey · **Status:** research report (no code change) ·
**corrected + extended 2026-07-10 review pass** (see §14 corrections ledger, §13 candidate experiments)
**Companions:** `docs/product/2026-07-08_sota-domain-bands.md` (band definitions),
`docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md` (the measured walls),
`docs/research/OVERALL.md` (synthesis). Constraint policy: CONSTRAINT-001 (`docs/ai/ACTIVE_DEV_RULES.md`).

**Scope note (per request):** this report covers only the **core USP** — on-device, language-independent,
speaker-dependent, few-shot, arbitrary-word open-set command matching: domains **D1** (rank-1), **D2**
(FRR@FAR), **D3/D7/D8** (always-on rejection), **D9** (deployable encoder), **D10** (language
independence), **D13** (enrollment efficiency), **D14** (vocab scaling), with D4–D6 (channel robustness)
touched only where they are encoder-coupled. D11/D12/D15 and production engineering are out of scope.

---

## 0. Executive summary

1. **On the committed scorecard** (dysarthric TORGO aggregate incl. severe speakers, single-utterance D2)
   a >950 composite is **measured-impossible**: D1-950 needs ≥90% rank-1 (off-device 316 M ceiling: 79.4%)
   and D2-950 needs ≤2% FRR @ FAR≤5% (severe-dysarthric genuine/impostor separability is capped at
   AUC ≈ 0.70 across every admissible representation, matcher, learned verifier, and training regime —
   banked 2026-07-10). No innovation in this report claims otherwise, and none should ever be laundered
   into claiming it.
2. **The honest 950 target** is the population/protocol the product will actually ship to most users:
   **typical + mild/moderate dysarthric speakers, few-shot enrollment, task-level acceptance protocol.**
   On that scorecard, >950 is a live but hard target: current best measured typical composite is **800**
   (off-device base-plus ceiling + multi-condition enrollment), deployable ≤25 MB is **700**
   (distilhubert D2 = 16.7%). Reaching 950 means beating the published reference points by roughly an
   order of magnitude — but note the nearest one is not a clean match: **ZP-KWS** reports 29–33%
   FRR@1%FAR only on its **two friendliest datasets** (78.2% on LibriPhrase-Hard, 49.8% on GSC), at
   **FAR 1%** not the report's FAR 5%, and as a *personalized keyword+speaker* number, **not** the
   speaker-independent baseline §3 contrasts against (§12). The comparison is directional, not
   FAR-matched. Either way, reaching 950 demands innovations the field has not shipped, not parameter tuning.
3. **The strategic thesis** (§3, derived from our own banked measurements): every *frozen-representation*
   lever is measured-capped **for severe-dysarthric D2** (typical D1 still rose 86.8→89.9 this session
   with a larger frozen encoder, and the unbuilt purpose-trained I1 is caught by no measurement), while
   every *per-user data* lever measured so far moved the ROC structurally
   (template count K=1→4 cut typical D2 FRR 46%→11%). The product's unique, unexploited asset is that it
   is **speaker-dependent and always-on**: it owns the user's genuine distribution (K enrollment reps),
   an unlimited stream of user-specific ambient negatives, the user's real acoustic channel, and an
   interactive decision protocol. Published speaker-independent KWS can use none of these. The 950 path
   is: **one remaining representation build (I1) + systematic exploitation of per-user data at the
   decision layer (I2–I6).**
4. Two **owner-level definitional decisions** (§7) gate whether the resulting system can be *scored*
   >950: (a) primary-population scoping, (b) D2 protocol/negative-set re-scope (task-level FRR at ≤2
   attempts; deployment-real negatives). Both are legitimate to decide openly (CONSTRAINT-001 —
   the current forms are partly artifacts of TORGO's shape, not product requirements); neither may be
   decided silently by an eval script.

---

## 1. What 950 requires on the core-USP domains

From `docs/product/2026-07-08_sota-domain-bands.md`, with the current best **measured** value beside it:

| Domain | 950 rung | Best measured today (population) | Gap |
|---|---|---|---|
| D1 rank-1 | ≥90% agg (95/90/85 per severity) | **89.9% typical** (wavlm-large L15 + multi-cond, off-device; base-plus 86.8%); 79.4% dys ceiling; 59.2% shipped MFCC | 0.1 pp typical at ceiling; dysarthric unreachable |
| D2 FRR@FAR≤5% | ≤2% (deploy-slice ≤3%) | 11.1% typical K=4 (in-sample θ, large L14); 13.8% held-out distinct-slice (base L12); 16.7% deployable ≤25 MB; ~40% dys plateau | ~7× reduction needed (typical, from the honest held-out 13.8%); dysarthric unreachable single-shot |
| D3 ambient FA/hr | ≤0.05 + det ≥95% @≤0.5 | ~82 FA/hr (MFCC single-template proxy); dual-cascade banked at the ≤0.5 boundary (WavLM) | ~3 orders of magnitude vs proxy; compound cascade unmeasured e2e |
| D7 wake det @≤0.5 FA/hr | ≥90% | in-regime MFCC proxy, optimistically biased | unmeasured at SSL level |
| D8 cascade rel-FRR | ≥50% rel, F03 ≤15% | 49.5% rel banked (WavLM); F03 25.4% | at the 950 boundary on rel; F03 absolute far |
| D9 deployable encoder | ≥80% dys rank-1, size-capped | distilhubert 68.2% dys / ~80% ctl @23 MB | rung definition needs the ≤25 MB amendment (§7.3) |
| D10 language indep. | Δ≤10 pp, ≥3 languages | NOT MEASURABLE on single-read CV; by-construction argument | needs a corpus with repeated words per language (I1 fixes this) |
| D13 enrollment eff. | ≥90% @ 2 templates | **950 banked** (90.7%) | none |
| D14 vocab @77 cmd | ≥85% | 56.8% MFCC / ~74% base-plus (F03 slice) | encoder-coupled; large gap |

**The separability arithmetic that governs D2.** FRR ≤2% @ FAR ≤5% corresponds to genuine/impostor
AUC ≳ 0.99 (binormal equal-variance approximation — indicative, not an exact derivation; same method as
the banked ROC-floor argument: 800/≤15% ≈ 0.97 — corrected from 0.93, which was the EER=15% value, not
FRR=15%@FAR=5%; see the wall-doc ROC-floor correction note). Measured
single-pair AUC: severe dysarthric **0.70** (invariant), control **0.83** (frozen wavlm). Neither
population's *single-pair, single-template* separability is within reach of 0.99 — which is exactly why
§3 argues the remaining headroom is at the **decision layer**, where effective AUC is a function of
single-pair AUC × per-user data volume (K templates, negative count, attempts), not representation alone.

---

## 2. Where the measured frontier is (what binds today)

Condensed from `docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md` — all banked:

- **Representation is capped.** MFCC 59.2 → distilhubert 68.2 → base-plus 71.9 → wavlm-large 79.4%
  dysarthric rank-1; dysarthric D2 AUC 0.67→0.70 across a 13× parameter jump. Learned projections
  (control-trained, LOSO in-domain), frame-DTW, and a nonlinear pairwise verifier all confirm the cap.
- **The one structural D2 lever found is per-user data volume:** template count. Typical FRR@FAR≤5%:
  K=1 46.2% → K=2 30.1% → K=3 15.4% → K=4 **11.1%** (band 800). Dysarthric plateaus ~40% by K=3.
  **Confound to resolve before §3's projections rest on this (candidate A1):** the curve is measured on
  "words with ≥K+1 reps," so the *word population shifts* as K grows (K=4 is only words with ≥5 reps).
  Part of the 46→11% drop may be word-selection, not template count — a **fixed-subset** re-run (the
  same words at every K) must confirm the lever's magnitude first. This curve is the single most
  load-bearing input to the whole decision-layer thesis.
- **Channel-matched enrollment works:** multi-condition enrollment lifted the typical composite run
  D1 84.3→86.8, D5 74.2→77.4, D6 80.0→82.2 (banked in the typical-composite spike logs).
- **Deployability is one build away for typical-700, further for 800+:** distilhubert (≤25 MB,
  user-authorized budget 2026-07-10) lands typical D2 = 16.7% (700); wavlm-base-class quality (D2 11%)
  would need ~90 MB INT8 — or a **purpose-trained** small model (I1), which no measurement caps.
- **Dysarthric severe is disorder-capped**, not encoder-capped: F04 (mild) reaches 20–46% D2;
  F01/F03 (severe) set the ~0.70 AUC aggregate. Population heterogeneity is real and product-relevant.
- **wavlm-large L15 typical-composite run (completed 2026-07-10, `_typical3.log`):** typical D1 **89.9%**
  (0.1 pp under the 950 rung), D4 88.5% (900), D5 81.4% (800), D6 86.9% (900) → typical composite 800,
  blocked at 950 by D2 and D5. Dysarthric at the same ceiling: D1 79.0% (800), D4 75.3% (800), D5 63.3%,
  D6 72.7% — encoder-dependent domains lift, D2/D5 still bind. Off-device ceiling evidence that typical
  D1-950 is within reach of a purpose-trained encoder; the deployable student must close a ~3–18 pp
  retention gap on top.
- **D2 operating-point mismatch to reconcile before scoring against the rung (candidate A3):** every
  banked D2 number here uses **FAR ≤5% per impostor trial** on TORGO in-vocab negatives, but the bands
  doc defines the D2 *rung* as FRR at **≤5 false accepts per hour** of ambient audio. These are different
  operating points on different negative distributions (5%/trial at ~1 window/2 s ≈ ~90 FA/hr). A
  windows/hour bridge measurement on real ambient is required before a banked FAR% can be read against
  the FA/hr rung — otherwise the D2 band claims are not comparable to the rung they are scored against.

---

## 3. Strategic thesis: representation is capped — personal data is not

Every published constraint-matched system is **speaker-independent**: it must decide from one query and
a fixed model. SpeechAngel's USP inverts this — the system is *speaker-dependent by design* and
*always-on by design*. That grants four data assets no published baseline exploits, and our own
measurements show the one we tried (K templates) is the only lever that ever moved D2 structurally:

| Per-user asset | Mechanism it feeds | Status |
|---|---|---|
| K genuine reps per command | genuine-distribution modeling (min-over-K → distribution scoring, I3) | K-curve banked; distribution scoring unmeasured |
| Unlimited ambient audio on the user's device | per-user negative mining → valid per-command calibration + conformal FAR control (I2) | unmeasured — fixes the *measured* failure mode of per-command calibration (sparse negatives) |
| The user's real channel/environment | in-situ + multi-condition enrollment (I6) | multi-condition banked (+2–8 pp); in-situ unmeasured |
| Interactive protocol | margin-gated retry → task-level FRR compounds per attempt (I5) | unmeasured; three-zone hysteresis already built |

**Why this can cross thresholds a 0.83 single-pair AUC cannot:** decision-level effective AUC rises with
every independent draw the decision aggregates. K=4 min-over-K already turned a 0.83-AUC representation
into an 11%-FRR@5%-FAR operating point (effective decision-level separability ≈ 0.98, binormal
approximation). Adding
independent information on the impostor side (real per-user negatives instead of a guessed global
threshold) and on the protocol side (a second genuine draw on low-margin rejects) attacks the same
tail again. None of it touches the five constraints: everything stays on-device, deterministic,
language-independent, few-shot, speaker-dependent.

---

## 4. Innovation portfolio

Ranked tiers. Every "expected" number is a **PROJECTION (EVAL-003, NOT banked)** with the experiment
that would bank it named in §8.

### Tier 1 — evidence-backed, admissible, unbuilt (run these)

**I1 — Purpose-trained multilingual word-discrimination encoder at ≤25 MB (the linchpin build).**
All three distillation attempts to date were *feature-copy* distillation from 6 k English LibriSpeech
windows — the weakest possible training signal for this task. The right build optimizes **exactly D2's
axis** (same-word vs different-word separability) with an episodic/metric objective:
- **Data:** MSWC — the Multilingual Spoken Words Corpus (MLCommons; ~340 k keywords, ~23 M one-second
  clips, 50 languages, **CC-BY-4.0** → passes the licensing constraint). Verify license + per-language
  word-repetition shape at download time. Supplement: cached Common Voice windows with wavlm-large L14
  teacher recompute.
- **Objective:** prototypical-episode / GE2E-style loss over word classes (episodes = few-shot
  enrollment simulations, K=1..5 supports — training matches the deployment protocol), plus distillation
  from wavlm-large L14 as an auxiliary target and SpecAugment/noise/RIR augmentation with teacher
  recompute.
- **Architecture:** small conv/BC-ResNet-class or distil-transformer student; the KWS literature's best
  small backbones are well under 25 MB (BC-ResNet ≈0.3 M params; multilingual embedding models ≈11 M),
  so the budget is generous — quality, not size, is the open question.
- **Why it is not capped by any measurement:** the banked "hard wall" scope-note explicitly excludes
  purpose-trained QbE embeddings trained at scale; the failed in-session attempts establish only that
  6 k-window feature-copying is insufficient.
- **What it unlocks beyond D1/D2:** the first **empirical D10 banding** — MSWC has repeated words per
  language by construction, so per-language rank-1/D2 deltas become measurable (950 rung: Δ≤10 pp over
  ≥3 languages), converting the by-construction argument into a measured claim. Also lifts D14 (vocab
  scaling is embedding-quality-coupled) and D4–D6 (SSL features degrade more gracefully; banked).
- **Expected (PROJECTION):** typical D1 → high-80s–90%; typical D2 (K=4, held-out) 13.8% → 6–10%;
  dysarthric D1 68→72–76% deployable. Multi-session build (GPU training + data pipeline).

**I2 — Passive per-user negative mining + conformal per-command calibration.**
The *measured* failure of per-command calibration (A2: FRR 39–49% but FAR blows to 22–27%) was a
sparse-negatives failure, not a concept failure — thresholds were fit on a handful of TORGO singleton
words. The shipped product has the opposite regime: the always-on Stage-1 gate hears **hours of the
user's real ambient audio daily**. Innovation: continuously bank embeddings (never audio) of ambient
windows on-device as a per-user negative pool; set per-command thresholds by **split-conformal
calibration** on that pool — a distribution-free, finite-sample **FAR guarantee** per command in the
user's actual acoustic environment. Fully on-device, privacy-preserving, deterministic.
- **Validity conditions (the guarantee holds only if these do — X4 must check them, not assume them):**
  (a) *exchangeability* — adjacent ambient windows are strongly autocorrelated, so the pool must be
  block-/time-spaced subsampled, never frame-adjacent, or the finite-sample coverage is void;
  (b) *contamination* — the pool will capture the user's own command utterances, so windows within ±N s
  of an accepted wake must be excluded or they poison the negative set toward accepting real commands;
  (c) *drift* — coverage holds only for the calibration period's distribution, so day-to-day environment
  change forces recalibration. These make I2 admissible-but-conditional, not a free guarantee.
- Fixes D2's per-command arm validity; personalizes D3's operating point (the FA/hr budget is enforced
  against the user's real environment, not LibriSpeech).
- **Expected (PROJECTION):** recovers a large share of the A2 arm's 10–17 pp FRR gain *at valid FAR*;
  typical D2 6–10% → 3–6% combined with I1. Cheap to simulate now (X4).

**I3 — Within-command distribution scoring (PLDA / WCCN over the K enrollment reps).**
Min-over-K discards K−1 of the enrollment information. With K=3–5 reps the system can estimate each
command's *within-class scatter* and score queries generatively (PLDA-style likelihood ratio, or at
minimum within-class-covariance normalization + z-scored distance). This is the speaker-verification
field's standard answer to exactly our problem — high within-class variability — and it has **never been
measured here** (the failed MLP verifier is a discriminative small-sample method; PLDA's generative
small-sample behavior is the opposite regime). Train the global within/between word scatter priors on
MSWC/control data offline; per-user statistics come from enrollment. Ships frozen, deterministic, tiny.
- **Expected (PROJECTION):** +0.02–0.05 effective AUC for typical (meaningful at the 950 margin);
  for severe dysarthric the within-class scatter is the disorder itself — expect proper normalization,
  not a wall-break. Cheap: runs on cached embeddings today (X2).

**I4 — Compound two-stage FA budgeting (the D3-950 path).**
D3-950 (≤0.05 FA/hr) looks unreachable for any single detector — but the architecture is already a
**product of two gates** (WakeWordGate × Recognizer), and false accepts multiply: a wake stage at
~1 FA/hr followed by a command matcher at conditional FAR ~5% yields ~0.05 FA/hr *compound* — exactly
the 950 rung — while FRR compounds only additively at high per-stage detection. The dual-cascade
(banked, 900) and multi-frame persistence (built) stack on top. What is missing is not architecture but
**one end-to-end measurement on ≥6 h of real ambient household audio** (the bands doc's own G-REALAMB
requirement) with the SSL encoder in both stages.
- **Expected (PROJECTION):** ≤0.1–0.05 FA/hr at wake-det ≥85–95% for typical speakers; the decisive
  unknowns are (a) detection retention through two gates and (b) **FA-side stage independence** — the ~5%
  is a *marginal* command FAR, but windows surviving the wake gate are adversarially pre-selected (they
  already resemble the wake) and both stages share the encoder, so the command stage's *conditional* FAR
  on survivors can exceed 5% and the ×0.05 multiply is optimistic. X5 must measure conditional-on-survivor
  FAR, not multiply marginals (candidate D24).

**I5 — Margin-gated single retry: task-level FRR (owner protocol decision, §7.2).**
The three-zone hysteresis (built, unmeasured at system level) makes rejects near the threshold trigger a
deterministic "say it again" rather than a hard reject. A second utterance is a **fresh draw from the
genuine distribution** — the same statistical event that makes the K-curve work, applied at decision
time. **But a second attempt is also a fresh *impostor* draw**, so the retry's FRR gain must be read at
**task-level FAR** (score both sides at the two-attempt operating point) or the win is partly FAR
inflation (X3 gate). If attempt outcomes were independent, typical D2 13.8% → ~1.9% at two attempts (950 territory);
dysarthric plateau 40% → ~16%. They are not independent — the *measurable* quantity is
P(reject₂ | reject₁), which TORGO's repeated words support directly (X3). Notably, the dysarthric
K-plateau's cause (each new token lands far from all K templates — i.e., tokens are broadly scattered)
is itself weak evidence that consecutive attempts are *less* correlated than for typical speech.
- This is the **single highest-leverage lever for the dysarthric population's real experience**, even
  though the committed single-utterance D2 metric cannot see it. Scoring it requires the §7.2 protocol
  re-scope — an owner decision, flagged, never silently taken.

**I6 — In-situ, multi-condition, variability-matched enrollment.**
Multi-condition enrollment is already banked (+2–8 pp on D1/D5/D6 typical). Extensions, all admissible:
(a) **in-situ enrollment** — enroll through the user's own phone/room/distance (the deployment channel
is the enrollment channel by construction; TORGO cannot measure this, a small self-recorded corpus can);
(b) **variability-matched augmentation** — jitter enrollment templates by pitch/rate/noise scaled to the
*user's own measured within-word variance* (AudioAugment has all primitives), expanding the genuine
acceptance region without a blanket FAR cost — must be evaluated at matched FAR;
(c) **enrollment quality gating / adaptive K** — at teach time, measure template self-consistency and
predicted FRR; prompt targeted re-records or extra reps only for inconsistent commands (turns the
K-curve into a per-command budget spent where it buys the most). D13 is at 950 with 2 reps, so a
targeted 3rd–5th rep for hard commands costs band-nothing and buys the K-curve's full drop.

### Tier 2 — plausible probes (cheap, honest expected value moderate)

- **I7 — Stability-weighted sub-segment matching (dysarthric).** Frame-DTW over whole utterances is
  banked-no-lift, but severe-dysarthric variability is plausibly segment-localized (stable syllable
  nuclei, unstable clusters). Probe: best-matching-subsequence / per-segment voting with segment weights
  learned from the K enrollment reps' self-alignment stability. If severe-dysarthric AUC moves at all
  (0.70 → ≥0.75) it is the first crack in the wall; expect honestly that it may not.
- **I8 — Prosodic/duration auxiliary channel (severe dysarthric).** Coarse envelope/duration/pitch-contour
  templates may be *more* repeatable for severe speakers than fine spectra. Fuse at the score level at
  matched FAR. Duration-ratio already helps in the dual-cascade — this generalizes that signal.
- **I9 — Query-side test-time augmentation.** Embed 3–5 jittered views of the query, average the
  embedding (variance reduction on the genuine side, cost ~nothing at 25 MB scale). Unmeasured.
- **I10 — Tiny enhancement front-end for the D4/D5 950 rungs.** A ≤1 M-param denoiser (GTCRN/DTLN-class)
  ahead of the encoder, evaluated with enrollment-condition matching so it never hurts clean speech
  (the banked NR-on-clean −4.1 pp mistake stays fixed).

### Tier 3 — research bets (multi-quarter, outcome genuinely unknown)

- **I11 — SAP-scale variability-aware dysarthric metric training.** The banked "more dysarthric data
  does not help D2" verdict rests on LOSO over **two** training speakers — sound for TORGO, silent about
  training on **hundreds** of dysarthric speakers (Speech Accessibility Project, DUA pending). The bet:
  an encoder trained with a *variability-absorption* objective (map a speaker's scattered productions of
  one word to a tight latent, e.g. per-speaker-per-word sub-center losses) on SAP-scale data. The
  disorder physics may still cap it — but this is the only representation regime no measurement has
  touched, and it is the only conceivable route that moves *severe-dysarthric* D2 rather than routing
  around it. Keep expectations bounded: treat AUC 0.70 → 0.80 as success; 0.99 is not on any roadmap.

---

## 5. Measured dead ends — do not re-spend here

All banked 2026-07-10 (`docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md`):
bigger **frozen** encoders (0.67→0.70 dys AUC for 95 M→316 M); front-end swap under DTW (ties MFCC);
frame-level DTW over SSL features (AUC 0.672, no lift); cosine vs Euclidean local distance (worse);
T-norm with an external/control cohort (86.5% FRR — cohort mismatch; note I2 is *not* this: its cohort
is the user's own environment); per-command thresholds without dense negatives (FAR 22–27%, invalid);
discriminative MLP pairwise verifier (generalizes worse across folds); naive feature-copy distillation
from small English data (two attempts below MFCC); margin cross-verify beyond the cascade (−0.4 pp).

---

## 6. Composite arithmetic — what lands where (PROJECTION, not banked)

Assuming Tier-1 lands at the midpoint of its projected ranges:

| Scorecard | D1 | D2 | D3 | D4/D5/D6 (channel) | D9/D10/D13/D14 | Composite |
|---|---|---|---|---|---|---|
| **Committed** (dys agg incl. severe, single-utterance) | ≤800 (ceiling 79.4) | 600–700 (plateau ~40) | ≤800–900 | ~800 (D5 dys 63.3) | D10 measurable via I1 | **600–700 — 950 impossible (measured)** |
| **Typical, single-utterance, deployable ≤25 MB** (I1+I2+I3+I6) | 900 | 800→900 (3–6%) | 900–950 (I4) | **D4 900 / D5 800 / D6 900 — measured `_typical3.log`; I1 only *projected* to lift** | D13 950; D14 ~900; D10 900–950 | **~900, min-bound by D5=800 and D14~900 (today's measured floor)** |
| **Typical+mild population, task-level ≤2-attempt D2, deployment-real negatives** (§7 decisions + full Tier 1) | 900–950 | 950 (task-level ~2%) | 950 (compound, real-ambient-verified) | **D5/D6 → ≥950 is PROJECTION only, no §8 gate — the residual wall** | as above | **>950 *only if* D5 and D14 also reach ≥950 (unmeasured) — see note** |

> **Residual-wall note (correction, 2026-07-10 review pass).** An earlier draft's row-3 composite read
> ">950 live target" while omitting the channel domains from the table. The composite is a **MIN**, and
> **D5 (reverb) is measured at 800** (typical rank-1 81.4%, `_typical3.log`) with **D14 at ~900** — so on
> today's numbers the min for rows 2–3 is bounded at ~800–900 by D5/D14, *not* by D2 alone. No experiment
> in §8 is pre-registered to lift D5 or D14 to ≥950; I1 is *projected* to help D4–D6 (SSL degrades more
> gracefully — banked as a direction, **not** a rung), but that projection is unbanked and no gate targets
> the D5-950 rung. **Open author/owner question (do not resolve silently):** does any listed lever credibly
> project D5 *and* D14 to ≥950? If yes, state it as an explicit PROJECTION with a §8 gate; if not, the
> honest row-3 composite is **~900, wall = D5/D14**, and ">950" is aspirational, not "live."

The honest reading: **engineering alone (row 2) credibly buys ~900.** The step from 900 to >950 runs
through the §7 definitional decisions *plus* the full portfolio landing *plus* lifting the channel wall —
D5 (reverb, measured 800) and D14 (~900) currently bound the min and have **no §8 gate** targeting 950
(see the residual-wall note). It does not run through D2 alone.

---

## 7. Owner-level decisions this report surfaces (never pulls)

1. **Primary-population scoping (§2, banked heterogeneity).** Mild/moderate dysarthric + typical
   speakers reach the high bands; severe dysarthric is disorder-capped at ~600–700 regardless of
   encoder. A headline composite >950 is only honest if the scorecard names its population — and the
   product should still ship the severe-dysarthric experience (I5/I6 help users the banded metric
   cannot see).
2. **D2 protocol + negative-set re-scope.** (a) Task-level FRR at ≤2 margin-gated attempts as the
   scored metric (single-utterance FRR stays reported alongside); (b) negatives = deployment-real
   (ambient/OOV speech, per-user pool) instead of TORGO in-vocab singletons — the wall doc already
   flags the singleton set as unrepresentatively harsh for a speaker-dependent product. Both change the
   *definition*, so both are owner sign-offs with the old metric kept visible (honesty rule).
3. **D9 rung amendment (mechanical).** The D9 band table still hard-codes ≤2 MB; the user authorized
   ≤25 MB on 2026-07-10 (CONSTRAINT-001 audit: the 2 MB cap had no 2026-device rationale). The bands
   doc needs the param-count column re-based so D9's rungs are scoreable for the I1 artifact.

---

## 8. Pre-registered experiment plan (EVAL-003)

Ordered by information-per-cost. Gates are stated **before** running; any number that survives goes
through fresh FAR-matched confirmation before banking (EVAL-003).

| # | Experiment | Cost | Pre-registered gate |
|---|---|---|---|
| X3 | **Retry-dependence probe**: on TORGO repeats (both populations), P(reject₂ \| reject₁) at the held-out threshold; task-level FRR@FAR curve for ≤2 attempts | hours (cached embeddings) | task-level typical FRR ≤5% AND dysarthric ≤25% **at matched task-level FAR ≤5% (impostors also get attempt 2 — score both sides)** → I5 is real; else drop retry from the 950 path |
| X2 | **PLDA/WCCN scoring** on cached wavlm embeddings, K=3–5, both populations, held-out θ | ~1 day | typical held-out D2 ≤11% (beats min-over-K 13.8%) at valid FAR → adopt; dys AUC reported, no gate |
| X4 | **Passive-negative conformal calibration sim**: per-"user" negative pools from LibriSpeech/ambient streams; per-command conformal θ; held-out FRR + realized FAR validity | ~1–2 days | per-command arm becomes *valid* (FAR ≤5% held-out) with FRR < global-θ arm → I2 is real |
| X5 | **Compound-cascade e2e FA/hr**: record real household ambient; wake×command with dual-cascade + persistence, SSL both stages. **Rule-of-three hours gate:** 0 FA in T h ⇒ 95% upper bound 3/T FA/hr, so ≥6 h banks only ≤0.5 (800); ≤0.1 (900) needs ≥30 FA-free h; ≤0.05 (950) needs ≥60 h | recording-bound (hours-scaled) | with H FA-free hours, bank only the rung whose FA/hr ≥ 3/H — never a rung the observed hours cannot support (6 h ⇒ 800 at most, *not* 900) |
| X1 | **I1 build**: MSWC episodic student ≤25 MB (license + data-shape audit first; then multi-session GPU training) | multi-session | typical D1 ≥85% AND held-out D2 ≤10% AND dys D1 ≥70% deployable; D10: Δ≤10 pp over ≥3 languages |
| X6 | **Sub-segment stability matching** (I7) on dysarthric cached features | ~1–2 days | severe-dys AUC ≥0.75 → first wall-crack, escalate; else bank the negative |
| X7 | wavlm-large typical composite | **DONE 2026-07-10** | typical D1 89.9 / D4 88.5 / D5 81.4 / D6 86.9 → composite 800; ceiling supports typical D1-950 (§2) |

Sequencing rationale: X3/X2/X4 are days-cheap on cached embeddings and de-risk the *decision-layer*
half of the thesis before the expensive X1 build; X5 requires only a recording and closes the biggest
D3 unknown; X1 is the linchpin but should start after its license/data-shape audit passes.

---

## 9. Honesty ledger

- Banked, reproducible inputs: every number in §1–§2 and §5 traces to
  `docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md`, the typical-composite spike logs, or
  `docs/product/2026-07-08_sota-domain-bands.md`.
- **Every forward-looking number in §4/§6 is a PROJECTION (EVAL-003, NOT banked)** — the §8 gates, not
  this report, decide what becomes real.
- The severe-dysarthric wall stands. Nothing here relabels it; §7's decisions re-scope what is *scored*,
  openly, while I5/I6/I11 remain the only levers that touch that population's lived experience.
- **Citations in §10–§12 were cross-validated against ≥2 independent sources each** (three verification
  passes, 2026-07-10; corrections applied inline — e.g. the cascade-KWS venue, LRDWWS venue, EasyCall
  license). Where a source disagreed or only one existed, the entry says so. None is load-bearing for a
  banked claim today; they justify *directions*, not results.
- **A 2026-07-10 review pass** re-derived the ROC arithmetic, cross-checked banked numbers against the
  wall doc/spike logs, and verified every load-bearing external citation against ≥2 primary sources. Its
  15 corrections are logged in **§14** (objective errors fixed inline with visible markers; contingent/
  re-run-dependent findings queued as caveats + §13 candidate experiments, never rewritten as settled).
  The one banked-doc edit (AUC 0.93→0.97) *strengthens* the wall and carries a dated correction note.

---

## 10. Top 100 techniques — decreasing expected value

**How to read this.** Grouped into EV tiers (A→G), roughly decreasing by expected value =
P(it helps) × magnitude × domain-breadth × admissibility ÷ cost. Ordering is by tier, not strictly
monotonic item-to-item — the methodology items (F) and research bets (G) are placed by role, since they
protect or extend the metric rather than move it directly. The first ~15 (tier A) are cheap,
evidence-backed, and testable **today on cached embeddings** — do these first. Every projected effect is a
**PROJECTION (EVAL-003, NOT banked)**; the §8 gates decide. Citation keys `[Author YEAR]` resolve in §12.
"banked" = already measured in this repo.

### A. Per-user decision-layer levers (cheap, cached-testable, highest EV) — the core thesis (§3)

1. **Multi-template min-over-K enrollment, K=4.** The one **banked structural** D2 lever: typical
   FRR@FAR≤5% 46.2%(K1)→11.1%(K4); raises ROC area, not just the operating point. UASpeech shows target
   users can give 5+ reps/word [Kim 2008]. Cost: ~zero. Do first.
2. **Split-conformal per-command thresholds on a per-user negative pool.** Distribution-free,
   finite-sample **FAR guarantee** per command — directly fixes the *measured* A2 failure (FAR blew to
   22–27% because thresholds were fit on a handful of TORGO singletons). On-device, deterministic
   [Vovk 2005; Angelopoulos & Bates 2021]. PROJECTION: recovers much of A2's 10–17 pp FRR *at valid FAR*.
3. **Passive on-device ambient negative mining (store embeddings, never audio).** The always-on gate
   already hears hours of the user's real audio; bank window embeddings as the dense per-user negative
   pool that #2/#6 need. First-principles: the product uniquely owns this stream; no SI baseline can.
4. **PLDA scoring backend over the K reps.** Generative within-/between-word model — the speaker-
   verification field's standard answer to *exactly* our failure mode (high within-class variance), and
   it behaves well with few enrollment samples [Ioffe 2006; Prince & Elder 2007]. Never measured here
   (the banked MLP verifier is discriminative small-sample — opposite regime). Runs on cached embeddings.
5. **WCCN (within-class covariance normalization) + Mahalanobis/cosine.** Lighter than PLDA: whiten the
   per-command intra-token scatter before distance. Standard SV backend; cached-testable.
6. **Adaptive s-norm with a _personal_ cohort.** Cohort = the user's own other-command / ambient
   embeddings. The repo's T-norm failed (86.5% FRR) **because the cohort was mismatched (control vs
   dysarthric)** — a personal cohort is the correct construction [Matejka 2017]. Cached-testable.
7. **Margin-gated single retry → task-level FRR.** A second utterance is a fresh genuine draw; the
   three-zone hysteresis is already built. If attempts were independent, typical 13.8%→~1.9% at 2
   attempts. The measurable quantity is P(reject₂|reject₁) (X3). Highest-leverage for the dysarthric
   population's lived experience even though single-utterance D2 can't see it (owner protocol call, §7.2).
8. **Systematic multi-condition enrollment (clean+noise+reverb+band).** Already **banked** +2–8 pp on
   typical D1/D5/D6 (typical-composite spike). Extend to the full condition set the encoder will face.
9. **DTW Barycenter Averaging to consolidate K reps into one robust prototype** [Petitjean 2011]. Cuts
   match cost/memory vs storing all K. **Caveat:** a barycenter keeps central tendency but *discards* the
   within-command scatter that min-over-K (#1) and PLDA (#4) exploit — so use it only as a prototype
   *alongside* separately-stored scatter stats, never as a replacement for the K reps (a lone barycenter
   would undo lever #1, the thesis's own structural D2 lever).
10. **Query-side test-time augmentation.** Embed 3–5 jittered views of the query, average the embedding
    — variance reduction on the genuine side; near-zero cost at ≤25 MB. Unmeasured.
11. **Enrollment-quality gating / adaptive K per command.** At teach time measure template self-
    consistency + predicted FRR; ask for extra reps only on inconsistent commands. D13 is 950 at 2 reps,
    so targeted 3rd–5th reps cost band-nothing and buy the K-curve's full drop.
12. **Sub-center prototypes per command (K centers, not 1 mean).** Robust to one outlier enrollment token
    [Deng 2020 sub-center principle]. Cached-testable.
13. **Score-level fusion: cosine + duration-ratio + margin (the dual-cascade, generalized).** Banked
    49.5% rel FRR reduction at WavLM [banked; Gruenstein 2017]. Replicate at MFCC and student level.
14. **Per-command DTW band width set from enrollment self-alignment variability.** Already configurable;
    wider for temporally variable commands, tighter for consistent ones. Zero-cost personalization.
15. **Per-command genuine-score normalization by the command's own enrollment self-distance stats.**
    z-scores the query distance against how tightly that specific command's reps cluster. Cached-testable.

### B. The deployable encoder build (I1) and its design choices (high magnitude, higher cost)

16. **Purpose-trained ≤25 MB metric-learning encoder** — the linchpin. Prototypical/GE2E episodes on
    MSWC (340 k keywords, 23.4 M clips, 50 langs, CC-BY 4.0) [Snell 2017; Wan 2018; Mazumder-MSWC 2021].
17. **Episodic training that matches the K=1..5 few-shot deployment protocol** (train the way you test)
    [Snell 2017].
18. **wavlm-large L14/L15 distillation as an auxiliary target** [Hinton 2015]; L14/L15 are the measured
    best layers here.
19. **EfficientNet-B0 (~11 M) backbone** — *proven* few-shot-in-any-language embedding model
    [Mazumder-FSKWS 2021].
20. **BC-ResNet backbone** (BC-ResNet-8 ≈ 321 k params, 98.7% GSC v2) — tiny, strong KWS backbone
    [Kim 2021]. (Note: the 98% belongs to BC-ResNet-8, not the 9.2 k -1 variant.)
21. **Attentive statistics pooling (mean+std, attention) instead of mean-pool** [Okabe 2018].
22. **Acoustic-word-embedding objective (fixed-dim, contrastive).** Neural AWEs *beat* raw-DTW on word
    discrimination and transfer across languages [Settle & Livescu 2016; Kamper 2020].
23. **Multilingual MSWC training → the first _measurable_ D10.** MSWC has repeated words per language by
    construction, so per-language rank-1/Δ become bankable (converts the by-construction argument).
24. **Sub-center AAM-softmax (ArcFace) head over word classes** — angular margin + label-noise robustness
    [Deng 2019; Deng 2020].
25. **SpecAugment during encoder training** [Park 2019].
26. **RIR augmentation (OpenSLR SLR28, Apache-2.0) + MUSAN noise (SLR17, CC-BY-4.0, commercial-OK) with
    teacher recompute.**
27. **PCEN trainable frontend for far-field/noise robustness** (AGC-style dynamic compression, beats
    static log-mel for noisy/far-field KWS) [Wang 2017].
28. **Soft-DTW as a sequence-level alignment loss** for a frame encoder [Cuturi & Blondel 2017].
29. **INT8 quantization-aware training** to hit ≤25 MB with minimal quality loss (distilhubert precedent,
    23.5 M / ~23 MB) [Chang 2022].
30. **Distill from a _combination_ of SSL layers (e.g. L10+L14)**, not one — richer supervisory target.
31. **Temperature-scaled soft-label distillation** on word-class logits [Hinton 2015].
32. **Fixed 256–512-dim embedding + cosine prototypes** — the banked 2×2 proved the lever is a fixed-dim
    QbE embedding, not a front-end swap. Keep dim modest.
33. **LEAF learnable frontend as a log-mel alternative** *when trained at MSWC scale* [Zeghidour 2021].
34. **Hard-negative mining across confusable words during training** (contrastive) — targets D2's exact
    same-word-vs-confusor axis.
35. **Held-out-language validation split during training** to *enforce* (and measure) language-independence.

### C. Always-on rejection / cascade (D3/D7/D8 — the deployability wall)

36. **Compound two-stage FA budgeting (wake × command multiplies FAR).** ~1 FA/hr wake × ~5% conditional
    command FAR ≈ 0.05 FA/hr compound — the 950 rung — while detection compounds only mildly. Industry-
    standard principle [Gruenstein 2017; Amazon two-stage, ~37% rel FAR reduction].
37. **Multi-frame wake persistence (N consecutive wakes).** Built; ~5 LOC to gate Stage-2.
38. **Dual-filter cascade (distance × duration-ratio) at SSL/student level.** Banked 900 at WavLM;
    replicate at the shipped front-end.
39. **SNR-adaptive wake threshold from the running noise floor.** Built (StreamingEnergyGate computes it).
40. **Personal-VAD-style target-speaker gate (~130 k params).** Speaker-dependent ⇒ fully admissible;
    fires only on the enrolled user, cutting ambient wake rate at the source [Ding 2020].
41. **Record ≥6 h of real household ambient and measure D3 end-to-end** — the honest-measurement gap the
    bands doc names (current ~82 FA/hr is an optimistic proxy).
42. **Refractory/debounce window tuning (~1.0 s)** to suppress repeat fires within one utterance.
43. **Second-pass verifier invoked only on wake** (heavier model, cheap on average) — classic cascade
    [Gruenstein 2017].
44. **Duration-ratio hard pre-gate** (`|log(dur_ratio)| > τ` → reject before distance) — cheap FA cut.
45. **Two-of-three sliding-window voting for a wake** — temporal agreement lowers FA.
46. **Teach-time wake-word distinctness advisor** (reject easily-confusable wakes) — `VocabularyDistinctness`
    already exists.
47. **Streaming embedding cache across overlapping windows** — frees compute budget for the accurate stage.
48. **Confidence-based early exit** (cheap MFCC gate → SSL only on borderline windows) — battery + accuracy.
49. **FA/hr calibrated against the _user's_ environment, not LibriSpeech** (personal negatives, ties to #3).
50. **Adaptive refractory scaled to command length.**
51. **Wake-stage energy hysteresis + adaptive VAD floor** — cheap Stage-1 FA reduction before any model.
52. **Per-user wake threshold via the same conformal machinery as #2** — one FA/hr guarantee, personalized.

### D. Enrollment & channel robustness (D1/D4/D5/D6, encoder-coupled)

53. **In-situ enrollment through the user's own device/room/distance** — deployment channel = enrollment
    channel by construction (a small self-recorded corpus can measure it; TORGO cannot).
54. **Variability-matched augmentation scaled to the user's measured within-word variance** — expand the
    genuine acceptance region without a blanket FAR cost (AudioAugment has the primitives); eval at matched FAR.
55. **Capture via `AudioSource.VOICE_RECOGNITION`** — Android CDD §5.4 mandates NS/AGC **off by default**
    on this source, matching enrollment/query channels [Android CDD 5.4].
56. **Per-session CMN/CMVN** to remove channel mean/scale.
57. **Pitch-shift enrollment augmentation** (`AudioAugment.pitchShift` built, E13-08).
58. **Time-stretch enrollment augmentation** (built).
59. **Band-limit augmentation covering phone-mic bandpass** (D6).
60. **Gain/level augmentation** for speaker-distance variation.
61. **Enrollment outlier rejection** (drop a rep > Nσ from the reps' centroid).
62. **Multi-session enrollment prompting** to capture day-to-day variability.
63. **Reverb augmentation matched to typical room RT60 (0.2–0.4 s)** (D5).
64. **Codec/AAC round-trip augmentation** for phone-path realism.
65. **LUFS loudness normalization before embedding** to stabilize scale.
66. **SNR-gated spectral subtraction (≤10 dB only).** Banked: NR-on-clean is −4.1 pp; SNR-gating fixes it
    without the artifact tax [Iwamoto 2022].
67. **Sub-80 Hz high-pass for wind/handling noise at capture.**
68. **Enrollment budget policy: 2 reps default (D13=950), +1–3 only for flagged-hard commands.**

### E. Matcher & scoring refinements (threshold-level; won't move rank-1, may move FRR/FAR)

69. **Duration-normalized / length-aware PLDA scoring** for variable-length commands.
70. **Endpoint-relaxed (subsequence) DTW** — match the template inside a longer query window, robust to
    endpointing error [Park & Glass 2008].
71. **Per-frame reliability-weighted DTW** (voiced/energy weights).
72. **k-NN over templates (k=3) averaging** — built; re-evaluate at the threshold level, not rank-1.
73. **Mahalanobis local distance under WCCN whitening** (vs Euclidean/cosine).
74. **Heterogeneous ensemble: MFCC-DTW ⊕ SSL-cosine, disagreement → reject** (cheap rejection signal).
75. **Attention pooling over DTW-aligned frames** (best-of-aligned soft pooling).
76. **Per-command accept-threshold floor** to block the accept-all fallback under sparse negatives (the A2
    failure guard).
77. **Platt/temperature calibration of distance→probability per command.**
78. **Second-best-margin (gap to runner-up command) as a rejection feature** — inside the cascade only
    (banked: margin cross-verify alone is −0.4 pp).
79. **Per-session query L2-normalize + centering.**
80. **Prosodic/duration auxiliary channel fused at score level (dysarthric)** — coarse envelope/duration
    may be *more* repeatable than fine spectra for severe speakers (I8).
81. **Envelope/rhythm coarse pre-filter for long commands** — cheap reject before full scoring.
82. **Stability-weighted sub-segment matching (I7)** — weight syllable nuclei over unstable clusters,
    weights learned from the K reps' self-alignment. The one probe that might crack severe-dysarthric AUC.

### F. Evaluation methodology & honesty machinery (protects every number above)

83. **Pre-registered, FAR-matched confirmation for every candidate win** (EVAL-001/003).
84. **McNemar paired testing at matched FA/hr for all A/B claims** [done, E10-06].
85. **Leave-one-fold-out held-out threshold selection — never in-sample θ** (the honest D2).
86. **Per-severity + per-speaker reporting** (heterogeneity is real; aggregate hides F04's 20–46% D2).
87. **Task-level (≤2-attempt) FRR reported alongside single-utterance FRR** (§7.2).
88. **Deployment-slice (≤25-cmd) evaluation matching the product vocabulary.**
89. **Language-split evaluation once the MSWC student exists** (bank D10).
90. **Bootstrap CIs on FRR/FAR** given small dysarthric N.
91. **ROC-AUC as the primary separability diagnostic** — the invariant the walls live on.
92. **Held-out ambient-negative split to _empirically validate_ conformal FAR coverage** (checks #2's guarantee).
93. **Commit result JSONs + seeds** (already practiced) for reproducibility.
94. **Keep device-scaled latency/battery _excluded_ from the composite** (honesty invariant; can't set the wall).
95. **Fidelity gate: reproduce shipped MFCC 59.2% / 75.6% before trusting any new harness** [EVAL-004].

### G. Research bets (multi-quarter, outcome genuinely unknown — lowest EV, highest ceiling)

96. **SAP-scale variability-aware dysarthric metric training** — the only untouched *representation*
    regime for severe-dysarthric D2 (SAP: >500 participants, >400 h as of late-2025) [SAP; I11].
97. **Per-speaker-per-word sub-center losses to absorb within-word scatter** [Deng 2020 principle] on SAP.
98. **TORGO articulatory (EMA) channel as a training-time auxiliary** (dev-time only, never shipped)
    [Rudzicz 2012].
99. **Curriculum mild→severe during dysarthric fine-tuning.**
100. **Privacy-preserving on-device continual prototype refinement over time** [E16-03] — bounded,
    confirmation-gated, never a self-adapting black box (respects the "robustness from re-enrollment" rule).

---

## 11. Top 100 initially-promising but likely-wrong directions (not previously tried here)

**How to read this.** Each is a direction that looks attractive, is **not already in this repo's banked
dead-ends** (§5), yet first principles or cited evidence predict it fails or violates an admissibility
constraint. Ordered by "temptation × wasted cost" (most likely to seduce a future session first). Refuting
this list is as valuable as the pursue-list: it stops the most expensive wrong turns.

### A. Break an admissibility constraint (look powerful, are inadmissible — REAL constraints)

1. **Whisper / large ASR → transcribe → text-match.** Breaks language-independence **and** on-device
   (≤25 MB) **and** fails the population: zero-shot Whisper-large on TORGO severe = **108% WER** isolated
   words [Hui 2024]. The single most seductive wrong turn.
2. **Phoneme / PPG posteriorgram matching.** Reintroduces a phone recognizer (language-model-tinged),
   is a heavy STD tool, and phone posteriors degrade on disordered speech [Hazen 2009; Kent 1999].
3. **Allosaurus universal-phone front-end (2000+ languages).** "Language-independent phones" is a mirage:
   it imposes a phone-inventory prior and phone recognizers degrade markedly on disordered speech
   [Li 2020; disorder-degradation from the general dysarthric-ASR literature].
4. **Cloud second-stage verifier.** Amazon ships it [Amazon 2017], but it breaks the on-device/no-cloud
   constraint (REAL). Do not design around connectivity.
5. **LLM to interpret ambiguous commands.** Breaks determinism + Google Play 2026 assistant policy
   (`isAccessibilityTool=true`, REAL). Non-starter regardless of accuracy.
6. **Per-user _supervised_ fine-tuning of the encoder with labeled reps.** Breaks 1-shot + on-device-
   learning simplicity, and banked LOSO in-domain training already showed ≈0 D2 gain [banked].
7. **Contrastive language-audio (CLAP-style) pretraining.** The text tower needs transcripts and
   reintroduces language dependence.
8. **Multitask with a phoneme-recognition head.** Same reintroduction of phonemes/language dependence.
9. **Retain the ≤2 MB hard cap.** CONSTRAINT-001: no 2026-device rationale, no user downside — an
   *artificial* cap already relaxed to ≤25 MB. Retaining it is itself a wrong direction.
10. **Retain 1-shot-only as sacred.** Banked K-curve says few-shot is *the* D2 lever and 3–5 reps has no
    UX downside — the 1-shot constraint is artificial [banked; CONSTRAINT-001].

### B. Wrong-objective representation learning (optimize the wrong thing)

11. **Scale to a 1 B-param frozen SSL (XLS-R-1B) expecting D2 to move.** Banked scaling: dysarthric AUC
    0.67→0.70 across a 13× param jump (95 M→316 M); 3× more won't reach the 0.97 the 800 rung needs.
12. **i-vector / GMM-UBM features as the command embedding.** Built for *speaker* ID; discards the
    temporal word content that command matching needs.
13. **x-vector TDNN trained for speaker ID as the encoder.** Optimizes speaker discrimination, not word
    discrimination — wrong axis.
14. **Wav2Vec2/HuBERT CTC fine-tune for keyword classification.** Closed-vocabulary; breaks arbitrary-word
    1-shot enrollment.
15. **Triplet loss with random negatives.** Random triplets collapse; prototypical/GE2E dominate few-shot
    [Snell 2017; Wan 2018].
16. **Siamese "same/different" binary verifier as the primary matcher.** Same discriminative-small-sample
    family as the banked MLP verifier, which generalized *worse* across folds [banked].
17. **Reconstruction/generative pretraining (autoencoder or APC/CPC next-frame prediction) as the _sole_
    encoder objective.** Tempting ("unsupervised, no labels needed"), but reconstruction fidelity preserves
    energy/channel/speaker, not same-word-vs-different-word separability — it optimizes the wrong axis for
    a discrimination task. Untried here; first-principles wrong-objective.
18. **Domain-adversarial training to erase speaker identity.** The product is *speaker-dependent* — erasing
    speaker is directly counterproductive.
19. **MAML / meta-learned encoder for fast per-user adaptation.** Instability + on-device training
    complexity; prototypical nets are the stable few-shot choice [Snell 2017].
20. **Mixup on spectrograms for word-ID.** Blends word identities — ill-posed for a discrimination task.

### C. Front-end / feature swaps (banked 2×2 says the front-end is not the lever)

21. **Gammatone / cochleagram front-end swap.** Another front-end swap; the banked 2×2 shows front-end
    under pooling is not where the signal is.
22. **Wavelet-scattering features.** Richer front-end, same ceiling logic; unproven for 1-shot word-ID,
    added compute.
23. **CQT / constant-Q spectrogram.** No mechanism to beat mel on this AUC-bound task.
24. **Raw-waveform CNN trained from scratch on TORGO.** ~3 dysarthric speakers — will overfit; SSL
    pretraining exists precisely because in-domain data is tiny.
25. **20–40 MFCC coefficients for "more detail."** Extra coefficients add noise dimensions; static-13 is
    tuned and higher orders were banked worse.
26. **3rd-order deltas (ΔΔΔ).** Repo banked static > ΔΔ; higher derivative orders are noisier still.
27. **Learnable frontend (LEAF/PCEN) trained on TORGO alone.** Data-starved; learnable frontends help only
    at scale (they belong on the *MSWC* build, not here) [Zeghidour 2021].
28. **VTLN (vocal-tract-length normalization).** A *cross-speaker* normalization — pointless in a
    single-speaker, speaker-dependent app.
29. **Glottal inverse-filtering / source features.** Unreliable for disordered phonation [Kent 1999].
30. **Pitch-synchronous analysis.** Requires reliable F0 — infeasible for severe dysarthria [Kent 1999].

### D. Matchers/classifiers that need data the product doesn't have

31. **HMM per command.** Needs many tokens/word; with 1–5 tokens it is exactly why template-matching/DTW
    is used instead [Rabiner & Juang 1993].
32. **GMM per command.** Same small-sample starvation.
33. **Random forest / SVM per command on pooled embeddings.** Sparse per-user positives → overfit; the
    banked per-command calibration already failed this way [banked].
34. **Logistic-regression global threshold on distances.** A monotone transform of distance — cannot beat
    the ROC whose area is the banked separability [banked ROC-floor].
35. **One-class SVM per command.** Sparse positives; boundary overfits.
36. **Isolation-forest OOV rejection.** Unsupervised, no per-command calibration — won't beat conformal.
37. **Optimal-transport (Wasserstein) frame matching.** Heavier than DTW, same "dysarthric timing breaks
    alignment" failure the banked frame-DTW showed.
38. **Derivative-DTW / weighted-DTW variants expecting alignment gains.** Banked frame-DTW over SSL: no
    lift; the wall is separability, not warping.
39. **Per-utterance PCA/whitening of the mel features to force channel-invariance.** Attractive as
    "remove the channel, keep the content," but whitening removes the between-command timbre variance that
    *carries word identity* — it buys invariance at the direct cost of discrimination. Untried;
    first-principles wrong trade.
40. **Attention cross-encoder (query×template) transformer verifier.** A heavier MLP verifier — same
    across-fold overfitting risk [banked verifier].
41. **RL-learned threshold policy.** The reward is a point on a static ROC; RL adds variance, not AUC.
42. **Bayesian-nonparametric per-command density.** Data-starved at few reps.
43. **Neural-ODE sequence matcher.** Research toy; on-device infeasible.
44. **Graph/lattice matching of frame sequences.** Over-engineered; no evidence of AUC gain.
45. **Energy-distance / MMD between query and template sets.** Exotic; no reason to beat cosine at AUC≤0.70.

### E. Data & training misdirections

46. **Train on UASpeech and expect TORGO D2 to transfer-fix.** Banked "more dysarthric data ≈ no D2 gain"
    for LOSO; different disorder mix won't change the disorder-intrinsic AUC [banked; Kim 2008].
47. **Pretrain on Google Speech Commands (35 English words) as a vocabulary.** English closed-vocab breaks
    language-independence + arbitrary-word if used as classes [Warden 2018].
48. **Multilingual ASR bottleneck features (QUESST-style).** Phone-posterior-ish, language-tinged, heavy
    [MediaEval QUESST].
49. **Self-supervised pretrain on TORGO only.** SSL needs scale; ~3 dysarthric speakers is far too little.
50. **openWakeWord-style massive synthetic (TTS) wake corpus.** Synthetic-only generalization gap **and**
    the pretrained models are non-commercial (CC-BY-NC-SA) [openWakeWord].
51. **Voice conversion to synthesize per-user dysarthric data.** Mixed/limited gains, artifacts, severity-
    dependent degradation [Soleymanpour 2022].
52. **GAN/diffusion TTS augmentation of commands.** Synthesis artifacts impede generalization beyond ~15 h;
    not a D2 lever [2025 VC/synthesis studies].
53. **AutoAugment search over augmentations.** Expensive search; marginal over hand-picked SpecAugment.
54. **SNR-only curriculum.** Noise is not the D2 wall (separability is); banked reverb/band are mild.
55. **Label smoothing / focal loss to "fix" the verifier.** Reweighting doesn't add AUC to an intrinsically
    overlapping signal.
56. **Pseudo-labeling ambient audio as negatives with a weak model.** Label noise; conformal (#2) needs no
    labels — strictly better.
57. **Tempo/speed augmentation as a severe-dysarthric _cure_.** Gains exist but are modest, especially for
    severe speakers [Vachhani 2018].
58. **Sub-center on typical data to "regularize" dysarthric.** The scatter *is* the disorder; regularizing
    on typical won't compress it.
59. **Add EMA articulatory features at _inference_.** TORGO has EMA but phones don't; usable only as a
    training auxiliary, never shipped.
60. **Curriculum from GSC → TORGO expecting D2 monotone gains.** Cross-corpus curriculum won't move the
    disorder-intrinsic separability.

### F. Signal-processing over-engineering (physically N/A or artifact-prone)

61. **Adaptive beamforming.** Single-mic phone — physically inapplicable.
62. **Blind source separation to isolate the speaker.** Needs multichannel; single-channel BSS fails.
63. **Heavy DNN enhancement (Demucs/FullSubNet, >5 M) ahead of the encoder.** Artifacts hurt recognition
    and blow the size budget [Iwamoto 2022].
64. **Always-on dereverberation (WPE).** Reverb is banked-mild; adds latency and can hurt clean speech.
65. **Always-on Wiener filtering.** Same artifact risk as any always-on NR [Iwamoto 2022].
66. **Tiny enhancer (GTCRN/DTLN) applied _unconditionally_.** Only admissible with enrollment-condition
    matching + SNR-gating; unconditional it repeats the banked NR-on-clean −4.1 pp mistake [Iwamoto 2022;
    GTCRN, DTLN].
67. **Modulation-spectrum features as a primary channel.** Plausible robustness but unproven for 1-shot
    word-ID; another feature stage for no measured gain.
68. **Sparse-coding / dictionary-learned features on-device.** Heavy, no evidence vs SSL embeddings.
69. **Formant-normalized features (F1–F3 warping).** Formant estimation unreliable/infeasible for severe
    dysarthria [Kent 1999; Saxon 2019].
70. **48 kHz capture for "more detail."** 16 kHz is speech-sufficient; 48 k wastes compute/battery.

### G. Deployment/architecture misdirections

71. **Assume NNAPI/NPU acceleration everywhere.** NNAPI is fragmented; a small INT8 CPU model is the safe
    target (the ≤25 MB relaxation is what buys headroom, not the NPU).
72. **TFLite GPU delegate for an always-on 25 MB model.** Battery/thermal cost; the win is a small INT8 CPU
    model behind a cheap gate.
73. **Continuous full-SSL always-on (no cheap Stage-1 gate).** Battery/thermals; violates the two-stage
    design that makes always-on viable.
74. **Store raw enrollment audio for re-embedding.** Privacy risk — store embeddings/features (ties to #3).
75. **On-device backprop personalization every session.** Battery + instability; bounded prototype
    refinement is sufficient [E16-03].
76. **Per-command separate ONNX models.** Memory blowup — one shared encoder + per-command prototypes.
77. **Float32 on-device inference.** 4× size/compute vs INT8 for no accuracy at this scale.
78. **Bluetooth-mic-only capture path.** Variable latency/codec; don't architect around it.
79. **Cloud model-update push as a core dependency.** Breaks the offline guarantee.
80. **"Always escalate every wake to the big model."** Defeats the cascade FA-budget arithmetic that makes
    D3-950 reachable [Gruenstein 2017].

### H. Evaluation / statistics traps (manufacture a number that won't replicate)

81. **Headline the in-sample-threshold D2 (the 11% number).** Not held-out — the honesty rule forbids it
    [banked note].
82. **Band language-independence from CV augment-self-match (~100%).** A fingerprinting tautology / null
    [banked D10].
83. **Report the aggregate-with-controls (71.9%) as the dysarthric headline.** Easier population; a mislabel
    [banked].
84. **Select the vocab-distinct subset on the test set.** Leaks; inflates [banked note].
85. **Micro-average FRR across all speakers into one pooled ROC.** Looks "more data, tighter CI," but
    F04's (mild) easy positives mask the severe F01/F03 tail — the aggregate then hides the population the
    metric exists to protect. Report the macro (per-speaker) aggregate. Untried trap; the banked numbers
    are already per-speaker, so pooling would be a *new* mistake.
86. **Optimize rank-1 to "fix" D2.** Ranking ≠ threshold separability; +rank-1 with flat D2 is the banked
    pattern [banked].
87. **Chase D11/D12 device bands to raise the composite.** Excluded by design — a modelled number can't set
    the wall [scorecard invariant].
88. **Simulate a many-shot dysarthric number to claim K≥4.** A PROXY can't earn a green band [banked honesty].
89. **Average bands across domains (mean, not min).** Hides the wall; the composite is a MIN [scorecard MIN invariant, bands doc — *not* EVAL-002, which
    governs held-out thresholds].
90. **Report FRR without the matched FAR.** A meaningless operating point.
91. **Headline EER instead of FRR@FAR≤5%.** Hides the asymmetric FA budget the product actually lives under.
92. **Report best-of-N seeds/layers.** Selection inflation without fresh confirmation [EVAL-003].
93. **Claim a language-independence Δ from two chance-level values.** The null, not signal [banked D10].
94. **Treat the in-regime Picovoice proxy as real ambient FA/hr.** Optimistically biased [banked D7].
95. **Silently re-scope to the typical population to "reach 950."** Legitimate only as an explicit owner
    sign-off with the old metric kept visible [§7; honesty rule].

### I. Product-scope illusions (route around the wall without admitting it)

96. **Fixed-vocabulary wake word (Porcupine/PD-DWS style) to hit low FAR.** PD-DWS reaches FAR 0.0032/FRR
    0.005 — but by training on a *fixed* wake word + dysarthric data (closed-vocab, language-dependent):
    it breaks arbitrary-word + language-independence [LRDWWS/PD-DWS 2024; Porcupine console-trained].
97. **License a proprietary wake engine (Porcupine) for the hard part.** Custom words require cloud console
    training — not free-form on-device arbitrary-word enrollment [Picovoice].
98. **Declare severe-dysarthric 950 by collecting more dysarthric data.** Banked: LOSO in-domain ≈ frozen on
    D2 — it's the disorder's within-word variability (AUC ~0.70), not data scarcity [banked].
99. **Assume a second mic / wearable to escape single-channel limits.** Changes the product; not the core
    on-phone USP.
100. **Wait for a bigger foundation model to "solve" dysarthric D2.** The banked encoder-invariance (MFCC →
    316 M → learned verifier all ~0.70 AUC) predicts scale alone won't; only a variability-*absorbing*
    objective at SAP scale (I11) has an untested shot, and even that targets 0.70→0.80, not 0.97.

---

## 12. References (cross-validated, 2026-07-10)

Each entry was checked against ≥2 independent sources in three verification passes; corrections from that
check are folded in. "repo-banked" items live in this repository's testing docs, not the external literature.

**Corpora & licenses**
- **MSWC** — Mazumder et al., "Multilingual Spoken Words Corpus," NeurIPS 2021 Datasets & Benchmarks.
  340 k+ keywords, 23.4 M ~1 s clips (>6000 h), 50 languages, **CC-BY-4.0**; forced-aligned from Common
  Voice. mlcommons.org/…/multilingual-spoken-words-corpus / huggingface.co/datasets/MLCommons/ml_spoken_words
- **MUSAN** — Snyder, Chen, Povey 2015 (arXiv:1510.08484). ~109 h; OpenSLR **SLR17**, **CC-BY-4.0**
  (commercial use permitted). openslr.org/17
- **OpenSLR SLR28 (RIRS_NOISES)** — companion to Ko et al. ICASSP 2017; **Apache-2.0**. openslr.org/28
- **Mozilla Common Voice** — **CC0** (public-domain dedication). commonvoice.mozilla.org
- **TORGO** — Rudzicz, Namasivayam, Wolff, "The TORGO database…," *Lang. Resources & Evaluation* 46(4):523–541,
  2012. Free for academic/non-profit use w/ citation. cs.toronto.edu/~complingweb/data/TORGO
- **UASpeech** — Kim, Hasegawa-Johnson et al., "Dysarthric speech database for universal access research,"
  Interspeech 2008. 19 cerebral-palsy speakers, 765 words/speaker.
- **Speech Accessibility Project (SAP)** — UIUC/Beckman, announced 2022-10; PD/DS/ALS/CP/stroke via signed
  DUA. Interspeech-2025 release >400 h from >500 participants; ~2000 recorded by end-Sept 2025.
- **LibriSpeech** — Panayotov et al., ICASSP 2015; ~1000 h read English (960 h training partition),
  **CC-BY-4.0**. openslr.org/12
- **Google Speech Commands v2** — Warden 2018 (arXiv:1804.03209). 35 words, 105,829 utterances,
  **CC-BY-4.0**.
- **EasyCall** — Turrisi et al., Interspeech 2021 (arXiv:2104.02542). Italian dysarthric commands; 31
  dysarthric + 24 healthy speakers; 21,386 recordings. **No formal corpus license stated (UNVERIFIED)** —
  the arXiv CC-BY covers the paper, not the data.

**Encoders, frontends, distillation**
- **WavLM** — Chen et al., IEEE JSTSP 2022 (arXiv:2110.13900). Base/Base+ = 94.7 M params; Large = 316.6 M.
- **DistilHuBERT** — Chang, Yang, Lee, ICASSP 2022 (arXiv:2110.01900). 23.5 M params (75% smaller than HuBERT-base).
- **Knowledge distillation** — Hinton, Vinyals, Dean 2015 (arXiv:1503.02531).
- **PCEN** — Wang et al., "Trainable Frontend for Robust and Far-Field Keyword Spotting," ICASSP 2017
  (arXiv:1607.05666).
- **LEAF** — Zeghidour et al., ICLR 2021 (arXiv:2101.08596).
- **SpecAugment** — Park et al., Interspeech 2019.

**KWS backbones & few-shot**
- **BC-ResNet** — Kim et al., "Broadcasted Residual Learning…," Interspeech 2021. BC-ResNet-8 ≈ 321 k params,
  98.7% GSC v2 (the 9.2 k -1 variant is 96.6% GSC v1 / 96.9% v2 — don't attach 98% to it).
- **Keyword Transformer (KWT)** — Berg et al., Interspeech 2021; 98.6% GSC v2 (12-cmd).
- **Few-Shot KWS in Any Language** — Mazumder, Banbury et al., Interspeech 2021. EfficientNet-B0 embedding,
  ~11 M params.
- **On-device few-shot personalization** — Cioflan, Cavigelli, Benini, tinyML 2024 (arXiv:2403.07802).
  23.7 k trainable params; unseen-speaker error 30.1%→24.3% on GSC-35.

**Metric learning & scoring backends**
- **Prototypical Networks** — Snell, Swersky, Zemel, NeurIPS 2017.
- **GE2E loss** — Wan et al., ICASSP 2018.
- **PLDA** — Ioffe, ECCV 2006; Prince & Elder, ICCV 2007.
- **ECAPA-TDNN** — Desplanques et al., Interspeech 2020 (~6.2 M / ~14.7 M param configs).
- **ArcFace** — Deng et al., CVPR 2019; **Sub-center ArcFace** — Deng et al., ECCV 2020 (label-noise robust).
- **Adaptive s-norm** — Matejka et al., "Analysis of Score Normalization in Multilingual Speaker
  Recognition," Interspeech 2017 (cohort selection matters; ~30% rel gain).
- **Attentive statistics pooling** — Okabe et al., Interspeech 2018.
- **Conformal prediction** — Vovk, Gammerman, Shafer, *Algorithmic Learning in a Random World*, Springer
  2005; Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction…," 2021 (arXiv:2107.07511).

**Sequence matching / QbE**
- **Acoustic word embeddings** — Settle & Livescu, SLT 2016; multilingual AWE transfer — Kamper et al.,
  ICASSP 2020 (AWEs beat raw-DTW on word discrimination).
- **QbE-STD with PPG + DTW** — Hazen, Shen, White, ASRU 2009.
- **Segmental-DTW pattern discovery** — Park & Glass, IEEE TASLP 2008.
- **QUESST/SWS (MediaEval 2013–15)** — best systems = multilingual bottleneck/phone-posterior features + DTW.
- **soft-DTW** — Cuturi & Blondel, ICML 2017.
- **DTW Barycenter Averaging (DBA)** — Petitjean, Ketterlin, Gançarski, *Pattern Recognition* 44(3), 2011.

**Cascade / wake-word / VAD**
- **Cascade KWS on mobile** — Gruenstein, Álvarez, Thornton, Ghodrat, "A Cascade Architecture for Keyword
  Spotting on Mobile Devices," 2017 (arXiv:1712.03603). [venue corrected: arXiv/workshop, not a main conf]
- **Two-stage on-device wake word** — Amazon (Monophone-based background modeling, ICASSP 2018; ~16% rel
  FRR / ~37% rel FAR reduction) + cloud verification (2017; Interspeech 2020).
- **Personal VAD** — Ding et al., Odyssey 2020 (~130 k params, target-speaker VAD); Personal VAD 2.0,
  Interspeech 2022.
- **Silero VAD** — MIT license, ~2 MB model, widely used on-device.

**Speech enhancement (lightweight) + the artifact caveat**
- **GTCRN** — Rong et al., ICASSP 2024. 23.7 k params, ~39.6 MMACs/s (paper figures); the official repo
  now states **48.2 k params / 33.0 MMACs** after ERB-module inclusion. Beats RNNoise.
- **DTLN** — Westhausen & Meyer, Interspeech 2020. <1 M params, real-time.
- **RNNoise** — Valin, IEEE MMSP 2018 (arXiv:1709.08243). ~85 kB 8-bit model.
- **Enhancement artifacts hurt ASR** — Iwamoto et al., "How bad are artifacts?…," Interspeech 2022
  (+ TASLP 2024 follow-up).

**Dysarthria / disordered-speech evidence**
- **Acoustic variability & imprecise articulation** — Kent, Weismer, Kent, Vorperian, Duffy, "Acoustic
  studies of dysarthric speech…," *J. Communication Disorders* 32(3):141–186, 1999.
- **Formant/pitch estimation infeasible for severe dysarthria** — Saxon et al., 2019 (arXiv:1911.11360, IEEE
  TASLP); corroborated by Kent 1999.
- **Whisper fails on severe dysarthria** — Hui, Zhang, Mohan 2024 (arXiv:2411.00980): zero-shot Whisper-
  large-v2 TORGO severe = 108.1% WER isolated words / 56.3% sentences vs mild 28.9%/5.16%.
- **Personalized disordered-speech ASR** — Shor et al., Interspeech 2019 (62% rel WER gain, ALS; 71% of gain
  from 5 min data); Green et al., Interspeech 2021 (personalized beats human listeners on short phrases).
- **Tempo/speed augmentation for dysarthric ASR** — Vachhani, Bhat, Kopparapu, Interspeech 2018 (modest,
  esp. severe).
- **Synthetic/VC dysarthric augmentation is mixed** — Soleymanpour et al. 2022 (arXiv:2201.11571, ~5.67%
  severe) + 2025 severity-dependent/degradation studies.
- **Universal phone recognition** — Li et al. (Allosaurus), ICASSP 2020 (2000+ languages); disorder
  degradation supported only by general dysarthric-ASR literature (no Allosaurus-specific eval — UNVERIFIED).

**External SOTA reference points**
- **LRDWWS / PD-DWS** — Low-Resource Dysarthria Wake-Up Word Spotting, **IEEE SLT 2024** [venue corrected].
  Winning PD-DWS: FAR 0.00321 / FRR 0.005 — but **Mandarin, fixed wake word, speaker-dependent closed-set**
  (breaks arbitrary-word + language-independence). arXiv:2409.10076; lrdwws.org
- **Porcupine / Picovoice** — custom wake words trained via cloud Console; no free-form on-device
  arbitrary-word enrollment.
- **openWakeWord** — Apache-2.0 code, but pretrained models trained on ~100% synthetic TTS and released
  **non-commercial (CC-BY-NC-SA 4.0)**.
- **ZP-KWS** — "Personalized Keyword Spotting for User-Defined Keywords Leveraging Text-Independent
  Speaker Verification," arXiv:2606.20106. Target-only FRR@1%FAR: **29.47% (LibriPhrase-Easy),
  33.12% (Qualcomm)** — but also **78.20% (LibriPhrase-Hard), 49.76% (GSC)**, so the "~29–33%" this
  report quotes is the two friendliest datasets only. **Two caveats for using it as the 950 anchor:**
  (a) it is a *personalized keyword+speaker* result (single text-independent enrollment utterance),
  **not** a clean speaker-independent open-vocab baseline — so it does not cleanly support §3's "no
  published system exploits speaker-dependence" contrast; (b) it is read at **FAR 1%**, not the report's
  **FAR 5%**, so any head-to-head must re-match FAR (rule #90). Keyword-only open-vocab work is normally
  reported as EER/AUC on LibriPhrase (PhonMatchNet, arXiv:2308.16511; CED; CLAP-IPA), not FRR@1%FAR.

**Classic anchor**
- **Template matching / DTW vs HMM** — Rabiner & Juang, *Fundamentals of Speech Recognition*, Prentice-Hall
  1993: DTW template-matching was the dominant pre-HMM paradigm and is the natural fit when only 1–5 tokens
  per word exist (HMMs need more training tokens). The few-token advantage is textbook-level, not a single
  numbered result.

**Platform**
- **Android capture path** — Android CDD §5.4 mandates NS/AGC **off by default** on
  `AudioSource.VOICE_RECOGNITION` (a compliance default, not an API switch); AOSP pre-processing guidance
  concurs.

---

## 13. Candidate experiments (review pass, 2026-07-10) — NOT yet pre-registered

**Status: candidates, not commitments.** These were proposed in the 2026-07-10 review pass. Unlike §8
(X1–X7), they are **not** pre-registered under EVAL-003: each must get a single a-priori hypothesis and a
FAR-matched adjudication plan *before* it runs, and any survivor still needs fresh confirmation before
banking. They are ordered by information-per-cost. Items **A1/A3/D24** are the fixes for the confounds/
gaps flagged inline (K-curve subset confound, D2 operating-point mismatch, I4 stage-independence); **A2**
is the highest information-per-hour item available. A1–A3 are ~a day each on cached data and de-risk more
of the roadmap than anything in §8 — run them ahead of X3/X2/X4.

### A. Repair the evidence base first (cached, hours–1 day; do before §8)
- **A1 — Fixed-subset K-curve.** Recompute K=1..4 on the *fixed* set of words with ≥5 reps, held-out θ,
  one encoder. Gate: K=4 ≤15% on the fixed subset → the structural lever holds; if the drop shrinks
  materially, every §3 projection re-bases. (Fixes the §2 K-curve confound.)
- **A2 — Deployment-real negatives vs the dysarthric wall.** Rescore cached severe-dys genuine pairs
  against ambient/OOV pools instead of TORGO in-vocab singletons. Gate: severe-dys AUC ≥0.85 → a large
  share of the "0.70 wall" is a negative-set artifact and §7.2(b) becomes evidence-backed, not hoped.
- **A3 — FAR%→FA/hr bridge.** Windows/hour at the deployed hop on real ambient; restate the banked 13.8%
  at the bands-doc ≤5 FA/hr operating point. (Fixes the §2 D2 operating-point mismatch.)
- **A4 — Severe-dys scatter decomposition.** PCA the within-word embedding residuals per speaker:
  structured/low-rank (duration, loudness, variant axes) or isotropic? Structured → I11 has a mechanism;
  isotropic → the wall is honest and I11's EV drops. Decides a multi-quarter bet for a day of linear algebra.
- **A5 — K-curve replication on a second corpus** (UASpeech control blocks / a typical corpus with
  repeats). EVAL-003 discipline applied to the central lever before a stack is built on it.

### B. Decision layer beyond §4 (cached, days)
- **B6 — Aggregation-rule sweep.** Min-over-K is a noisy extreme order statistic; test soft-min
  (logsumexp/temperature), mean-of-best-2, k-of-K voting, median, at matched held-out FAR. Gate: beat 13.8%.
- **B7 — KDE likelihood-ratio scoring.** Score = log p_genuine(d)/p_ambient(d) — the continuous, fusable
  form of conformal thresholds; feeds the dual-cascade as a feature, not a binary gate.
- **B8 — First-attempt-as-template retry.** On a margin-zone reject, add attempt-1's embedding as a
  temporary K+1th template when scoring attempt 2 — *exploits* attempt correlation (which breaks I5's
  independence) as signal. Gate: P(accept₂|reject₁) beats vanilla retry at matched task-level FAR.
- **B9 — SPRT-style sequential protocol.** Accumulate log-LRs across attempts with Wald bounds instead of
  a fixed 2-attempt rule — task-level FRR *and* FAR controlled by construction (what X3 currently lacks);
  gives §7.2 a principled artifact to sign off.
- **B10 — Margin-zone width optimization.** Choose the retry zone on the ROC to maximize task-FRR
  reduction s.t. a task-FAR budget — turns I5 from heuristic into an optimized operating point.
- **B11 — Per-command-set confusability shaping.** Pairwise thresholds/margins from enroll-time
  cross-distances between the *user's own* commands. Attacks D14 (in-vocab confusion), a different error
  mode from open-set FA that no §4 item targets directly.
- **B12 — Environment-conditioned conformal calibration.** Cluster the ambient pool by noise state (from
  the running noise floor); calibrate per state; switch deterministically. Gate: per-state FAR validity
  with FRR below the single-threshold arm.
- **B13 — Conformal validity engineering.** (a) Block-subsampled pools for exchangeability under
  autocorrelation; (b) contamination guard — quantify user-speech leakage and the FRR cost of excluding
  ±N s around accepted wakes; (c) day-1→day-7 coverage-drift audit. Prerequisites for I2's guarantee.

### C. Encoder-build de-risking (before/inside X1)
- **C14 — Frozen-feature episodic-head ceiling probe** (~1 GPU-day). Train only a small metric head on
  MSWC episodes over frozen distilhubert/wavlm-base. Recovers most of I1's projected gain → the objective,
  not capacity, was the gap (cheap insurance); if not, you know where the loss lives before full training.
- **C15 — Learned layer-mix probe.** SUPERB-style scalar weights over cached SSL layers under the episodic
  loss — cheapest representation probe; tells X1 which layers to distill from (currently guessed L10+L14).
- **C16 — Architecture bake-off at 1% MSWC scale.** BC-ResNet vs ECAPA-lite vs tiny conformer at matched
  params before committing — the report picks backbones from literature alone.
- **C17 — Asymmetric episodes: clean supports, noisy/reverberant queries.** Matches deployment and directly
  targets D4/D5 — the domains that actually bind the composite (§6) and that no §4 training item optimizes.
- **C18 — Relational KD.** Distill the teacher's pairwise *distance structure* (same/different-word margins;
  RKD) rather than features/logits — the two failed attempts were feature-copy; distance structure is the
  quantity the product consumes.
- **C19 — MSWC domain-gap audit.** MSWC is forced-aligned from continuous read speech; commands are
  isolated citation-form words. Validate the student on isolated-word data (GSC + a small self-recorded
  command set) before trusting MSWC-internal validation. X1's gate is currently blind to this shift.
- **C20 — Phrase-length generalization.** Commands are often multi-word; MSWC is 1-s single words. Train
  with concatenated-word episodes/random crops; evaluate on multi-word phrases.
- **C21 — Deployable-gap decomposition.** Measure large→base→distilled→INT8 stepwise on one eval so the
  3–18 pp retention gap gets causal shares (capacity vs distillation data vs quantization).
- **C22 — D10 pilot without X1.** Frozen wavlm-large QbE rank-1/AUC per language on MSWC, 5 typologically
  diverse languages, matched vocab. Banks a preliminary D10 in days and gives X1 its language baseline —
  the report ties D10's first banding to the expensive student unnecessarily.

### D. Always-on / D3 (fixing X5)
- **D23 — Power-compliant ambient corpus.** 6 h self-recorded + ≥60 h assembled household ambient
  (CHiME-Home/DCASE domestic, TV-on strata), banking rule pre-registered as "bank ≤X FA/hr only if the
  Poisson 95% upper bound ≤ X." Direct fix for X5's rule-of-three limit; without it no D3 claim above 800
  is bankable.
- **D24 — Stage-correlation audit.** On the existing Picovoice streams: conditional stage-2 FAR on stage-1
  survivors vs marginal FAR. Quantifies I4's independence optimism for near-zero cost before any 950 claim.
- **D25 — Other-speaker FA measurement.** FA/FR on non-user speech (other TORGO speakers, TV voices,
  household members). Measures the rejection speaker-dependence actually buys, and whether the personal-VAD
  gate is even needed.

### E. Channel (D5 binds the typical composite — currently under-served)
- **E26 — D5 loss decomposition.** Stratify the 81.4% by RT60/condition and enrollment coverage: early-
  reflection mismatch (cheap enrollment-augmentation fix) or intrinsic smearing (needs I10's dereverb)?
- **E27 — K-budget allocation factorial.** At fixed K=4: {4 clean} vs {2 clean+2 reverb} vs {2 clean+2
  noisy} vs {3 clean+1 in-situ}. Multi-condition is banked as additive; the *allocation tradeoff at fixed
  rep budget* — the actual product decision, since D13 fixes the budget — is unmeasured.

### F. Dysarthric-specific mechanisms (beyond I7/I8)
- **F28 — Multimodal enrollment.** Cluster a severe speaker's reps; if productions form 2–3 stable variants
  (categorical variant-switching, not pure noise), enroll per-cluster templates + per-cluster thresholds.
  Gate: severe-dys AUC ≥0.75 (same bar as X6, different mechanism).
- **F29 — Query-side rate normalization.** Envelope-modulation syllable-rate estimate → deterministic
  linear time-warp toward the template rate *before* embedding (SSL embeddings are rate-sensitive; severe
  speakers vary rate hugely). Distinct from enrollment-side tempo augmentation.
- **F30 — UASpeech block-drift analysis.** Within-block vs cross-block genuine distances (B1/B2/B3): is the
  ~40% plateau short-term variability or session drift? Decides re-enrollment cadence and whether I2's pool
  needs recency weighting — the report never addresses *time* for this population.

---

## 14. Corrections ledger (2026-07-10 review pass)

Applied after an independent review (repo cross-checks, math re-derivation, external-citation verification
against ≥2 primary sources each). Objective errors were corrected inline with visible markers; contingent
or re-run-dependent findings were added as **caveats + queued candidate experiments** (§13), never rewritten
as settled — the honesty rule forbids presenting an unresolved finding as fixed.

| # | Location | Before → After | Reason |
|---|---|---|---|
| 1 | Wall doc §ROC-floor + §1/§11.11/§11.100 here | AUC **0.93 → 0.97** for the 800 rung; jump +0.23 → **+0.27** | 0.93 is the EER=15% value; the rung is FRR=15%@FAR=5% (d′=2.68 ⇒ AUC=0.971). Strengthens the wall. Visible dated note added to the banked wall doc. |
| 2 | §6 composite table | Added **D4/D5/D6 column**; ">950 live target" → "**>950 only if D5 and D14 also reach ≥950**" + residual-wall note | Composite is a MIN; D5=800/D14~900 (measured) bound it, and no §8 gate targets D5-950. Surfaced as an open owner question, not silently demoted. |
| 3 | §8 X5 gate | "stretch ≤0.1 @ 6 h" → **rule-of-three hours gate** (6 h ⇒ ≤0.5 only; ≥30 h for 900; ≥60 h for 950) | 0 FA in T h ⇒ 95% upper bound 3/T FA/hr; 6 h cannot bank a rung below 0.5. |
| 4 | §4 I4 | Added **FA-side stage-independence caveat** (→ candidate D24) | The ×0.05 compound assumes independent stages; wake survivors are adversarially selected + share the encoder, so conditional FAR can exceed marginal. |
| 5 | §4 I5 + §8 X3 gate | Added **task-level FAR** requirement | A retry is a fresh impostor draw too; FRR gain must be read at the two-attempt FAR or it is partly FAR inflation. |
| 6 | §4 I2 | Added **conformal validity conditions** (exchangeability / contamination / drift) | The "finite-sample guarantee" holds only under these; adjacent windows autocorrelate and the pool captures the user's own commands. |
| 7 | §8 header + top comment | Pre-registration cite **EVAL-001 → EVAL-003** | EVAL-001 is the cross-distribution-threshold rule; pre-registration is EVAL-003. |
| 8 | §11.89 | "[EVAL-002]" → **[scorecard MIN invariant]** | EVAL-002 governs held-out thresholds, not the composite=MIN construction. |
| 9 | §0 exec + §12 | **ZP-KWS** qualified + added to §12 | Its 29–33% is the two friendliest datasets at FAR **1%** (report uses 5%) and is a personalized keyword+speaker number, not a speaker-independent baseline; not FAR-matched to the report. |
| 10 | §1 D2 gap | "~5× reduction" → **~7×** (from held-out 13.8%) | 13.8/2 ≈ 6.9; 5× came from the in-sample 11.1%. |
| 11 | §3 thesis / §0 item 3 | "every representation lever is measured-capped" → capped **for severe-dysarthric D2** | Typical D1 rose 86.8→89.9 with a larger frozen encoder this session; I1 (unbuilt) is caught by no measurement. |
| 12 | §2 K-curve | Added **subset-confound caveat** (→ candidate A1) | The curve is measured on "words with ≥K+1 reps," so the word set shifts with K; part of the drop may be word selection. |
| 13 | §2 | Added **D2 operating-point mismatch caveat** (→ candidate A3) | Banked D2 uses FAR≤5%/trial on TORGO in-vocab negatives; the rung is ≤5 FA/hr on ambient — different operating points. |
| 14 | §10 #9 (DBA) | "keeps distribution info" → **caveat**: a barycenter discards within-command scatter | Scatter is exactly what min-over-K (#1) and PLDA (#4) exploit; a lone barycenter would undo lever #1. |
| 15 | §12 minors | BC-ResNet-1 96.6% → **96.6% v1 / 96.9% v2**; GTCRN + **repo revision 48.2 k/33.0 MMACs**; Hui mild-sentence 5.2% → **5.16%** | Primary-source precision from the citation-verification pass. |

**Verified and left unchanged** (confirmed against primary sources in the review pass): MSWC (340 k
keywords / 23.4 M clips / 50 langs / CC-BY-4.0), openWakeWord non-commercial pretrained models,
LRDWWS/PD-DWS (FAR 0.00321 / FRR 0.005, Mandarin fixed-word), EfficientNet-B0 ~11 M, Cioflan 30.1→24.3%,
Android CDD §5.4, and the report's other two AUC figures (950-rung 0.99, K=4 0.98, both already computed
the FRR@FAR way).
