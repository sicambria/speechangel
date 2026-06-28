# AI Framework Maturity Standard

A reproducible `/1000` score for "how mature is the AI-assisted development framework in this repo?"
Ten dimensions, each scored **Absent (0) → Documented (≈50) → Enforced (100)**, with partial scores
allowed. Re-score on a cadence (alongside the monthly retro) so "are we mature?" is a number, not a
vibe. The score drives the **promotion decision**: which dimension to push from Documented to
Enforced next.

> **Scoring discipline (meta §5.1):** score from *this repo's* real evidence, never copy another
> project's score. **Enforced** means a gate actually blocks (a wired-and-green verifier in an
> active hook/CI). A verifier that runs green standalone but whose hook is **authored-but-not-
> installed** is *Documented+*, not Enforced — that is the honest state of this freshly-transplanted
> port (see `docs/meta/port-status.md`).

---

## Levels

| Level | Score | Meaning |
|---|---|---|
| **Absent** | 0 | No artifact, no convention. |
| **Documented** | ~50 | A written standard/convention exists; adherence is manual. |
| **Documented+** | ~60–75 | A verifier exists and exits 0 standalone, but no active hook/CI blocks on it yet. |
| **Enforced** | 100 | A gate actively blocks the commit/push/CI on violation. |

---

## Current score — 2026-06-28 (first transplant scoring)

| # | Dimension | Level | Score | Evidence |
|---|---|---|---|---|
| 1 | Agent operating rules / behavior guardrails | Documented | 50 | `AGENTS.md`, `docs/ai/AI_BEHAVIOR_GUARDRAILS.md`, `docs/ai/START_HERE.md` exist; behavioral, not gate-enforceable. |
| 2 | Learning loop (incident → knowledge gate) | Documented+ | 70 | `scripts/audits/verify-learning-loop.mjs` + `scripts/ops/create-incident-report.mjs` green standalone; memory empty; hook authored-not-installed. |
| 3 | Audit loop | Documented+ | 65 | `scripts/audits/verify-audit-loop.mjs` + `scripts/ops/create-audit-finding.mjs` green standalone; no findings yet. |
| 4 | Docs integrity / governance | Documented+ | 70 | `scripts/audits/verify-docs-integrity.mjs` + `docs/standards/documentation-governance.md`; temporal buckets seeded. |
| 5 | Reproducibility guardrails (versions/wrapper/catalog) | Documented+ | 70 | `verify-no-dynamic-versions.mjs`, `verify-gradle-wrapper-pinned.mjs`, `verify-version-catalog-usage.mjs` green on the real repo. |
| 6 | Android platform guardrails (FGS / secrets) | Documented | 50 | `verify-foreground-service-types.mjs` (skips — no manifest yet), `verify-no-secrets.mjs` (best-effort). Will harden when `:app` lands. |
| 7 | Plan / worktree discipline | Documented | 35 | Docs + dir tree present; pre-commit guard is **advisory only**; no worktree tooling ported (Wave 1 deferred). |
| 8 | Contracts-as-data (shift-left classifier) | Documented+ | 55 | `scripts/workflow/classify.mjs` + `docs/ai/workflow-boundary-contracts.json` (3 real contracts); advisory, not blocking. |
| 9 | Test strategy & gates | Documented | 45 | `docs/testing/strategy.md`; Gradle `:core:*:test`/detekt/spotless/kover exist but are not yet wired as committed-active gates. |
| 10 | Self-measurement (rubric / dreaming / decision log) | Documented | 45 | This rubric + `docs/meta/dreaming/` + `docs/ai/ai-decision-log.md` exist, started empty; cadence not yet run. |

**Total: 555 / 1000.**

Honest read: the framework's *structure* is transplanted and the guardrail verifiers run green
standalone, but the enforcing hooks are authored-not-installed and the memory is empty. Maturity will
climb as (a) hooks/CI go active, (b) `:app`/`:data` land and the Android guardrails harden, and
(c) real incidents fill the loop. Lowest-hanging promotion: install the hooks (lifts #2–#5 toward
Enforced) and port the worktree tooling (#7).

---

## Re-scoring cadence

Re-score monthly with the retro (`docs/ai/retro/2026-06/2026-06.md`). Record the new total + the one
dimension you chose to promote and why. The delta over time is the maturity trend.
