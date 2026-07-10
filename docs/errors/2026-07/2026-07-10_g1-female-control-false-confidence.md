# G1's female-control "replication" was false confidence — refuted by real male speakers

**2026-07-10.** Round-2 identified G1 (per-user within-word whitening) as the first lever to move the
dysarthric in-vocab wall: female TORGO in-vocab D2 −10.6pp (55.3→44.7%, McNemar p=0.004), which *also*
replicated on female **control** (−8.7pp, p<0.001). It was written up as "directional positive, gate-able,
pending UASpeech." Round-3 acquired real **male** dysarthric speakers (TORGO M01–M05) and applied the frozen
Round-2 config to them as a held-out 2nd population: **G1 is null on male** (pooled −1.4pp, p=0.63; per
speaker 1 up / 1 down / 3 flat). The lever does not generalize across gender.

- **Trigger:** Round-3 held-out male replication (P7) returned null (p=0.63) for a lever banked-adjacent as
  a Round-2 "directional positive"; advisor review confirmed the female-control "replication" was false
  confidence.
- **Automation Links:** `scripts/eval/ssl_frontend_spike/p7_male_g1_confirm.py`,
  `docs/ai/ACTIVE_DEV_RULES.md` (EVAL-006).

## Summary
A significant, replicated-looking personalization lever was retracted when tested on a genuinely
out-of-demographic population. The Round-2 "replication" (female control) shared gender + corpus + channel
with the female dysarthric target, so it corroborated nothing the target didn't already show.

## Root Cause
Treating a **same-demographic, same-corpus** control as an independent 2nd population. G1 is per-user, but
its *benefit* turned out to be conditional on axes (gender/pitch-structure of the within-word covariance, or
the female-TORGO recording pool) that both the female dysarthric and female control share. The control could
only ever confirm "works on female TORGO," never "generalizes." The GSC-typical reversal already hinted G1
was scope-limited; the male-null pinned it as non-generalizing across the *dysarthric* population itself.

## Rerun Analysis
The cheap test that would have flagged it earlier: any cross-demographic held-out set. Real male TORGO was
freely downloadable the whole time (`M.tar.bz2`, HTTP 200) — the n=3 "blocker" was a not-yet-fetched asset,
not a hard wall (cf. host-capability lesson §1.4). Fetching it first would have prevented the Round-2
"directional positive, pending UASpeech" framing from hardening.

## Prevention
Rule **EVAL-006**: same-demographic control replication ≠ generalization; a personalization lever needs
cross-demographic (here cross-gender) held-out confirmation before banking. Standing bar for dysarthric
levers: F↔M cross-gender held-out.

## Guardrail Updates
`scripts/eval/ssl_frontend_spike/p7_male_g1_confirm.py` — frozen-config cross-gender held-out replication
with paired McNemar; the reference harness for the EVAL-006 bar. `docs/ai/ACTIVE_DEV_RULES.md` gains
EVAL-006.

## Planning Integration
Rule **EVAL-006** (`docs/ai/ACTIVE_DEV_RULES.md`) is the concrete artifact produced. The Round-3 plan
(`docs/testing/2026-07-10_dysarthric-over900-plan.md`) Definition of Done gains a standing bank bar: **F↔M
cross-gender held-out** confirmation before any dysarthric-lever bank. Round-4 leads with the R-series
(adaptive thresholds / T-norm), which attacks the operating-point threshold gap without requiring the
representation to generalize across speakers.

## Shift-Left Decision
**Decision: add.** Added rule **EVAL-006** to `docs/ai/ACTIVE_DEV_RULES.md` (same-demographic control
replication ≠ generalization; require cross-demographic held-out before banking a personalization lever),
shifting the check to bank-time. Corollary applied: acquire every freely-available population (here TORGO
male, one download away) *before* framing a single-population result as "directional pending an external
corpus" — the UASpeech caveat had masked a cheaper real 2nd population.

## Automation Follow-Up
None mechanized (research harness, not product code). The advisory reference is `p7_male_g1_confirm.py`;
future dysarthric-lever reports should include its cross-gender table before a bank line.
