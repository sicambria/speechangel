#!/usr/bin/env node
// classify.mjs — contracts-as-data shift-left classifier.
// Matches changed paths against docs/ai/workflow-boundary-contracts.json and surfaces the
// boundary contracts a change touches, plus the follow-up commands to run. Advisory only
// (always exits 0) — it shifts the "did you remember the other side of this boundary?" question
// left, to command-construction time.
//
// Usage:
//   node scripts/workflow/classify.mjs <path> [<path> ...]
//   node scripts/workflow/classify.mjs            # no args -> uses `git diff --name-only HEAD`

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const CONTRACTS = resolve(repoRoot, "docs/ai/workflow-boundary-contracts.json");

function changedFromGit() {
  try {
    const out = execFileSync("git", ["diff", "--name-only", "HEAD"], { cwd: repoRoot, encoding: "utf8" });
    return out.split("\n").map((s) => s.trim()).filter(Boolean);
  } catch {
    return [];
  }
}

function main() {
  let paths = process.argv.slice(2);
  let fromGit = false;
  if (paths.length === 0) {
    paths = changedFromGit();
    fromGit = true;
  }

  let data;
  try {
    data = JSON.parse(readFileSync(CONTRACTS, "utf8"));
  } catch (e) {
    process.stderr.write(`classify: cannot read ${CONTRACTS}: ${e.message}\n`);
    process.exit(0); // advisory — never block
  }
  const contracts = data.contracts || [];

  if (paths.length === 0) {
    process.stdout.write(
      `classify: no paths given${fromGit ? " (and no git changes)" : ""}. Known contracts:\n`
    );
    for (const c of contracts) process.stdout.write(`  - [${c.category}] ${c.id}: ${c.title}\n`);
    process.exit(0);
  }

  // Compile a pattern, supporting a leading "(?i)" inline-flag prefix (JS has no inline flags).
  const compile = (p) => {
    const m = p.match(/^\(\?([a-z]+)\)(.*)$/);
    return m ? new RegExp(m[2], m[1]) : new RegExp(p);
  };

  const hits = [];
  for (const c of contracts) {
    const regexes = (c.patterns || []).map(compile);
    const matched = paths.filter((p) => regexes.some((re) => re.test(p)));
    if (matched.length) hits.push({ contract: c, matched });
  }

  if (hits.length === 0) {
    process.stdout.write(`classify: ${paths.length} path(s) touched no boundary contract.\n`);
    process.exit(0);
  }

  process.stdout.write(`classify: ${hits.length} boundary contract(s) touched:\n\n`);
  for (const { contract, matched } of hits) {
    process.stdout.write(`▶ [${contract.category}] ${contract.title}\n`);
    process.stdout.write(`  why: ${contract.description}\n`);
    process.stdout.write(`  matched: ${matched.join(", ")}\n`);
    for (const f of contract.followUps || []) {
      process.stdout.write(`  → ${f.label}: ${f.command}\n`);
    }
    process.stdout.write("\n");
  }
  process.exit(0);
}

main();
