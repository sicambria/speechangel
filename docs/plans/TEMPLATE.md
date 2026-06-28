# Plan: <title>

<!--
  Canonical plan template (Wave 1 worktree/plan workflow). This file is EXEMPT from the
  plan-workflow completeness gate by filename (TEMPLATE.md). Copy it via:
      node scripts/ops/create-plan.mjs --slug <slug> --phase <0|1|2> --item "<roadmap item>"
  A scaffolded plan FAILS verify-plan-workflow-guardrails.mjs until every <TODO> is replaced and
  Status is moved off `draft` (this is by design — an unfinished plan is not a plannable plan).
-->

- **Date:** <iso>
- **Phase:** <phase>
- **Roadmap item:** <roadmap item this plan delivers>
- **Status:** draft  <!-- draft | planned | active | blocked | done -->
- **Worktree:** <branch/worktree name, or n/a for docs-only>
- **Plan quality:** <score>/100  <!-- self/review score; target > 94 before implementation -->

## Goal

<TODO: the outcome in one or two sentences — what is true when this is done that is not true now.>

## Context & Constraints

<TODO: the non-negotiables this must respect (on-device, deterministic action layer, FRR+FAR honesty,
Play-policy line, licensing). Link related plans/docs with backtick code-paths.>

## Approach

<TODO: the chosen approach and why, plus the alternatives rejected and why. Name the modules touched.>

## Steps

<TODO: ordered, concrete steps. Each step names the file(s) it creates/edits and the check that proves
it landed. Keep steps small enough to verify individually.>

## Definition of Done

<TODO: objective acceptance criteria. For recognizer/accuracy work this MUST be expressed as
FRR + FAR/hour against a named dataset — never a bare percentage. For UX/service work, the concrete
observable behavior + the gate that proves it.>

## Risks & Mitigations

<TODO: what could make this fail or regress, and the mitigation/rollback for each.>

## Test & Verification

<TODO: the exact commands/gates that verify this plan's output (e.g. `make verify`, a new
`:core:*:test`, an instrumentation test, a guardrail). State what is verifiable on this host vs what
needs a device/real audio, and say so honestly.>
