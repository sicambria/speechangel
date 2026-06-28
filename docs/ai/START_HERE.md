# START HERE

The entry point for any AI agent (or human) working on SpeechAngel. Read this first, every session.

SpeechAngel is an **on-device, language-independent, user-trainable** Android voice-command app for
immobilized and speech-impaired users. It is **deterministic** (a fixed command→action table), runs
**always-on / hands-free**, and is built in Kotlin / Gradle / Jetpack Compose. The "what" lives in
`research/` — read it before touching matcher, persistence, accessibility, or Play-policy code.

<!-- BUG_RCA_DISCOVERY_GATE: ANY failure found ANY way triggers the Incident Protocol in
     AGENTS.md §4. Found incidentally is not an exemption. -->

---

## Source-of-truth order (read in this order)

1. `docs/ai/START_HERE.md` — this file.
2. `AGENTS.md` — operating rules + the 9-step Incident Protocol + the Gradle gates.
3. `docs/ai/AI_BEHAVIOR_GUARDRAILS.md` — the ~13 universal behavior rules.
4. `docs/ai/ACTIVE_DEV_RULES.md` — promoted technical rules (starts empty).
5. `research/README.md` and `research/04_build_and_reuse_plan.md` — what the app is + the build plan.
6. `docs/ROADMAP.md` — the trackable phase/wave roadmap.

---

## Session-start invariant

At the start of a session **and after every context compaction**:

1. Re-read this file and `AGENTS.md`.
2. `cat docs/errors/INDEX.md` — load existing known-error knowledge before doing anything.
3. Confirm the toolchain facts in `CLAUDE.md` (absolute-path shell; the JDK 21 / `ANDROID_HOME`
   Gradle invocation; only `core:*` builds today).

---

## Quick-task table

| I want to… | Do this |
|---|---|
| Understand what the app is | Read `research/README.md` then `research/04_build_and_reuse_plan.md` |
| Record a failure / bug | `node scripts/ops/create-incident-report.mjs --slug <s> --area <a> --trigger "<t>"`, then follow `AGENTS.md` §4 |
| Verify the learning loop is closed | `node scripts/audits/verify-learning-loop.mjs` (`knowledge:check`) |
| Record an audit finding | `node scripts/ops/create-audit-finding.mjs --slug <s> --area <a> --severity <sev>` |
| Run all guardrails | `node scripts/audits/run-all.mjs` (`guardrails:check`) |
| Check docs integrity | `node scripts/audits/verify-docs-integrity.mjs` (`docs:check`) |
| See which boundary a change touches | `node scripts/workflow/classify.mjs <changed-paths…>` (`classify`) |
| Run the core test gate | `JAVA_HOME=…21 ANDROID_HOME=… ./gradlew :core:model:test :core:dsp:test :core:matching:test :core:enrollment:test` (see `CLAUDE.md`) |
| Start substantive work | Open a plan under `docs/plans/2026-06/`, work in a worktree (`docs/plans/worktrees/`) |

---

## Plan types (worktree discipline)

- Active plans: `docs/plans/2026-06/`
- Completed plans: `docs/plans/done/2026-06/`
- Per-worktree plan state: `docs/plans/worktrees/`
- Executed RCA plans: `docs/errors/rca/rca-plan-done/2026-06/`

Substantive (non-docs) work goes in a plan inside a worktree, never directly on `main`.
