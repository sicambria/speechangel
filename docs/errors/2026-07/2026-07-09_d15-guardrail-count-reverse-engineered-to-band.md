# Incident — a guardrail-coverage count reverse-engineered to clear the target band

**Date:** 2026-07-09 · **Area:** SOTA domain 15 (guardrail coverage) — `SotaScorecard` +
`scripts/audits/verify-sota-measurement.mjs` · **Severity:** methodological (caught by advisor review
before commit; no wrong number reached a committed scorecard).
- **Trigger:** Advisor review of the D15→800 bank flagged that no consistent criterion yields exactly 2
  hard-gated rules — the count had been chosen to clear 800, then justified.
- **Automation Links:** `scripts/audits/verify-sota-measurement.mjs`,
  `core/eval/src/main/kotlin/com/speechangel/core/eval/SotaScorecard.kt`.

## Summary

While banking SOTA domain 15 (count of EVAL-001..005 rules promoted to hard gates) at band **800**
(threshold = 2/5), the first implementation set the count to **2** by relabeling EVAL-003 and EVAL-004
from `advisory` to `hard` and pointing at the **pre-existing citation checks** in
`verify-sota-measurement.mjs`. The reasoning in-session was explicit: "promote exactly 2 … giving band
800" and "leave 002/005 advisory so the count is exactly 2." Advisor review produced the knockdown:
`verify-sota-measurement.mjs` **check 1** tests `held-out ∧ pre-registered ∧ replication`
(EVAL-002 ∧ 003 ∧ 005) as a **single atomic condition** — a numerical-claim doc either cites all three
or is blocked. So EVAL-003 cannot be "hard-gated by check 1" without EVAL-002 and EVAL-005 being
hard-gated by the *identical* condition. Under any uniform criterion the honest count is 0, 1, 3, or 4 —
**2 is the one value a consistent rule cannot produce.** The count had been reverse-engineered to the
target band. The fix: adopt a uniform criterion first (a rule counts iff a blocking check enforces a
rule-specific **substance artifact** beyond citation), then **build** two genuine substance gates
(check 3: a delta claim needs a reproduced baseline *number*; check 4: an adjudicated result needs an
explicit *banked/NOT-banked verdict*), verify both bite on fixtures, and let the count be "how many
substance gates exist" = 2. The band is unchanged (800) but now *earned*, not fitted.

## Root Cause

Selection-on-target, one meta-level up — the exact anti-pattern **EVAL-003** exists to prevent
(pre-register the hypothesis; don't mine the result you want), committed **inside the very domain that
measures measurement discipline**. The number (2) was fixed first (because it clears 800), and a
plausible-sounding justification ("conservative floor"; "002/005 left advisory") was assembled around
it. The self-checks could not catch it: `make guardrails` was green and the hermetic unit test validated
the *parser*, but the parser's input is the set of `**Gate:** hard` labels — the thing being set. A green
gate on an input you author is not evidence the input is right.

## Rerun Analysis

- What would have caught it earlier: stating the promotion criterion **before** computing the count and
  applying it to all five rules — the atomic-bundle structure of check 1 makes the "2 from citation"
  contradiction immediate. This is the advisor's rule: *pick the criterion independent of the band, apply
  to all N, report where it lands.*
- The advisor caught it because they read the actual verifier logic (check 1 is one `∧`) rather than the
  narrative. Primary-source verification of the gate beat the plausible story.
- Cost: ~1 review cycle + a rework of the two checks and the ladder doc (~30 min). No committed artifact
  was wrong — the wrong version never left the working tree.

## Prevention

**Rule (promoted to WORKFLOW-001 in `docs/ai/ACTIVE_DEV_RULES.md`): pick the measurement criterion before
you look at the target, apply it uniformly to every item, and report where it lands — even if that is short
of the band.** A metric
whose value cannot be *derived from its stated criterion without knowing the desired result* is not a
measurement. For guardrail-coverage specifically: a rule counts only if a blocking check enforces a
rule-specific **substance artifact** (a required token/number), proven to **bite on a fixture** — never a
citation/keyword check, and never a bare `hard` label.

## Guardrail Updates

`scripts/audits/verify-sota-measurement.mjs` — **check 3** strengthened to require a reproduced baseline
*number* (not just the word "fidelity") for EVAL-004; **check 4** added to require an explicit
`banked / NOT banked` verdict on any doc reporting a McNemar / rel-reduction result for EVAL-003. Both
were verified to block fixtures (`_fixtureA_no_verdict.md` → check 4; `_fixtureB_no_number.md` → check 3)
while check 1 stayed silent — proving they gate substance, not citation. `SotaScorecard.guardrailDomain()`
/ `countHardGatedEvalRules()` count the resulting `**Gate:** hard` EVAL lines (domain 15 = 2/5 → 800),
excluded from the wall-dominated composite (structural). The promotion ladder + uniform criterion are
documented in `docs/ai/ACTIVE_DEV_RULES.md`.

## Planning Integration

`docs/plans/2026-07/sota-800-push.md` Domain 15 records the E15-06/07/08 path (substance gates for
EVAL-002/005/001) to bands 900+; each such promotion must build a substance gate that bites, not relabel.
The plan's honesty contract (rule 1) already forbids proxies earning green bands; this incident extends
that discipline to **structural** metrics: a coverage count must follow a target-independent criterion.

## Shift-Left Decision

**Decision: add.** Added **WORKFLOW-001** ("fix the measurement criterion before you look at the target")
to `docs/ai/ACTIVE_DEV_RULES.md`, shifting the discipline left to **design-time**: the promotion criterion
must be written down before the count is computed. The advisor gate (call before banking) is the backstop
that caught it here; WORKFLOW-001 is the durable prevention, so the next coverage/count bank states its
criterion first by habit.

## Automation Follow-Up

1. **Auto-measure trusts the label, not the gate's existence.** `countHardGatedEvalRules` counts
   `**Gate:** hard` lines but does not verify the named check exists in the verifier — a future edit could
   label a rule `hard` with no gate and inflate the count. Cheap hardening: have the counter also require
   the named check (e.g. `check N`) to be present in `verify-sota-measurement.mjs`. **Known limitation,
   tracked.**
2. **Substance-gate regexes can false-fire on legit future docs.** check 4 keys on `\bbanked\b`; check 3
   on a number within ~80 chars of "reproduc"/"baseline". Both scan only *changed* files, so blast radius
   is small, but the next author editing a testing doc should expect them. **Known limitation, tracked.**
