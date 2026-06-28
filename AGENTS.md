# AGENTS.md — Operating rules for AI agents on SpeechAngel

SpeechAngel is an **on-device, language-independent, user-trainable** Android voice-command
app (Kotlin / Gradle / Jetpack Compose) for immobilized and speech-impaired users. It must run
**always-on and hands-free**, and it must stay a **deterministic command→action tool — never an
autonomous LLM agent** (this is a Play-policy make-or-break line; see `research/04_build_and_reuse_plan.md` §7).

This file is the operating contract for any agent (Claude Code, or otherwise) that edits this repo.
Read it together with `docs/ai/START_HERE.md` (source-of-truth order) and
`docs/ai/AI_BEHAVIOR_GUARDRAILS.md` (the agent-neutral behavior rules).

---

## 0. The one idea

> **Failures are structured data; structured data becomes guardrails; guardrails block the next
> commit if the loop is left open.**

```
incident → docs/errors entry → ACTIVE_DEV_RULES rule
        → docs/ai/workflow-boundary-contracts.json contract (advisory)
        → scripts/audits/<verifier>.mjs (hard gate via husky)
```

A rule earns promotion up that ladder only after repeated low-false-positive catches.

---

## 1. Source-of-truth order

1. `docs/ai/START_HERE.md` — entry map + quick-task table + session-start invariant.
2. `AGENTS.md` (this file) — operating rules + the Incident Protocol.
3. `docs/ai/AI_BEHAVIOR_GUARDRAILS.md` — the ~12 universal behavior rules.
4. `docs/ai/ACTIVE_DEV_RULES.md` — promoted, numbered technical rules (starts empty).
5. `research/*.md` — what the app is and its hard constraints. The matcher, persistence,
   accessibility, and Play-policy boundaries all come from here.

---

## 2. The build & the gates (the real Gradle invocation)

The shell in this environment only resolves **absolute** binary paths and Gradle needs JDK 21 +
the Android SDK. The single working invocation is:

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
ANDROID_HOME=/home/arsvivendi/Android/Sdk \
/home/arsvivendi/git/speechangel/gradlew -p /home/arsvivendi/git/speechangel <tasks>
```

Only the `core:*` modules build today (`:app` and `:data` are scaffolded in parallel — see
`settings.gradle.kts`). Do **not** run full builds. The green core test gate is:

```
:core:model:test  :core:dsp:test  :core:matching:test  :core:enrollment:test
```

Quality gates: `detekt` (config `config/detekt/detekt.yml`), `spotless` / `spotlessCheck`
(ktlint), `kover` coverage (≥70 % on core logic).

Workflow gates (Node, dependency-free, run with the absolute node path
`/home/arsvivendi/.nvm/versions/node/v24.16.0/bin/node`):

| Gate | Script | npm script |
|---|---|---|
| All guardrails | `scripts/audits/run-all.mjs` | `guardrails:check` |
| Learning loop | `scripts/audits/verify-learning-loop.mjs` | `knowledge:check` |
| Audit loop | `scripts/audits/verify-audit-loop.mjs` | `audit:check` |
| Docs integrity | `scripts/audits/verify-docs-integrity.mjs` | `docs:check` |
| No dynamic versions | `scripts/audits/verify-no-dynamic-versions.mjs` | (in `guardrails:check`) |
| Gradle wrapper pinned | `scripts/audits/verify-gradle-wrapper-pinned.mjs` | (in `guardrails:check`) |
| Version-catalog usage | `scripts/audits/verify-version-catalog-usage.mjs` | (in `guardrails:check`) |
| Foreground-service types | `scripts/audits/verify-foreground-service-types.mjs` | (in `guardrails:check`) |
| No secrets | `scripts/audits/verify-no-secrets.mjs` | (in `guardrails:check`) |
| Classify a change | `scripts/workflow/classify.mjs` | `classify` |

---

## 3. Plan & worktree discipline

Substantive (non-docs) development is done **inside a plan, inside a worktree** — not directly on
`main`. The pre-commit hook carries an **advisory** "non-docs changes on `main` should be in a
worktree/plan" warning (advisory only at this stage of the port — see `docs/meta/port-status.md`).

Plan types live under `docs/plans/`:

- `docs/plans/2026-06/` — active plans for the current month (temporal `YYYY-MM` bucket).
- `docs/plans/done/2026-06/` — completed plans.
- `docs/plans/worktrees/` — per-worktree plan state.

RCA plans, once executed, are archived under `docs/errors/rca/rca-plan-done/2026-06/`.

A plan names: the goal, the affected modules, the Definition of Done (tests + the relevant
`scripts/audits/*` gate), and the worktree branch.

---

## 4. Incident & Error Protocol (the 9 steps)

<!-- BUG_RCA_DISCOVERY_GATE: ANY failure found ANY way — a bug, a build break, a red gate, a
     console error, an incidental observation, or a PLANNING-PHASE DESIGN ERROR — triggers this
     protocol. "Found incidentally" and "caught during plan review before any code was written"
     are NOT exemptions. A design error that would have caused a silent regression if not caught
     is just as incident-worthy as a runtime failure — it tells you your design process has a gap.
     Do not silently fix-and-move-on in either case. -->

1. **Stop & read existing knowledge.** `cat docs/errors/INDEX.md` — has this class been seen before?
2. **Classify the failure.** Run `node scripts/workflow/classify.mjs <changed-paths>` to surface the
   boundary contracts the change touches.
3. **Root-cause it.** Find *why*, not just *where*. Scan the codebase for the same failure class
   elsewhere (e.g. another module hardcoding a dependency coordinate, another manifest missing a
   foreground-service type).
4. **Scaffold the incident note.** `node scripts/ops/create-incident-report.mjs --slug <slug>
   --area <area> --trigger "<what triggered it>"` writes `docs/errors/2026-06/<date>_<slug>.md`
   with every required section.
5. **Fix RED→GREEN.** Write the failing test first where it applies, then the fix.
6. **Close the loop in the note.** Fill `## Root Cause`, `## Prevention`, `## Guardrail Updates`
   (cite real repo files), `## Planning Integration` (name a concrete plan/DoD/rule),
   `## Shift-Left Decision` (an explicit `add` / `update` / `skip`-with-reason for tests **and** a
   guardrail). No surviving template placeholders.
7. **Regenerate & verify the index.** `node scripts/audits/verify-learning-loop.mjs` regenerates
   `docs/errors/INDEX.md` and **blocks** if the loop is open.
8. **Single commit.** Fix + tests + incident note + rule updates land together.
9. **Promote** when the class recurs with low false positives: known-error → `ACTIVE_DEV_RULES`
   rule → `workflow-boundary-contracts.json` contract → a `scripts/audits/<verifier>.mjs` hard gate.

---

## 5. The non-negotiable product gates (carry these into every plan)

These come from `research/04_build_and_reuse_plan.md` §7 and are first-class guardrail subjects:

1. **Deterministic, not an autonomous LLM agent** (`isAccessibilityTool="true"` + fixed
   command→action table).
2. **Accuracy reported as FRR + FAR/hour**, never a bare "99 %".
3. **On-device enrollment is the differentiator** — never regress to a language-dependent STT core.
4. **Robustness = effortless re-enrollment + multi-template + confirmation-gated adaptation.**
5. **First-time setup needs a caregiver** (un-automatable grants) — design for it honestly.

---

## 6. Reproducibility hard rules (Android/Gradle, gate-enforced)

- **No dynamic dependency versions** anywhere (`+`, `latest.release`, `-SNAPSHOT`).
- **Gradle wrapper pinned** to an explicit distribution; `validateDistributionUrl=true`.
- **All dependencies go through the version catalog** (`gradle/libs.versions.toml`) — never a
  hardcoded `"group:artifact:version"` coordinate in a module `build.gradle.kts`.
- **A microphone foreground service** must declare `foregroundServiceType="microphone"` and the
  `FOREGROUND_SERVICE_MICROPHONE` permission in its `AndroidManifest.xml`.
- **No secrets** in tracked files (keystores, PEM keys, API tokens).
