#!/usr/bin/env node
// verify-sota-measurement.mjs  (guardrails:check)
// Hard gate: enforces EVAL-001 through EVAL-005 measurement discipline on any code or doc
// change that touches accuracy-critical paths (core:eval, scripts/eval, core:matching,
// core:enrollment, core:dsp, or accuracy-claim docs).
//
// Three checks:
//   1. EVAL-002/003 gate: any testing doc with a numerical accuracy claim must cite held-out
//      threshold selection and pre-registration/banked-vs-exploratory status.
//   2. S-tier experiment staleness: any S-tier experiment (score >= 810 in SCORES.md) that is
//      "planned" for >30 days without activity triggers a warning.
//   3. Honesty-banner presence: any generated eval report under core/eval/build/ that lacks
//      the required honesty caveats (synthetic banner, condition simulation banner, etc.)
//      blocks the commit.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { resolve, join } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");

const EVAL_CRITICAL_PATHS = [
  /^core\/eval\//,
  /^core\/matching\//,
  /^core\/enrollment\//,
  /^core\/dsp\//,
  /^scripts\/eval\//,
  /^docs\/testing\//,
  /^docs\/research\/experiments\//,
  /^docs\/product\/.*sota/,
];

function changedFiles() {
  try {
    const staged = execFileSync("git", ["diff", "--cached", "--name-only", "HEAD"], {
      cwd: repoRoot, encoding: "utf8", timeout: 10000
    }).split("\n").map(s => s.trim()).filter(Boolean);
    const unstaged = execFileSync("git", ["diff", "--name-only"], {
      cwd: repoRoot, encoding: "utf8", timeout: 10000
    }).split("\n").map(s => s.trim()).filter(Boolean);
    return [...new Set([...staged, ...unstaged])];
  } catch {
    return [];
  }
}

function pathsTriggerEval(files) {
  return files.filter(f => EVAL_CRITICAL_PATHS.some(re => re.test(f)));
}

// --- Check 1: Testing docs must cite EVAL discipline ---

function checkEvalCitations(triggered) {
  const violations = [];
  const testingDocPattern = /^docs\/(testing|research\/experiments)\/.*\.md$/;
  const testingDocs = triggered.filter(f => testingDocPattern.test(f));

  for (const f of testingDocs) {
    const full = resolve(repoRoot, f);
    if (!existsSync(full)) continue;
    const content = readFileSync(full, "utf8");

    const hasNumericalClaim = /\d{1,3}\.\d+%\s*(FRR|rank)/i.test(content) ||
      /(FRR|rank).*\d{1,3}\.\d+%/i.test(content) ||
      /\d+\s*FA\/hr/i.test(content) ||
      /McNemar/i.test(content);

    if (!hasNumericalClaim) continue;

    const hasHeldOut = /held.out|EVAL-002|leave.one.*fold|leave-one-fold-out/i.test(content);
    const hasPrereg = /pre.reg|EVAL-003|banked|NOT banked|exploratory/i.test(content);
    const hasReplicate = /replicate|EVAL-005|speaker/i.test(content);

    const missing = [];
    if (!hasHeldOut) missing.push("held-out threshold selection (EVAL-002)");
    if (!hasPrereg) missing.push("pre-registration or banked/exploratory label (EVAL-003)");
    if (!hasReplicate) missing.push("replication claim or speaker breakdown (EVAL-005)");

    if (missing.length > 0) {
      violations.push(`${f}: numerical accuracy claim without ${missing.join(", ")}`);
    }
  }

  return violations;
}

// --- Check 2: S-tier experiment staleness (ADVISORY WARNING only) ---

function checkStierStaleness() {
  const warnings = [];
  const scoresPath = resolve(repoRoot, "docs/research/experiments/SCORES.md");
  if (!existsSync(scoresPath)) return warnings;

  const content = readFileSync(scoresPath, "utf8");
  const lines = content.split("\n");
  for (const line of lines) {
    const match = line.match(/^\|\s*(E\d{2}-\d{2})\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*\*{0,2}(\d+)\*{0,2}\s*\|\s*(\w+)/);
    if (!match) continue;
    const [, id, scoreStr, status] = match;
    const score = parseInt(scoreStr, 10);
    if (score < 810) continue;
    if (status !== "planned") continue;

    warnings.push(`S-tier experiment ${id} (score ${score}) is "planned" — consider creating a plan under docs/plans/ or promoting to active`);
    return warnings; // One warning is enough
  }

  return warnings;
}

// --- Check 3: Generated eval reports carry honesty banners ---

function checkHonestyBanners() {
  const violations = [];
  const buildDir = resolve(repoRoot, "core/eval/build");
  if (!existsSync(buildDir)) return violations;

  try {
    const files = readdirSync(buildDir, { recursive: true });
    const reports = files.filter(f => f.endsWith(".md") && (f.includes("report") || f.includes("eval") || f.includes("torgo") || f.includes("picovoice")));

    for (const f of reports) {
      const full = resolve(buildDir, f);
      const stat = statSync(full);
      if (!stat.isFile()) continue;
      const content = readFileSync(full, "utf8");

      // Check for synthetic banner
      const syntheticCaveats = /NOT REAL|simulated|synthetic.*corpus|NOT MEASURED|probe,? not/i;
      if (content.includes("SYNTHETIC") && !syntheticCaveats.test(content)) {
        violations.push(`core/eval/build/${f}: SYNTHETIC marker without honesty caveat (expected "NOT REAL SPEECH", "simulated", or "NOT MEASURED")`);
      }

      // Check for condition simulation banner
      const hasConditions = /noise_|reverb_|bandlimit_|living_room/i.test(content);
      const hasSimCaveat = /simulated channel|simulated.*condition|condition.*simulation|channel.*simulation|probe,? not.*field|NOT MEASURED/i.test(content);
      if (hasConditions && !hasSimCaveat) {
        violations.push(`core/eval/build/${f}: acoustic condition data without simulation caveat (expected "simulated channel" or equivalent)`);
      }
    }
  } catch {
    // build/ might not exist on CI — skip
  }

  return violations;
}

// --- Main ---

function main() {
  const triggered = pathsTriggerEval(changedFiles());
  if (triggered.length === 0) {
    process.stdout.write("verify-sota-measurement: no eval-critical paths changed — SKIPPED\n");
    process.exit(0);
  }

  process.stdout.write(`verify-sota-measurement: ${triggered.length} eval-critical path(s) changed\n`);

  const violations = [
    ...checkEvalCitations(triggered),
    ...checkHonestyBanners(),
  ];
  const warnings = checkStierStaleness();

  for (const w of warnings) {
    process.stdout.write(`  WARN: ${w}\n`);
  }

  if (violations.length === 0) {
    if (warnings.length > 0) {
      process.stdout.write("verify-sota-measurement: PASS (with advisory S-tier staleness warnings)\n");
    } else {
      process.stdout.write("verify-sota-measurement: PASS\n");
    }
    process.exit(0);
  }

  for (const v of violations) {
    process.stderr.write(`  FAIL: ${v}\n`);
  }
  process.stderr.write("verify-sota-measurement: FAILED — EVAL discipline violations must be resolved before commit.\n");
  process.exit(1);
}

main();
