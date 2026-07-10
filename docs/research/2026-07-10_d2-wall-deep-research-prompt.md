# Deep-research prompt — the D2 verification wall

**Generated:** 2026-07-10 · **via** `/deep-research-prompt`
**Binding metric:** D2 = FRR @ FAR≤5%, held-out, dysarthric in-vocab confusor rejection
**SOTA state:** composite `<600` (wall-dominated), D2-bound; genuine–impostor AUC≈0.70, encoder-invariant

Sources: `core/eval/src/main/kotlin/com/speechangel/core/eval/SotaScorecard.kt` (composite = min band),
`docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md`,
`docs/testing/2026-07-10_dysarthric-round3-results.md`, `docs/plans/2026-07/sota-800-push.md`.

---

```
DEEP RESEARCH: Verification-limited voice-command recognition under severe dysarthria

SYSTEM (admissibility envelope — hard filter, any violating method is out regardless of accuracy):
On-device, speaker-dependent, language/vocabulary-agnostic (arbitrary user-chosen words), few-shot-enrolled
(3–5 reps/command), deterministic (no LLM, no cloud) Android accessibility command verifier. Pipeline:
frozen SSL encoder (WavLM-large = current ceiling) → utterance embedding → cosine/DTW score → per-command
accept/reject at a fixed operating point. NNAPI/INT8, on-device model ≤~150 MB.

THE WALL (single binding metric, "D2"): FRR @ FAR≤5%, held-out, dysarthric IN-VOCABULARY CONFUSOR
rejection, does not fall below ~55% under any admissible lever. Genuine-vs-impostor score separability is
capped at ROC-AUC ≈ 0.70; FRR≤15% at FAR≤5% needs AUC ≳ 0.95. The cap is ENCODER-INVARIANT: SSL front-ends
lift closed-set accuracy walls (dysarthric rank-1 79.4%, clears production band) but do NOT move D2.
Measured root cause (variance decomposition, real TORGO corpus, n=8): intra-speaker within-word variance
across repetitions of command W ≳ between-command distance — a speaker's own renditions of W scatter as far
as W is from a distinct command W′. SEVERITY-GRADED: mild dysarthria D2≈27% (deployable), very-severe
D2≈90%. Typical (non-dysarthric) speakers are NOT verification-limited.

PRECISE PROBLEM STATEMENTS (search admissible solutions; judge each returned method pass/fail against it):
P1 SCORE-DOMAIN. Given per-command genuine/impostor score distributions with genuine coefficient-of-variation
   ~1, what decision-rule / score-normalization / calibration maximizes genuine–impostor AUC at a FIXED
   per-command FAR≤5%, using only on-device enrollment-time statistics? (T-/Z-/S-/AS-norm, cohort/impostor-
   cohort normalization, per-command adaptive thresholds, conformal/quantile calibration.) Quantify expected
   AUC gain at CV≈1.
P2 REPRESENTATION-DOMAIN. Is there an on-device-admissible trainable verification BACKEND on top of frozen SSL
   embeddings (PLDA / neural-PLDA / metric-learning / few-shot discriminative adapter) that raises separability
   specifically when within-word variance dominates — where frozen-SSL+cosine cannot? (Distinct from swapping
   the encoder, which is refuted below.)
P3 VARIABILITY MODELING. Can modeling the within-word trajectory DISTRIBUTION (segmental/dynamic/articulatory-
   inspired, or variance-aware exemplar sets) recover separability that a single summary vector destroys?
P4 ENROLLMENT-SIDE. Variance-aware / active enrollment — stable-exemplar selection, per-command variance
   normalization, severity-scaled #reps — does it move D2 at fixed UX cost?
P5 REFRAME. For the severe tail where AUC≈0.70 is near information-theoretically fixed, what deterministic
   SYSTEM-level rule (abstain+confirm turn, per-severity operating point, complementary modality) yields a
   usable product? Bound achievable operating point vs. speaker severity.

DO NOT RE-DERIVE (already refuted on THIS exact problem; cite only to contrast):
- Front-end swaps (MFCC↔delta-delta): within sampling error.
- SSL encoder upgrade as a D2 fix: lifts accuracy, NOT verification separability (encoder-invariant).
- Per-user within-word whitening/contraction: +10.6pp on one demographic (female) but REFUTED on held-out
  males (Δ−1.4pp, p=0.63) — not speaker-general.
- Nuisance-subspace projection: separability gain was a train/test LEAKAGE artifact.
- Confusion-aware vocabulary selection: rep-limited negative.
- Distilled ≤2 MB student: below MFCC (the ≤2 MB cap was artificial; re-examine ONLY under the ≤150 MB
  envelope, not the old cap).
- ANY simulator-based dysarthric evidence: the sim failed its fidelity gate (unfit). Require real dysarthric
  corpus, per-severity, held-out speaker, FAR-matched. Same-demographic control ≠ generalization.

PRIORITIZE (highest-value untried frontier): P1 per-command score normalization / adaptive thresholds (never
run; most direct attack on a fixed-AUC-at-fixed-FAR wall) and P2 trainable backend on frozen SSL embeddings.

DELIVERABLE (per P1–P5): (a) 3–5 strongest candidate methods + primary citations; (b) reported effect size on
genuine–impostor separability or FRR@fixed-FAR in dysarthric OR analogous high-within-class-variance
verification (speaker verification under vocal pathology, child ASR, atypical/accented speech); (c) on-device
feasibility under the envelope; (d) ranked ≤3-experiment shortlist most likely to move AUC 0.70→>0.85, with
pre-registered success criteria. FLAG any method whose evidence is only from typical-speech benchmarks as an
external-validity risk.
```
