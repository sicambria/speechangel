# Engineering Principles

These are the foundational engineering principles that govern every architectural and
implementation decision in this repo. They apply equally to human and AI contributors and are
enforced (best-effort) by the AI behavior guardrails in `docs/ai/AI_BEHAVIOR_GUARDRAILS.md`,
the boundary classifier in `docs/ai/workflow-boundary-contracts.json`, and the gate scripts in
`scripts/audits/`.

---

## 1. First Principles Engineering

Apply first-principles thinking before making architectural or implementation decisions.
Decompose every problem into its fundamental objectives, constraints, assumptions, and measurable
requirements rather than following existing implementations by default.

For every significant component:

1. Identify the core problem being solved.
2. Distinguish essential complexity from accidental complexity.
3. Challenge inherited assumptions — especially assumptions baked into the original port source
   (see `docs/meta/port-status.md` for the honest transplant state).
4. Evaluate alternative solution spaces.
5. Justify the chosen design using evidence, benchmarks, and trade-off analysis.
6. Explicitly document why simpler or more general approaches were rejected.

Avoid local optimizations that increase overall system complexity. Optimize for correctness,
simplicity, maintainability, extensibility, reproducibility, and measurable real-world performance.

**AI workflow link:** Design decisions that pass a confidence threshold (>90/100) and are made
autonomously are logged in `docs/ai/ai-decision-log.md` with the alternatives considered, the
evidence, and a reversal trigger. Guardrail #2 ("Ground every claim in the repo or a primary
source") in `docs/ai/AI_BEHAVIOR_GUARDRAILS.md` enforces the evidence requirement.

---

## 2. Open Source Reuse Before Reinvention

Treat existing, well-maintained open-source software as the default implementation strategy.
SpeechAngel already carries a reuse map in `research/04_build_and_reuse_plan.md` §3 — consult it
before adding a new dependency or implementing a new algorithm.

Before implementing any non-trivial algorithm, framework, utility, workflow, parser, optimizer,
benchmark, visualization, or infrastructure component:

1. Actively search for mature, production-proven OSS alternatives.
2. Compare multiple candidates using objective evaluation criteria.
3. Document trade-offs including maturity, maintenance activity, community adoption, license
   compatibility, security history, performance, extensibility, and long-term sustainability.
4. Prefer composition over custom implementation whenever practical.
5. Minimize custom code by leveraging proven libraries.

Only implement custom solutions when at least one of the following is true:

- No suitable OSS solution exists.
- Measurable performance or capability requirements cannot be achieved (with reproducible
  benchmarks that demonstrate the gap — see `docs/ai/ACTIVE_DEV_RULES.md` EVAL-004 for the
  fidelity-gate requirement).
- Licensing prevents use.
- Security or compliance requires a custom implementation.
- Repository-specific requirements fundamentally differ from available solutions.

Every custom implementation must include documented justification explaining why existing OSS
solutions were not adopted. That justification lives in the relevant plan under `docs/plans/`
and is cross-referenced in the `docs/ai/ai-decision-log.md` when the decision was made
autonomously.

**AI workflow link:** Guardrail #12 ("Prefer backtick code-paths") in
`docs/ai/AI_BEHAVIOR_GUARDRAILS.md` ensures reuse justifications remain link-safe. The
`dependency-catalog-sync` contract in `docs/ai/workflow-boundary-contracts.json` enforces that
every new dependency is routed through the version catalog with a pinned, non-dynamic version.

---

## 3. Continuous Technology Discovery

During repository analysis, continuously identify opportunities to replace custom implementations
with higher-quality OSS components. Produce a migration backlog ranked by expected impact,
engineering effort, technical risk, maintenance cost reduction, and projected improvement in
benchmark scores.

Whenever a replacement is proposed:

1. Estimate expected gains in correctness, performance, maintainability, reliability, developer
   productivity, and total cost of ownership.
2. Validate these estimates through reproducible benchmarks before adoption — not after.
   A benchmark that cannot be reproduced is not evidence (see `docs/ai/ACTIVE_DEV_RULES.md`
   EVAL-004 §1 for the fidelity-gate: reproduce the committed number first, then trust the delta).

The migration backlog is maintained as a section in the relevant plan (under `docs/plans/`) or
as a standalone discovery entry when surfaced during analysis that does not yet have a plan.
Findings that constitute a "gap" between current state and a known higher-quality OSS alternative
are surfaced in the monthly meta-scan (cadence) under `docs/meta/dreaming/`.

**AI workflow link:** The `START_HERE.md` session-start invariant (`docs/ai/START_HERE.md`)
requires re-reading the error index and known errors before acting — this ensures discovery
findings about replaced components are always in context. Guardrail #11 ("Promote on evidence,
not intuition") in `docs/ai/AI_BEHAVIOR_GUARDRAILS.md` governs whether a discovery candidate
earns promotion into a hard gate.
