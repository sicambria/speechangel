#!/usr/bin/env node
// verify-plan-workflow-guardrails.mjs  (Wave 1 — worktree/plan workflow)
// Enforces plan-doc discipline so the "plan inside a worktree" rule (AGENTS.md §3) has teeth:
//
//   1. Structure   — every active/planned/blocked/done plan under docs/plans/<YYYY-MM>/ has the
//                    required sections + a valid Status; no scaffold placeholders survive.
//   2. Accuracy honesty — a plan whose Roadmap item / text concerns the recognizer or accuracy must
//                    express its Definition of Done as FRR + FAR (never a bare "99%") — the project's
//                    non-negotiable (research/ + ROADMAP cross-cutting rule).
//   3. Worktree registry — every docs/plans/worktrees/<name>.md names a plan file that exists.
//   4. Done discipline — a plan with Status `done` MUST include a YYYY-MM-DD date in its Status
//                    line (e.g. `done (…2026-06-28…)`) so "done" is never set speculatively and
//                    every completion is timestamped for the INDEX.md audit trail.
//
// `draft`-status plans are skipped (work in progress). TEMPLATE.md and .gitkeep are exempt.
// On a repo with zero plans this passes vacuously (exit 0).
//
// Usage: node scripts/audits/verify-plan-workflow-guardrails.mjs

import { walk, read, exists, done } from "../_lib.mjs";

const NAME = "verify-plan-workflow-guardrails";
const PLANS_DIR = "docs/plans";

const REQUIRED_HEADINGS = [
  "## Goal",
  "## Context & Constraints",
  "## Approach",
  "## Steps",
  "## Definition of Done",
  "## Risks & Mitigations",
  "## Test & Verification",
];
const VALID_STATUS = ["draft", "planned", "active", "blocked", "done"];
const PLACEHOLDERS = [/<TODO/i, /\bTBD\b/, /<iso>/, /<phase>/, /<score>/, /<title>/, /<roadmap item/i];

// Accuracy-honesty trigger: plans about these need FRR+FAR, not a bare percentage.
const ACCURACY_WORDS = /\b(FRR|FAR|recogni[sz]|matcher|accuracy|threshold|DTW|MFCC|false accept|false reject)\b/i;

function planFiles() {
  return walk(PLANS_DIR).filter(
    (f) =>
      f.endsWith(".md") &&
      !f.endsWith("TEMPLATE.md") &&
      !f.endsWith("INDEX.md")
  );
}

function section(text, heading) {
  const idx = text.indexOf(heading);
  if (idx === -1) return null;
  const rest = text.slice(idx + heading.length);
  const next = rest.search(/\n## /);
  return (next === -1 ? rest : rest.slice(0, next)).trim();
}

function statusOf(text) {
  const m = text.match(/\*\*Status:\*\*\s*([a-z]+)/i);
  return m ? m[1].toLowerCase() : null;
}

// Full Status line (everything after the label), for extra checks on done plans.
function statusLineFull(text) {
  const m = text.match(/\*\*Status:\*\*\s*(.+)/);
  return m ? m[1].trim() : "";
}

function validatePlan(file, failures) {
  const text = read(file);
  const status = statusOf(text);

  if (!status) {
    failures.push(`${file}: missing or unreadable **Status:** label (one of ${VALID_STATUS.join("|")}).`);
    return;
  }
  if (!VALID_STATUS.includes(status)) {
    failures.push(`${file}: invalid Status "${status}" (expected one of ${VALID_STATUS.join("|")}).`);
    return;
  }
  if (status === "draft") return; // work-in-progress — not yet held to the bar

  // 4. done discipline — must include a YYYY-MM-DD date so completion is timestamped
  if (status === "done" && !/\d{4}-\d{2}-\d{2}/.test(statusLineFull(text))) {
    failures.push(
      `${file}: Status is "done" but missing implementation date (YYYY-MM-DD) — e.g. done (…2026-06-28…).`
    );
  }

  // 1. structure
  for (const h of REQUIRED_HEADINGS) {
    if (!text.includes(h)) failures.push(`${file}: missing required section "${h}".`);
  }
  // 1b. no scaffold placeholders in a non-draft plan
  for (const re of PLACEHOLDERS) {
    if (re.test(text)) {
      failures.push(`${file}: unfilled scaffold placeholder (${re}) — finish the plan or set Status: draft.`);
      return;
    }
  }
  // 1c. key sections non-empty
  for (const h of ["## Goal", "## Definition of Done", "## Test & Verification"]) {
    const body = section(text, h);
    if (!body || body.length < 12) failures.push(`${file}: section "${h}" is empty.`);
  }

  // 2. accuracy honesty
  const dod = section(text, "## Definition of Done") || "";
  if (ACCURACY_WORDS.test(text)) {
    const hasFrrFar = /FRR/i.test(dod) && /FAR/i.test(dod);
    const barenPercent = /\b9\d(\.\d+)?\s*%/.test(dod); // 90%+ bare claim
    if (!hasFrrFar) {
      failures.push(
        `${file}: accuracy/recognizer plan — ## Definition of Done must be expressed as FRR + FAR (never a bare %).`
      );
    }
    if (barenPercent && !hasFrrFar) {
      failures.push(`${file}: ## Definition of Done uses a bare high-% accuracy claim — use FRR + FAR/hour instead.`);
    }
  }
}

function validateWorktreeRegistry(failures) {
  const entries = walk(`${PLANS_DIR}/worktrees`).filter((f) => f.endsWith(".md"));
  for (const f of entries) {
    const text = read(f);
    // any backtick docs/plans/...md reference must resolve
    const refs = text.match(/docs\/plans\/[A-Za-z0-9_./-]+\.md/g) || [];
    for (const r of refs) {
      if (!exists(r)) failures.push(`${f}: references plan "${r}" which does not exist.`);
    }
  }
}

function main() {
  const failures = [];
  for (const f of planFiles()) validatePlan(f, failures);
  validateWorktreeRegistry(failures);
  done(NAME, failures);
}

main();
