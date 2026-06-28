# Active Development Rules

Promoted, numbered **technical** rules — code-level conventions that earned their place by an
incident or a recurring failure class. This file starts **empty by design**: rules are added only
when an incident in `docs/errors/` justifies promotion (see the ladder in `AGENTS.md` §0).

For agent-neutral *behavior* rules (how to work), see `docs/ai/AI_BEHAVIOR_GUARDRAILS.md`.

---

## Numbering convention

- Rules are numbered per area, e.g. `DSP-001`, `MATCH-001`, `ANDROID-001`, `BUILD-001`, `WORKFLOW-001`.
- Each rule records: **the rule** (one imperative sentence), **why** (the incident that promoted it,
  linked by `docs/errors/2026-06/<file>.md` code-path), and **the gate** (the
  `scripts/audits/<verifier>.mjs` or test that enforces it, or `advisory` if not yet automated).
- A rule is only added here after its class recurs with low false positives. Do not pre-seed.

### Areas

- **BUILD** — Gradle, version catalog, wrapper, reproducibility.
- **ANDROID** — manifest, foreground service, accessibility, permissions, Play policy.
- **DSP** — MFCC / VAD / framing signal-processing rules (`core:dsp`).
- **MATCH** — DTW / template-matching / threshold rules (`core:matching`, `core:enrollment`).
- **MODEL** — domain model invariants (`core:model`).
- **WORKFLOW** — plan/worktree/incident process rules.

---

## Rules

_None yet. The first rule is added when the first incident promotes one._
