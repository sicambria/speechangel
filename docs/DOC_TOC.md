# Documentation Table of Contents

The index of standing documentation. Paths are backtick code-paths (resolve from the repo root) per
`docs/standards/documentation-governance.md` — never relative markdown links.

## Entry / operating

- `docs/ai/START_HERE.md` — session entry point, source-of-truth order, quick-task table.
- `AGENTS.md` — operating rules, the 9-step Incident Protocol, the Gradle gates.
- `CLAUDE.md` — Claude Code operational patterns, toolchain invocations, cost discipline.
- `docs/ai/AI_BEHAVIOR_GUARDRAILS.md` — the universal agent-neutral behavior rules.
- `docs/ai/ACTIVE_DEV_RULES.md` — promoted technical rules (starts empty).

## Build & environment

- `docs/DEPENDENCIES.md` — full host/SDK/emulator/KVM dependency manifest (build tier + run tier).

## Standards

- `docs/standards/documentation-governance.md` — temporal buckets + link-safety.
- `docs/standards/ai-framework-maturity-standard.md` — the 10-dimension `/1000` maturity rubric.

## Planning & roadmap

- `docs/ROADMAP.md` — phased roadmap (Phase 0 spike → MVP → persistence/policy → delight).
- `docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md` — **current** score (480/1000, early-alpha): path to SOTA FRR/FAR + real-life factor scorecard + where-SOTA/where-not.
- `docs/product/2026-07-06_product-maturity-scorecard.md` — *superseded* pre-measurement scorecard (442/1000); retained for methodology + gap register.
- `docs/plans/TEMPLATE.md` — canonical plan template (scaffold via `scripts/ops/create-plan.mjs`).
- `docs/plans/2026-06/` — active plans.
- `docs/plans/done/2026-06/` — completed plans.
- `docs/plans/worktrees/` — per-worktree plan state.

## Learning loop / errors

- `docs/errors/INDEX.md` — generated index of incidents.
- `docs/errors/2026-06/` — incident notes (current month).
- `docs/errors/rca/rca-plan-done/2026-06/` — executed RCA plans.

## Audits

- `docs/audits/INDEX.md` — generated index of audit findings.
- `docs/audits/findings/2026-06/` — audit findings (current month).

## Testing

- `docs/testing/strategy.md` — layered test strategy.

## Workflow / contracts

- `docs/ai/workflow-boundary-contracts.json` — contracts-as-data (boundary classifier input).
- `docs/ai/ai-decision-log.md` — append-only autonomous-decision log (starts empty).

## Self-measurement / meta

- `docs/ai/retro/2026-06/2026-06.md` — monthly retrospective.
- `docs/meta/dreaming/` — meta-scan reports (cadence).
- `docs/meta/port-status.md` — honest wave-by-wave port status.
