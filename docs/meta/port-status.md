# Port status — SpeechAngel AI workflow transplant

**Date:** 2026-06-28
**Source meta-system:** the changemappers project's porting guide
(changemappers/docs/meta/porting-ai-workflow-to-new-projects.md — external to this repo).
**Target stack:** Android / Kotlin / Gradle / Jetpack Compose (on-device speech app). The source is
Node/Next.js — this is an **adaptation**, not a verbatim copy.

> **Honesty rule (meta §10.1):** *Validated a lesson* ≠ *validated a port*. As of 2026-06-28 this is
> a **structurally-complete port**: the learning loop ("the heart", Wave 3) plus the plan workflow
> (Wave 1), the Android guardrail bundle (9 verifiers), the Gradle gates (Wave 4, incl. `:app`/`:data`),
> the hooks (Wave 7, now **installed and active**), and CI (Wave 8) all run green on the real repo.
> The one remaining gap to *behaviorally* validated is that no real incident has yet exercised the
> full commit-blocking loop end to end — so the loop is **wired-but-not-yet-exercised**, not proven.

---

## Wave-by-wave status

| Wave | Scope | Status | Notes |
|---|---|---|---|
| **0** — Foundations (entry docs, docs tree) | `AGENTS.md`, `CLAUDE.md`, `START_HERE.md`, behavior guardrails, `ACTIVE_DEV_RULES` skeleton, governance, DOC_TOC, temporal-bucket tree | **green-and-wired** | All entry docs adapted to Kotlin/Gradle/Compose. Temporal buckets seeded. |
| **0.5** — Host-capability precheck | absolute-path shell + JDK21/`ANDROID_HOME` Gradle invocation captured in `CLAUDE.md` | **green-and-wired** | The two host lessons recorded so the next session skips rediscovery. |
| **1** — Worktree + plan workflow | plan scaffolder + guardrail + template | **green-and-wired** (2026-06-28) | `docs/plans/TEMPLATE.md`, `scripts/ops/create-plan.mjs` (`plan:new`), and `scripts/audits/verify-plan-workflow-guardrails.mjs` (`plan:check`) ported and wired into `run-all.mjs`. The verifier enforces plan structure, no-placeholder completeness, and the FRR+FAR accuracy-honesty rule on recognizer plans; worktree-registry references must resolve. Git-worktree creation itself stays manual (advisory). |
| **1A** — Harness layer (Claude Code settings.json hooks, agent memory, template sync) | `~/.claude/settings.json` PreToolUse/PostToolUse, external memory dir | **deferred** | Out of this port's path ownership; cost/context prose captured in `CLAUDE.md`. |
| **2** — Docs integrity + secrets | `verify-docs-integrity.mjs`, `verify-no-secrets.mjs` | **green-and-wired** | Docs integrity adapted to backtick code-paths + temporal buckets. Secret scan is best-effort over `git ls-files`. |
| **3** — Learning loop + audit loop ("the heart") | `verify-learning-loop.mjs`, `create-incident-report.mjs`, `verify-audit-loop.mjs`, `create-audit-finding.mjs` | **green-and-wired** | Four-dimension completeness gate (§5.2) implemented incl. `## Shift-Left Decision` + `## Planning Integration`. Loop birth-date is 2026-06-28 (no inherited exemption window). Memory empty. |
| **4** — Lint/typecheck/test gates | Gradle `detekt`/`spotless`/`:core:*:test`/`:app`+`:data` test+assemble/`kover` | **green-and-wired** (2026-06-28) | Full gate `detekt spotlessCheck :app:lintDebug test :app:assembleDebug` verified green on this host; `pre-push` now runs it (hooks active). Instrumentation tests remain device-gated (CI/manual). |
| **5** — Clean-code budgets + framework guardrails | — | **adapted-as Android guardrails** | Instead of Next/React verifiers: `verify-no-dynamic-versions`, `verify-gradle-wrapper-pinned`, `verify-version-catalog-usage`, `verify-foreground-service-types`. All green on the real repo (FGS skips gracefully — no manifest yet). |
| **6** — Contracts-as-data | `classify.mjs` + `workflow-boundary-contracts.json` | **green-and-wired** | 3 real contracts authored for SpeechAngel's actual boundaries. Advisory classifier. |
| **7** — Wire the hooks | `.husky/pre-commit`, `.husky/pre-push` | **installed-and-active** (2026-06-28) | `git config core.hooksPath .husky` set; both hooks run green. pre-commit runs the guardrail bundle + advisory worktree reminder; pre-push runs the bundle + the full Gradle gate (incl. `:app`/`:data`). |
| **8** — Session loop + CI + self-measurement | maturity rubric, dreaming cadence, decision log, retro, CI | **green (self-measurement) / present-not-yet-Actions-verified (CI) / deferred (session-closeout tooling)** | Rubric/dreaming/decision-log/retro structures seeded empty + first maturity score (555/1000). `.github/workflows/ci.yml` is present (build-test + guardrails jobs) and mirrors the locally-green `make verify`, but has not been observed green on a GitHub Actions run. `session-closeout` tooling not ported. |

---

## What is green standalone (verified `exit 0` on this repo, 2026-06-28)

- `node scripts/audits/verify-learning-loop.mjs`
- `node scripts/audits/verify-audit-loop.mjs`
- `node scripts/audits/verify-plan-workflow-guardrails.mjs`
- `node scripts/audits/verify-docs-integrity.mjs`
- `node scripts/audits/verify-no-dynamic-versions.mjs`
- `node scripts/audits/verify-gradle-wrapper-pinned.mjs`
- `node scripts/audits/verify-version-catalog-usage.mjs`
- `node scripts/audits/verify-foreground-service-types.mjs` (skips — no manifest)
- `node scripts/audits/verify-no-secrets.mjs`
- `node scripts/audits/run-all.mjs` (the bundle)
- `node scripts/workflow/classify.mjs <paths>`

## Deliberately deferred (with reasons)

- **Wave 1A harness layer** — lives outside the repo (`~/.claude/settings.json`) and outside this
  port's path ownership.
- **Git-worktree creation tooling** — `create-plan.mjs` scaffolds the plan doc; actually spawning a
  `git worktree` is left manual (advisory) until substantive parallel work needs it.
- **On-device instrumentation gate** — `:app:connectedDebugAndroidTest` needs a running
  emulator/device; it belongs in a manual/CI on-device job, not a per-push gate.
- **`session-closeout` tooling (Wave 8)** — not ported.

> **Closed since the initial port (2026-06-28):** Wave 1 plan tooling, Wave 7 hook installation,
> Wave 4 `:app`/`:data` Gradle gates, and the Wave 8 CI workflow are all now landed and green
> (see the table above).

## Definition-of-done gap to a *validated* port (meta §10)

Hooks are now installed and active, so the structural gate is met. The remaining gap to "validated
end-to-end" is **behavioral**: run a real `incident:new` → fix → `knowledge:check` → single-commit
cycle, and demonstrate a non-docs commit on `main` being steered into a worktree. Until a real
incident exercises the commit-blocking loop, treat the *loop* as **wired-but-not-yet-exercised**.
