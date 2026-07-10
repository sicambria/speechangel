# Dysarthric Round-2 results — L26 diagnostic + G1 (pre-registered primary) + H6 upper bound

> **⚠️ SUPERSEDED IN PART (Round-3, 2026-07-10):** the G1 "directional positive, gate-able, pending
> UASpeech" verdict below **did NOT survive held-out real-male replication** — G1 is null on M01–M05
> (pooled −1.4pp, p=0.63) and is **not a speaker-general lever**. The female-*control* replication cited
> below was same-gender/same-corpus false confidence (→ rule EVAL-006). See
> `2026-07-10_dysarthric-round3-results.md`. The L26/H6 characterizations below still hold.

**2026-07-10.** Execution of the Round-2 plan (`2026-07-10_dysarthric-800-rescore-and-plan.md`) under
`/journey` discipline. Threat-model decision this session (user): **cohabitant-rejection is OUT OF SCOPE**
(mainstream-assistant model). That drops the 87% other-speaker-same-word wall and the L27/L29/K22-speaker/
L28-security series from the composite. The binding wall is now **in-vocab command confusion only**
(57.4% FRR@FAR≤5%, vocab-distinct, band 500).

**Honest deliverable framing (set before running, advisor-gated):** the only on-host dysarthric data is
**3 female TORGO speakers** (F01/F03/F04; no M tarball, UASpeech host-gated). "Replicate on a 2nd
dysarthric population before banking" is therefore *unsatisfiable on this host* — GSC is typical, so it
tests typical-generalization, not a disorder-specific effect. So this run **cannot bank a dysarthric 800**.
Its honest output is: **the diagnostic + ONE pre-registered primary lever run with full rigor + directional
evidence + a pre-registered UASpeech confirmation**. The remaining 26 experiments stay as next-iteration
hypotheses (running all 30 and headlining the winner would be selection-on-test, EVAL-003).

Harnesses: `l26_variance_decomp.py`, `g1_contraction.py`, `g1_confirm.py`, `g1_mechanism.py`,
`h6_vocab_ceiling.py`. Encoder: wavlm-large L15, mean-pooled, VAD-trimmed (fidelity: G1 raw baseline
55.3% reproduces the committed re-score 57.4% within subset variance — EVAL-004 gate passes).

---

## 1. L26 — the wall is within-word scatter, not between-word distance (diagnostic, banked characterization)

Per-speaker within-word vs nearest-between-word geometry (wavlm-large L15):

| set | dys fisher (betw_min/within) | dys within-word dist | dys rank-1 confusion | ctl fisher | ctl within |
|---|---|---|---|---|---|
| ALL commands | **1.04** | 0.037–0.048 | 20.5% | 2.28 | 0.013–0.022 |
| vocab-distinct≤25 | **1.17** | 0.037–0.054 | 15.6% | 4.02 | 0.014–0.020 |

- Dysarthric within-word scatter is **~2.5× control** (0.04–0.05 vs 0.013–0.022). Fisher ≈ 1.0 means a
  genuine dysarthric repeat sits about as far from its own word's centroid as from the nearest *other*
  word's — in-vocab confusion is geometrically near-unavoidable.
- Vocab-distinct selection lifts **control** fisher 2.28→4.02 but **dysarthric** only 1.04→1.17.
- The threshold-free rank-1 confusion floor is 15.6% (distinct), but the re-score's operating-point FRR is
  57.4% — so **~42pp is the FAR≤5% threshold** rejecting correctly-classified genuine utterances (confusors
  sit so close that a threshold rejecting 95% of them also rejects 42% of genuine repeats). ⇒ the lever must
  **contract within-word scatter**, not separate command centroids.

## 2. G1 — per-user within-word whitening (PRE-REGISTERED PRIMARY) → directional positive on dysarthric

Per-user linear transform fit on the user's own words (fold-held-out from the start, per the G3 leak
lesson), scoring cosine in the transformed space. Exploratory sweep (18 configs, `g1_contraction.py`) then
a **pre-registered** confirmation on ONE mid config chosen before seeing the winner (`zca, r=32, eps=0.1` —
deliberately not the maximal r=64), with paired McNemar at matched FAR (`g1_confirm.py`):

| population | raw FRR | zca (pre-reg) | Δ | McNemar (b=hurt, c=helped) | verdict |
|---|---|---|---|---|---|
| **TORGO dysarthric** (target) | 55.3% | **44.7%** (band 600) | **+10.6pp** | b=5 c=20 **p=0.004** | ✓ gate passed |
| TORGO typical control | 13.7% | 5.0% | +8.7pp | b=0 c=14 **p<0.001** | ✓ replicates (2nd TORGO pop) |
| **GSC typical** (independent corpus) | 6.2% | 12.1% | **−5.8pp** | b=55 c=2 **p<1e-13** | ✗ reverses on clean typical |

Exploratory upper end (NOT headlined, selection-on-test): `zca r=64` → dys 39.0% (−18.4pp), ctl 5.0%.

**Verdict: directional POSITIVE on the dysarthric target — the first lever this campaign has found that
moves the binding in-vocab wall** (57→45%, band 500→600, p=0.004, fold-held-out, fidelity-checked). It is
**scope-limited to non-typical speech** (the GSC reversal), which is a *scoping* result, not a refutation:
by pre-registration GSC (typical) cannot refute a disorder-specific effect.

**Gate (buildable, provably safe):** enable G1 only when measured within-word scatter ≥ ~0.03. Dysarthric =
0.044; all typical corpora = 0.016–0.023 → the gate turns G1 ON only in the dysarthric regime and OFF for
both typical corpora, correctly avoiding the GSC harm (at the cost of leaving the TORGO-control bonus on the
table — the safe trade). The gate rests on n=3 dys, which is exactly why UASpeech is the next step.

**Status: NOT banked — directional positive, pending the pre-registered UASpeech confirmation.**

### 2b. Mechanism (`g1_mechanism.py`) — the differentiator is corpus/channel-level, not per-user

Three candidate *per-speaker* gating mechanisms were tested and **all falsified**:

| population | within-word scatter | residual PR (structure) | multi-session? | G1 Δ |
|---|---|---|---|---|
| TORGO dys | 0.044 | 8.5 | mostly single | +10.6 ✓ |
| TORGO ctl | 0.017 | 15.5 | mostly single | +8.7 ✓ |
| GSC typical | 0.016 | **8.9** | single | −5.8 ✗ |

Scatter magnitude, cross-session nuisance, and residual effective-rank each fail to predict the sign
(GSC PR 8.9 ≈ dys PR 8.5, yet opposite sign; single-session speakers still benefit). The mechanism hunt was
**stopped at three** (a fourth per-speaker guess would be selection-on-mechanism). The signal they
collectively give: the differentiator is **corpus/channel-level** (TORGO close-mic controlled capture vs
GSC crowd-sourced) — recorded as the **open mechanistic question for the UASpeech round**. Note the
*deployment* gate (§2, scatter≥0.03) does not depend on resolving this — it is safe by construction.

## 3. H6 — vocabulary co-design ceiling for dysarthric (upper bound, characterization)

Achievable in-vocab D2 FRR@FAR≤5% vs vocabulary size N, random vs teach-time distinct set (committed
`held_out_d2` scorer):

| N | dys random | dys distinct | ctl random | ctl distinct |
|---|---|---|---|---|
| 5 | **26.6% (band 700)** | 35.5% | 9.6% | 0.0% |
| 8 | 40.1% | 45.1% | 12.2% | 3.5% |
| 12 | 48.7% | 49.4% | 14.4% | 10.7% |
| 20 | 51.1% | 56.3% | 17.2% | 13.4% |

Two findings:
1. **Distinctness co-design does NOT help dysarthric** (distinct ≥ random FRR at every N — it slightly
   *hurts*), while it strongly helps typical (ctl N=5: 0.0% vs 9.6%). Confirms L26: the dys wall is
   within-word scatter, not between-word distance, so max-min-centroid selection buys nothing. ⇒ H7-style
   confusable-pair remediation is **not** a dysarthric lever. (Banked negative.)
2. **Vocabulary size IS a real, honest lever:** a small ~5-command set reaches **band 700 (26.6%)** for
   dysarthric users vs band 500–600 at N=20–25 — fewer confusors, no tricks. Deployable today.

---

## What is banked / directional / refuted

- **Banked (characterization):** the dysarthric in-vocab wall is **within-word scatter (~2.5× control,
  fisher≈1.0)**, and ~42pp of the operating-point FRR is the FAR threshold rejecting correctly-classified
  genuine repeats (L26). Vocabulary *distinctness* co-design does not help dysarthric (H6). Vocabulary
  *size* does: N≈5 → band 700 (H6, deployable).
- **Directional positive, NOT banked:** **G1 per-user within-word whitening** → dys in-vocab D2 −10.6pp
  (57→45%, band 500→600), p=0.004, fold-held-out, replicated on TORGO control; scope-limited to non-typical
  (GSC reversal); gate-able on within-word scatter ≥0.03. **Next step = pre-registered UASpeech
  confirmation** (the disorder-specific 2nd population this host lacks).
- **Refuted:** the "G1 is scatter-gated / session-gated / structure-gated" per-speaker mechanisms (all
  three falsified — differentiator is corpus-level). Earlier: G3 fixed nuisance-subspace projection (leak,
  §2 of the plan doc).

## Next levers (pre-registered hypotheses for the next iteration — NOT run this session)

1. **UASpeech confirmation of G1** (blocks the bank; disorder-specific 2nd population + resolves the
   corpus/channel mechanism question). Highest priority.
2. **G1 × small-vocab stacking** — do the within-word whitening (§2) and the N≈5 vocabulary (§3) compound?
   Both attack the same wall from different sides; measure jointly at matched FAR.
3. **J16 frame-level SSL-DTW** — a genuinely *different* representation (alignment-tolerant) that could be
   the *generalizing* lever G1 is not; test with the same one-config-pre-registered + independent-corpus
   discipline (TORGO frames cached; needs GSC frames for the typical check).
4. **G2 per-user Mahalanobis** — the learned-metric successor to G1's fixed whitening (gate: beat G1 by ≥3pp).

> **Honest bottom line:** cohabitant-scope-out + this run leaves the composite bound by dysarthric in-vocab
> confusion. G1 is the first real lever on it (directional, gate-able), and small-vocab reaches band 700
> honestly — but a *banked* dysarthric 800 is not achievable on n=3 TORGO. It needs the UASpeech confirmation,
> which is now the pre-registered critical-path step.
