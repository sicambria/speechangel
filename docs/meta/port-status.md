# Port status — SpeechAngel AI workflow transplant

**Date:** 2026-06-28
**Source meta-system:** the changemappers project's porting guide
(changemappers/docs/meta/porting-ai-workflow-to-new-projects.md — external to this repo).
**Target stack:** Android / Kotlin / Gradle / Jetpack Compose (on-device speech app). The source is
Node/Next.js — this is an **adaptation**, not a verbatim copy.

> **Honesty rule (meta §10.1):** *Validated a lesson* ≠ *validated a port*. This is a **partial,
> stage-appropriate port**: the learning loop ("the heart", Wave 3) is landed and green standalone,
> the Android-specific guardrails are the real adaptation work and run green on the real repo, but
> several waves are deliberately deferred (below). It is **not** an end-to-end validated port:
> the §10 four-bullet gate is not met because the hooks are authored-not-installed and no incident
> has yet exercised the full commit-blocking loop.

---

## Wave-by-wave status

| Wave | Scope | Status | Notes |
|---|---|---|---|
| **0** — Foundations (entry docs, docs tree) | `AGENTS.md`, `CLAUDE.md`, `START_HERE.md`, behavior guardrails, `ACTIVE_DEV_RULES` skeleton, governance, DOC_TOC, temporal-bucket tree | **green-and-wired** | All entry docs adapted to Kotlin/Gradle/Compose. Temporal buckets seeded. |
| **0.5** — Host-capability precheck | absolute-path shell + JDK21/`ANDROID_HOME` Gradle invocation captured in `CLAUDE.md` | **green-and-wired** | The two host lessons recorded so the next session skips rediscovery. |
| **1** — Worktree + plan workflow | worktree tooling scripts | **deferred** | Plan/worktree *docs + dir tree* exist and the pre-commit guard is advisory; the `worktree:*` scripts (`verify-plan-workflow-guardrails`) were not ported. Discipline is advisory-only here. |
| **1A** — Harness layer (Claude Code settings.json hooks, agent memory, template sync) | `~/.claude/settings.json` PreToolUse/PostToolUse, external memory dir | **deferred** | Out of this port's path ownership; cost/context prose captured in `CLAUDE.md`. |
| **2** — Docs integrity + secrets | `verify-docs-integrity.mjs`, `verify-no-secrets.mjs` | **green-and-wired** | Docs integrity adapted to backtick code-paths + temporal buckets. Secret scan is best-effort over `git ls-files`. |
| **3** — Learning loop + audit loop ("the heart") | `verify-learning-loop.mjs`, `create-incident-report.mjs`, `verify-audit-loop.mjs`, `create-audit-finding.mjs` | **green-and-wired** | Four-dimension completeness gate (§5.2) implemented incl. `## Shift-Left Decision` + `## Planning Integration`. Loop birth-date is 2026-06-28 (no inherited exemption window). Memory empty. |
| **4** — Lint/typecheck/test gates | Gradle `detekt`/`spotless`/`:core:*:test`/`kover` | **partial** | The Gradle gates exist (owned by others); referenced in `pre-push` but not yet committed-active. |
| **5** — Clean-code budgets + framework guardrails | — | **adapted-as Android guardrails** | Instead of Next/React verifiers: `verify-no-dynamic-versions`, `verify-gradle-wrapper-pinned`, `verify-version-catalog-usage`, `verify-foreground-service-types`. All green on the real repo (FGS skips gracefully — no manifest yet). |
| **6** — Contracts-as-data | `classify.mjs` + `workflow-boundary-contracts.json` | **green-and-wired** | 3 real contracts authored for SpeechAngel's actual boundaries. Advisory classifier. |
| **7** — Wire the hooks | `.husky/pre-commit`, `.husky/pre-push` | **authored-not-installed** | Hook files written + executable; not installed (`git config core.hooksPath .husky` enables them — see `CLAUDE.md`). pre-push carries the JDK21 Gradle gate + a TODO for app/data assemble + instrumentation. |
| **8** — Session loop + CI + self-measurement | maturity rubric, dreaming cadence, decision log, retro | **green (self-measurement) / deferred (CI, session-closeout tooling)** | Rubric/dreaming/decision-log/retro structures seeded empty + first maturity score (555/1000). CI workflow and `session-closeout` tooling not ported. |

---

## What is green standalone (verified `exit 0` on this repo, 2026-06-28)

- `node scripts/audits/verify-learning-loop.mjs`
- `node scripts/audits/verify-audit-loop.mjs`
- `node scripts/audits/verify-docs-integrity.mjs`
- `node scripts/audits/verify-no-dynamic-versions.mjs`
- `node scripts/audits/verify-gradle-wrapper-pinned.mjs`
- `node scripts/audits/verify-version-catalog-usage.mjs`
- `node scripts/audits/verify-foreground-service-types.mjs` (skips — no manifest)
- `node scripts/audits/verify-no-secrets.mjs`
- `node scripts/audits/run-all.mjs` (the bundle)
- `node scripts/workflow/classify.mjs <paths>`

## Deliberately deferred (with reasons)

- **Wave 1 worktree tooling** — needs the `worktree:*` script family; advisory discipline is
  sufficient until substantive parallel work begins.
- **Wave 1A harness layer** — lives outside the repo (`~/.claude/settings.json`) and outside this
  port's path ownership.
- **Hook installation (Wave 7 activation)** — authored; installing is a one-liner left to the repo
  owner so the bootstrapping commit is not bricked.
- **CI workflow (Wave 8)** — the .github/ workflow tree is owned by others (outside this port's path ownership).
- **App/data Gradle gates** — `:app`/`:data` do not exist yet; the pre-push gate has a TODO to add
  their assemble + instrumentation tests once they land ("wire only what is green").

## Definition-of-done gap to a *validated* port (meta §10)

To upgrade from "partial" to "validated end-to-end": install the hooks, run a real
`incident:new` → fix → `knowledge:check` → single-commit cycle, and demonstrate a non-docs commit on
`main` being steered into a worktree. Until then this is honestly **partial**.
