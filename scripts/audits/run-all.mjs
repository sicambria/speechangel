#!/usr/bin/env node
// run-all.mjs  (guardrails:check)
// Runs every guardrail verifier, prints a summary, and exits non-zero if any failed.
// Each verifier is a self-contained .mjs that exits 0 on pass / non-zero on fail; we run them as
// child node processes so one crashing verifier cannot take down the whole bundle silently.

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));

// Order: cheap/structural first, then content gates. Only verifiers that exist and exit 0 standalone
// are wired here (meta Wave 7 — "wire only what is green").
const VERIFIERS = [
  "verify-docs-integrity.mjs",
  "verify-learning-loop.mjs",
  "verify-audit-loop.mjs",
  "verify-plan-workflow-guardrails.mjs",
  "verify-no-dynamic-versions.mjs",
  "verify-gradle-wrapper-pinned.mjs",
  "verify-version-catalog-usage.mjs",
  "verify-foreground-service-types.mjs",
  "verify-listening-offmain.mjs",
  "verify-no-secrets.mjs",
  "verify-sota-measurement.mjs",
];

function main() {
  const results = [];
  for (const v of VERIFIERS) {
    const script = resolve(here, v);
    const r = spawnSync(process.execPath, [script], { encoding: "utf8" });
    const passed = r.status === 0;
    results.push({ v, passed });
    process.stdout.write(`\n=== ${v} ===\n`);
    if (r.stdout) process.stdout.write(r.stdout);
    if (r.stderr) process.stderr.write(r.stderr);
  }

  const failed = results.filter((r) => !r.passed);
  process.stdout.write("\n──────── guardrails:check summary ────────\n");
  for (const r of results) {
    process.stdout.write(`  ${r.passed ? "PASS" : "FAIL"}  ${r.v}\n`);
  }
  process.stdout.write(
    `\n${results.length - failed.length}/${results.length} verifiers passed.\n`
  );
  if (failed.length) {
    process.stderr.write(`guardrails:check FAILED (${failed.length} verifier(s) failed).\n`);
    process.exit(1);
  }
  process.stdout.write("guardrails:check PASSED.\n");
  process.exit(0);
}

main();
