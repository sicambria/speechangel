#!/usr/bin/env node
// create-plan.mjs  (Wave 1 — worktree/plan workflow)
// Scaffolds a plan at docs/plans/<YYYY-MM>/<slug>.md from docs/plans/TEMPLATE.md, pre-filling the
// metadata block. The scaffold keeps every <TODO> placeholder + Status: draft, so a freshly created
// plan FAILS verify-plan-workflow-guardrails.mjs until it is actually written (this is by design).
//
// Usage:
//   node scripts/ops/create-plan.mjs --slug <slug> --phase <0|1|2> --item "<roadmap item>" [--worktree <name>]

import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, read, ok, fail, info } from "../_lib.mjs";

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

function main() {
  const args = parseArgs(process.argv.slice(2));
  const slugRaw = args.slug;
  if (!slugRaw || slugRaw === "true") {
    fail("create-plan: --slug is required, e.g. --slug stage1-vad-wake-word");
    process.exit(2);
  }
  const slug = slugify(slugRaw);
  const phase = args.phase && args.phase !== "true" ? args.phase : "?";
  const item = args.item && args.item !== "true" ? args.item : "<TODO: roadmap item this plan delivers>";
  const worktree = args.worktree && args.worktree !== "true" ? args.worktree : "n/a";
  const { iso, month } = today();

  const dir = join(repoRoot, "docs", "plans", month);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, `${slug}.md`);
  if (existsSync(file)) {
    fail(`create-plan: ${file} already exists — refusing to overwrite.`);
    process.exit(1);
  }

  const title = slugRaw.replace(/[-_]+/g, " ");
  const tmpl = read("docs/plans/TEMPLATE.md")
    .replace("# Plan: <title>", `# Plan: ${title}`)
    .replace("- **Date:** <iso>", `- **Date:** ${iso}`)
    .replace("- **Phase:** <phase>", `- **Phase:** ${phase}`)
    .replace("- **Roadmap item:** <roadmap item this plan delivers>", `- **Roadmap item:** ${item}`)
    .replace("- **Worktree:** <branch/worktree name, or n/a for docs-only>", `- **Worktree:** ${worktree}`);

  writeFileSync(file, tmpl);
  ok(`scaffolded docs/plans/${month}/${slug}.md`);
  info("Fill every section, set Plan quality and move Status off `draft`, then run `node scripts/audits/verify-plan-workflow-guardrails.mjs`.");
}

main();
