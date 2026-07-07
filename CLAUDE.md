# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

All six modules (`:core:*`, `:data`, `:app`) are enabled in `settings.gradle.kts`.
`:app:assembleDebug` is **verified green** on this host (builds in ~4 s from cache).
Default to the four core test tasks as the fast gate:

```
:core:model:test  :core:dsp:test  :core:matching:test  :core:enrollment:test
```

Run `:app:assembleDebug` / `:data` tasks when the task genuinely needs them.

See `docs/DEPENDENCIES.md` for the full host/SDK/emulator dependency manifest and
`scripts/setup/install-deps.sh` to provision the run tier.

> "Verified" honestly (meta §0.5): a change is verified only when the relevant `scripts/audits/*.mjs`
> gate **and** the affected `:core:*` test task have actually run green — not "would pass".

### 1.3 Verifying "did background work close?" — trust the harness list, not a hand-written `pgrep`

Captured the hard way: after a long spike I told the user "all shells closed properly" based on a
`pgrep` pattern (`in_regime|inregime_paired|ssl_frontend`) — but the still-live job ran `sweep_ssl.py`,
which the pattern never matched. A hand-written process filter only covers the script names you *remember*,
so it produces confident-but-wrong "all clear" answers. Concrete lessons:

- **The exit dialog's "Background work is running" list is the source of truth**, not your `pgrep`. Those
  are harness-tracked background shells (each with a task ID + human name). `TaskList` returns the **todo**
  list, *not* background shells, so it can read empty while shells are live — do not treat an empty
  `TaskList` as "nothing running."
- **To actually enumerate what's alive**, list *all* your user's processes and inspect them
  (`ps -o pid,ppid,etime,%cpu,stat,args -u "$(id -un)"`), don't grep for names you assume.
- **A hung job looks "sleeping," not "running":** the stuck sweep sat at `loading …xlsr-53` for ~17 h at
  **0.2 % CPU** (state `Sl`) — a stalled model/network fetch. Check `%cpu` + output-file mtime, not just
  "is the PID present."
- **`until ! pgrep …; do sleep N; done` watcher loops never self-close** if the thing they poll dies
  without the expected sentinel — they orphan and poll forever. Prefer a bounded/`timeout`-wrapped wait, or
  stop them explicitly. To kill a specific tracked shell use `TaskStop <task-id>`; the IDs surface in the
  task-completion notifications.

---

## 2. Make targets (preferred interface)

The `Makefile` pins `JAVA_HOME` and `ANDROID_HOME` so you don't need to prefix every Gradle call:

| Target | What it runs |
|---|---|
| `make test` | All JVM unit tests |
| `make static` | detekt + spotlessCheck + `:app:lintDebug` |
| `make format` | Auto-format (spotless/ktlint) |
| `make build` | Debug APK (`:app:assembleDebug`) |
| `make verify` | Full local gate: static + lint + tests + APK (mirrors CI) |
| `make guardrails` | All AI-workflow audit scripts |
| `make ci` | `verify` + `guardrails` |
| `make emulator` | Boot the dev AVD (`changemappers-test`, Pixel 6 API 35) |
| `make bench-picovoice-fetch` | Provision the Picovoice benchmark corpus into `PV_DIR` (open downloads, no key) |
| `make bench-picovoice` | Run the wake-word benchmark; **no overrides ⇒ reproduces the committed report** |
| `make bench-picovoice-smoke` | Fast run (`bgSeconds=120`) — **does NOT match the committed report** |
| `make bench-picovoice-anchor` | Same-host PocketSphinx anchor on the dumped streams |

**Experimentation (`bench-picovoice`).** Sweep knobs are env overrides mapped to `-D` props:
`FRONTEND=` (`none`/`delta`), `DELTA=` (`NONE`/`DELTA`/`DELTA_DELTA`), `SNR=`, `WINDOW=`, `HOP=`,
`TARGETFA=`, plus `BG=`/`ENROLL=`/`HELD=`. Each **unset knob falls back to the ctor default that produced
the committed report**, so the no-override run is byte-reproducible — that is the pinned baseline. Per
**EVAL-003** any swept variant is an exploratory, **NOT-banked** family; never headline a mined variant as
an FRR/FAR win without a fresh, pre-registered, FAR-matched confirmation. **CI boundary:** the corpus is
`[measure-only]` (uncommitted), so this is never a CI gate — `make test` stays green via the `assumeTrue`
skip when `-Dpicovoice.dir` is unset.

Run a single module's tests directly when you only touched one area:

```sh
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
ANDROID_HOME=/home/arsvivendi/Android/Sdk \
/home/arsvivendi/git/speechangel/gradlew :core:matching:test
```

---

## 3. Running the app on the emulator

**AVD:** `changemappers-test` (Pixel 6, API 35, x86_64)  
**APK output:** `app/build/outputs/apk/debug/app-debug.apk`  
**Package:** `com.speechangel.app.debug`

```sh
# 1 — start emulator (background, no audio)
ANDROID_HOME=/home/arsvivendi/Android/Sdk \
$ANDROID_HOME/emulator/emulator -avd changemappers-test -no-audio -no-boot-anim \
  -no-snapshot-save -gpu swiftshader_indirect &

# 2 — wait for boot
$ANDROID_HOME/platform-tools/adb -e wait-for-device
until [ "$($ANDROID_HOME/platform-tools/adb -e shell getprop sys.boot_completed | tr -d '\r')" = "1" ]; do sleep 2; done

# 3 — build + install + launch
make build
$ANDROID_HOME/platform-tools/adb -e install -r app/build/outputs/apk/debug/app-debug.apk
$ANDROID_HOME/platform-tools/adb -e shell am start \
  -n com.speechangel.app.debug/com.speechangel.app.MainActivity
```

Stop: `adb -e shell am force-stop com.speechangel.app.debug` then kill the emulator process.

---

## 4. Architecture — runtime signal flow

The big picture that requires reading across several files:

```
AudioRecord (16 kHz PCM)
  └─ StreamingEnergyGate  (core:dsp)   — coarse VAD; gates the MFCC stage
       └─ MfccExtractor   (core:dsp)   — 13 MFCC + delta
            └─ TemplateMatcher (core:matching) — length-normalised DTW vs enrolled templates
                 └─ Recognizer (core:enrollment) — 1-NN min-distance across a command's templates + OOV reject
                      └─ CommandActionBus (app:action) — in-process event bus
                           └─ SpeechAngelAccessibilityService (app:service)
                                — ONE deterministic action per command (Play-policy line)
```

The `ListeningService` (foreground `microphone` service) owns the audio loop and drives the
pipeline above. `WakeWordGate` (core:enrollment) sits between `Recognizer` and the bus as an
optional coarse filter.

Enrollment path: UI (`app:ui:teach`) → `Enroller` (core:enrollment) → `SpeechBackend`
(core:enrollment) → Room database (`:data`). Templates are loaded from Room into
`TemplateMatcher` on service start.

**Hard constraints (do not cross):**
- `AccessibilityService` must remain `isAccessibilityTool=true` and deterministic — no LLM, no
  autonomous decisions (Google Play 2026 policy; see `research/04_build_and_reuse_plan.md` §7).
- The recognizer is purely on-device — no cloud calls anywhere in the pipeline.
- Always-on mic requires a `FOREGROUND_SERVICE_MICROPHONE` foreground service; the manifest and
  notification channel are verified by `scripts/audits/verify-foreground-service-types.mjs`.

---

## 5. The workflow scripts are dependency-free Node ESM

Every script under `scripts/` is a `.mjs` ESM module that runs on node v24 with **no external
deps** (no `npm install` needed). Run any of them standalone:

```sh
/home/arsvivendi/.nvm/versions/node/v24.16.0/bin/node scripts/audits/verify-docs-integrity.mjs
```

`package.json` wires friendly aliases (`knowledge:check`, `audit:check`, `docs:check`,
`guardrails:check`, `incident:new`, `audit:index`, `classify`), but the scripts never require the
npm layer to run.

---

## 6. Enabling the git hooks

The hooks live in `.husky/` as plain executable shell scripts. **Husky is not installed** (no
`npm install` is run for this workflow). To enable them on a host that uses them, point git at the
directory:

```sh
git config core.hooksPath .husky
```

- `.husky/pre-commit` runs `node scripts/audits/run-all.mjs` and emits the advisory
  "non-docs on `main` should be in a worktree/plan" warning.
- `.husky/pre-push` runs the guardrail bundle plus the Gradle quality + core-test gate with the
  JDK 21 / `ANDROID_HOME` env.

---

## 7. Cost & context discipline (advisory)

- **Route read-only fan-out to a cheaper subagent.** Use the `Explore` agent for "where does X
  live across the modules" sweeps; keep the file dumps out of the main context.
- **Prefer Read on a known path over a broad search.** When the file is known, read the relevant
  slice, not the whole tree.
- **Compact / clear at thresholds.** `/compact` when the transcript grows past usefulness; `/clear`
  between unrelated tasks. Re-read `AGENTS.md` + `START_HERE.md` after a compaction (the session-start
  invariant in `START_HERE.md`).
- **One worktree / one dev concern at a time.** Stray parallel state is a cost and a correctness risk.

---

## 8. Session-close protocol (mandatory — run in order)

Every session that touches code or plans must close with these steps **before** ending. Missing any
step is a process gap — the pre-commit hook and guardrails enforce them mechanically.

1. **Update plan status.** For every plan whose A-deliverables landed this session:
   - Set `Status: done (A-deliverables implemented YYYY-MM-DD; …)` (date is mandatory — the
     guardrail rejects `done` without a `YYYY-MM-DD`).
   - For plans still in progress: set `Status: active`.
   - For plans blocked externally: set `Status: blocked` with a one-line blocker note.

2. **Update `docs/plans/INDEX.md`.** Every plan file has an entry. Mark done plans with ✅ and a
   date; mark active/blocked plans accordingly.

3. **Write incident docs for every non-trivial error.** If any design error, build failure, or
   wrong assumption cost > ~5 min to fix, create a note under `docs/errors/YYYY-MM/`:
   - Required sections: Summary, Root Cause, Rerun Analysis, Prevention, Guardrail Updates,
     Planning Integration, Shift-Left Decision, Automation Follow-Up.
   - Cite a real repo file in `## Guardrail Updates` (never leave it empty).

4. **Update `docs/ai/ACTIVE_DEV_RULES.md`.** If the incident produced a new rule, add it (e.g.
   MATCH-002). If an existing rule proved insufficient, extend it.

5. **Run `make guardrails` (or `node scripts/audits/run-all.mjs`).** All 9 checks must pass green
   before the first commit. Fix any failures before committing — a red guardrail is a blocker.

6. **Commit in logical chunks** (never one giant commit):
   - Chunk 1: core logic changes (Domain models, matchers, enrollers).
   - Chunk 2: app wiring (service, DI, ViewModels).
   - Chunk 3: UI changes (screens, Compose).
   - Chunk 4: docs + plan status updates.
   - Chunk 5: workflow improvements (guardrails, hooks, CLAUDE.md, AGENTS.md).
   Each chunk must pass `make guardrails` independently. Use `git add -p` or per-file staging.

7. **Verify the commit message.** Each commit message must describe *why*, not just *what*.
   Include the plan name or gap number when relevant (e.g. "Gap 1: two-stage ListeningService
   loop — streaming mic + WakeWordGate wiring").

> **Why this is mandatory:** in the session that introduced this protocol, plan status updates,
> INDEX.md updates, incident docs, and guardrail fixes were all done manually — each one because
> a process gap was discovered in real time. Automating the checklist prevents the same discovery
> loop in every future session.
