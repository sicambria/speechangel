#!/usr/bin/env node
// create-incident-report.mjs
// Scaffolds an incident note at docs/errors/<YYYY-MM>/<YYYY-MM-DD>_<slug>.md from a template that
// contains EVERY section the learning-loop gate requires (incl. ## Shift-Left Decision and
// ## Planning Integration). The scaffold is intentionally full of placeholders so that an unfilled
// note FAILS verify-learning-loop.mjs until the loop is actually closed (meta §5.2).
//
// Usage:
//   node scripts/ops/create-incident-report.mjs --slug <slug> --area <area> --trigger "<text>"
//
// After scaffolding it re-validates by running the loop check note-locally is left to the operator
// (run `node scripts/audits/verify-learning-loop.mjs`).

import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, ok, fail, info } from "../_lib.mjs";

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const val = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "true";
      args[key] = val;
    }
  }
  return args;
}

function slugify(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

function today() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return { iso: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`, month: `${d.getFullYear()}-${p(d.getMonth() + 1)}` };
}

function template({ title, area, trigger, iso }) {
  return `# Incident: ${title}

- **Date:** ${iso}
- **Area:** ${area}
- **Trigger:** ${trigger}
- **Status:** open
- **Guardrail Links:** <TODO: link the ACTIVE_DEV_RULES rule / contract / gate this promotes to>
- **Automation Links:** <TODO: link the scripts/audits/<x>.mjs gate or 'skip'>

## Summary

<TODO: what broke, in one paragraph — symptom, patterns, surprises, time wasted>

## Root Cause

<TODO: WHY it broke — the actual cause, not the symptom. Scan the codebase for the same class.>

## Rerun Analysis

(For command-triggered failures. Fill each field; use 'n/a' only if genuinely not applicable.)

- **Last command proved:** <TODO>
- **Failed phase:** <TODO>
- **Still unknown:** <TODO>
- **Failure class:** <TODO>
- **Smallest next probe:** <TODO>
- **Stop condition:** <TODO>

## Prevention

<TODO: the concrete change that prevents recurrence — a real change, not a restatement of the bug>

## Guardrail Updates

<TODO: cite the concrete repo file(s) changed, e.g. scripts/audits/<x>.mjs, docs/ai/ACTIVE_DEV_RULES.md>

## Planning Integration

<TODO: name the concrete planning artifact that carries this lesson forward — a plan under
docs/plans/2026-06/, a Definition of Done, or a docs/ai/ACTIVE_DEV_RULES.md rule>

## Shift-Left Decision

- **Tests:** <add|update|skip> — <reason>
- **Guardrail/automation:** <add|update|skip> — <reason>

## Automation Follow-Up

<TODO: the guardrail/automation to build now or later, or an explicit 'skip' with reason>
`;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const slugRaw = args.slug;
  const area = args.area || "general";
  const trigger = args.trigger && args.trigger !== "true" ? args.trigger : "<TODO: what triggered this>";
  if (!slugRaw || slugRaw === "true") {
    fail("create-incident-report: --slug is required, e.g. --slug stale-mfcc-vector");
    process.exit(2);
  }
  const slug = slugify(slugRaw);
  const { iso, month } = today();
  const dir = join(repoRoot, "docs", "errors", month);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, `${iso}_${slug}.md`);
  if (existsSync(file)) {
    fail(`create-incident-report: ${file} already exists — refusing to overwrite.`);
    process.exit(1);
  }
  const title = slugRaw.replace(/[-_]+/g, " ");
  writeFileSync(file, template({ title, area, trigger, iso }));
  ok(`scaffolded docs/errors/${month}/${iso}_${slug}.md`);
  info("Now close the loop: fill every section, then run `node scripts/audits/verify-learning-loop.mjs`.");
  info("The note will FAIL the gate until all <TODO>/TBD placeholders are replaced (this is by design).");
}

main();
