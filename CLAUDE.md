# CLAUDE.md — Claude Code operational patterns for SpeechAngel

Read `AGENTS.md` first (operating rules + Incident Protocol) and `docs/ai/START_HERE.md`
(source-of-truth order). This file holds the **Claude-Code-specific** patterns: the exact working
toolchain invocations, the captured host-capability lessons, and cost/context discipline.

---

## 1. Captured host-capability lessons (meta §0.5 — "probe, don't assume; then record it")

The single most common reason a task "can't be verified the first time" is a **host-capability gap
mistaken for a hard blocker**. Both lessons below were captured the hard way on this host — they are
recorded here so the next session never rediscovers them.

### 1.1 The shell only resolves ABSOLUTE binary paths

Bare builtins (`echo`, `pwd`, `ls`, `cat`) **fail with exit 1** in this environment's non-login
agent shell. Always use absolute paths:

- Node: `/home/arsvivendi/.nvm/versions/node/v24.16.0/bin/node`
- `/bin/ls`, `/bin/cat`, `/bin/mkdir`, `/usr/bin/find` (used sparingly — prefer the Read/Write tools).

Run the workflow gates like this:

```sh
/home/arsvivendi/.nvm/versions/node/v24.16.0/bin/node scripts/audits/run-all.mjs
```

### 1.2 The ONE working Gradle invocation (JDK 21 + Android SDK)

Gradle needs JDK 21 and `ANDROID_HOME`. The invocation that works:

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
ANDROID_HOME=/home/arsvivendi/Android/Sdk \
/home/arsvivendi/git/speechangel/gradlew -p /home/arsvivendi/git/speechangel <tasks>
```

**Only the `core:*` modules build today** — `:app` and `:data` are being scaffolded in parallel and
are commented out in `settings.gradle.kts`. **Do not run full builds.** The green gate is the four
core test tasks: `:core:model:test :core:dsp:test :core:matching:test :core:enrollment:test`.
You may run a single `:core:matching:test` to confirm something, but nothing heavier.

> "Verified" honestly (meta §0.5): a change is verified only when the relevant `scripts/audits/*.mjs`
> gate **and** the affected `:core:*` test task have actually run green — not "would pass".

---

## 2. The workflow scripts are dependency-free Node ESM

Every script under `scripts/` is a `.mjs` ESM module that runs on node v24 with **no external
deps** (no `npm install` needed). Run any of them standalone:

```sh
/home/arsvivendi/.nvm/versions/node/v24.16.0/bin/node scripts/audits/verify-docs-integrity.mjs
```

`package.json` wires friendly aliases (`knowledge:check`, `audit:check`, `docs:check`,
`guardrails:check`, `incident:new`, `audit:index`, `classify`), but the scripts never require the
npm layer to run.

---

## 3. Enabling the git hooks

The hooks live in `.husky/` as plain executable shell scripts. **Husky is not installed** (no
`npm install` is run for this workflow). To enable them on a host that uses them, point git at the
directory:

```sh
git config core.hooksPath .husky
```

- `.husky/pre-commit` runs `node scripts/audits/run-all.mjs` and emits the advisory
  "non-docs on `main` should be in a worktree/plan" warning.
- `.husky/pre-push` runs the guardrail bundle plus the Gradle quality + core-test gate with the
  JDK 21 / `ANDROID_HOME` env. App/data assemble + instrumentation tests are a documented TODO
  (Wave 7 — "wire only what is green") that lands once those modules exist.

---

## 4. Cost & context discipline (advisory)

- **Route read-only fan-out to a cheaper subagent.** Use the `Explore` agent for "where does X
  live across the modules" sweeps; keep the file dumps out of the main context.
- **Prefer Read on a known path over a broad search.** When the file is known, read the relevant
  slice, not the whole tree.
- **Compact / clear at thresholds.** `/compact` when the transcript grows past usefulness; `/clear`
  between unrelated tasks. Re-read `AGENTS.md` + `START_HERE.md` after a compaction (the session-start
  invariant in `START_HERE.md`).
- **One worktree / one dev concern at a time.** Stray parallel state is a cost and a correctness risk.
- This discipline is **advisory** by design — there is no token-budget gate yet. It is a promotion
  candidate if cost overruns recur.
