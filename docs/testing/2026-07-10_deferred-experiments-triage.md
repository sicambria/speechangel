# Deferred-experiment triage — what got run, what is subsumed, what is blocked

**Date:** 2026-07-10 · **Context:** the goal was "run all experiments that were NOT run before." This
triages the full deferred backlog (Round-2 26 items, Round-3 26 items, Round-1 blocked 5) against the
Round-4 results (`docs/testing/2026-07-10_d2-wall-p1p2p3-results.md`) and cost/constraint discipline
(CLAUDE.md §7; CONSTRAINT-001). **Running all ~57 verbatim is not warranted** — most are members of families
now settled by a decisive negative, and several are corpus/compute-blocked. Disposition of every cluster
below; the high-value runnable ones **were executed this session**.

## Executed this session (the high-value untried attacks)

| ID (this session) | = deferred item(s) | Result | Evidence |
|---|---|---|---|
| **R1** frame-DTW D2 | Round-2 **J16/J** (alignment-aware), frame_dtw_sep deferred "full D2" | NOT-BANKED | `r1_frame_dtw_d2.json` |
| **R2** backend D2 | Round-3 **P2** family | KILLED | `r2_backend_d2.json` |
| **R3** score-norm D2 | Round-3 **R16–R20** (per-cmd/T-/Z-norm), Round-2 **K** decision layer | NULL @ matched FAR | `r3_scorenorm_d2.json` |
| **N1** best stack | Round-3 **N1** (PRIMARY DoD, never run) | band-900 CONFIRMED UNREACHABLE | `n1_stack_d2.json` |

Plus the enabling asset: **`male_frames_L14.npz`** (male frame embeddings extracted — unblocks P3 on the
live moderate population).

## Round-2 backlog (26 items) — disposition by cluster

| Cluster (plan §) | Theme | Disposition | Rationale |
|---|---|---|---|
| **G** (G2, G3b, G4) | personalized within-word contraction (whitening/subspace) | **SUBSUMED — do not run** | G1 refuted on held-out males (p=0.63); G3 leakage artifact; R2 (P2, same linear-transform family) KILLED. The whole "learn a transform to shrink within-word scatter" family is settled: it raises central AUC, not the tail. |
| **H** (H7–H10) | discriminative command-set co-design | **SUBSUMED** | N2 (confusion-aware vocab) was a rep-limited negative; H is the same between-word-separation lever. Central separability is not the binding quantity (Round-4). Small-vocab N≈5 (H6) already banked band 700 separately. |
| **I** (I11–I15) | dysarthria-tuned front-ends | **SUBSUMED + COMPUTE-BLOCKED** | encoder-invariance is established (SSL lifts accuracy not the D2 tail); several need GPU/download. No device rationale to spend here. |
| **J** (J17–J20) | alignment-aware matching | **SUBSUMED** by R1 | frame-trajectory DTW (J16, run as R1) is not-banked; smarter-warp variants attack the same central separability. |
| **K** (K21–K24) | decision layer, high-overlap | **SUBSUMED** by R3 | per-command / normalized thresholds are null at matched FAR. |
| **K25** | SPRT multi-attempt | **RE-SCOPED → W20** | genuinely distinct (task-level multi-turn, not single-shot D2); folded into the P5 abstain+confirm/multi-attempt experiment W20 in the follow-up plan. |
| **L** (L27–L30) | personalized speaker-security (other-speaker-same-word) | **DISTINCT AXIS — deferred** | this is the impostor=other-*speaker* wall (86.9%), a different sub-problem from the in-vocab-confusor D2. Out of scope for the D2 push; tracked separately. |

## Round-3 backlog (26 items) — disposition

| Item(s) | Disposition | Rationale |
|---|---|---|
| **N1** | **RUN** (this session) | band-900 stack — CONFIRMED UNREACHABLE. |
| N3–N5 | **SUBSUMED** | downstream of N1/N2; the stack does not reach band 900. |
| **P8–P10** | **SUBSUMED** by R2 | P-series backends = the killed P2 family. |
| **Q11–Q15** | **SUBSUMED / P5** | high-overlap decision variants → R3 null; multi-attempt → W20. |
| **R16–R20** | **RUN** as R3 | the R-series = score normalization + adaptive thresholds — null at matched FAR. |
| **S21, S23–S25** | **BLOCKED — simulator** | S22 fidelity gate failed (sim unfit); simulator-based dysarthric evidence is excluded by requirement. |
| **T26–T30** | **SUBSUMED / P5** | integration/product-framing → superseded by the P5 cluster (W20–W23). |

## Round-1 blocked (5 items)

| Item | Disposition | Rationale |
|---|---|---|
| C16 | **COMPUTE-BLOCKED** | GPU-gated; host is CPU-only. |
| C20, C22 | **CORPUS-BLOCKED** | need MSWC corpus (absent). |
| D23 | partial only | low marginal value given Round-4. |
| B12 | **no-headroom** | explicitly dominated. |

## Honest coverage statement (no silent truncation)

- **Executed:** the 3 highest-value untried attacks (P1/P2/P3 = R1/R2/R3) + the Round-3 primary DoD (N1),
  all on real TORGO with FAR-matched/held-out/cross-gender controls, + the male-frame extraction that
  unblocked them.
- **Not executed, by design:** the ~48 remaining deferred items are either (a) **subsumed** — members of the
  whitening/subspace/backend/score-norm/frame-DTW families now settled by a decisive negative (running them
  would be low-value churn, CLAUDE.md §7), (b) **corpus-blocked** (MSWC/UASpeech/EasyCall absent — see
  follow-up W25/W26), (c) **compute-blocked** (GPU), or (d) **simulator-excluded** (S22 unfit).
- **Re-scoped forward:** the genuinely distinct unrun ideas (SPRT multi-attempt K25/Q; speaker-security L;
  tail-direct and reframe levers) are pre-registered as the 26 W-series experiments in
  `docs/plans/2026-07/d2-wall-followup-experiments.md`.
