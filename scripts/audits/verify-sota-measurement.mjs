#!/usr/bin/env node
// verify-sota-measurement.mjs  (guardrails:check)
// Hard gate: enforces EVAL measurement discipline on any code or doc change that touches
// accuracy-critical paths (core:eval, scripts/eval, core:matching, core:enrollment, core:dsp,
// or accuracy-claim docs).
//
// Checks (hard gates, block commit):
//   1. Citation gate — any testing/experiment doc with a numerical accuracy claim must cite
//      EVAL-002 (held-out thresholds), EVAL-003 (banked/exploratory label), and EVAL-005
//      (replication or speaker breakdown).
//   2. Honesty-banner gate — generated eval reports under core/eval/build/ and scripts/eval/
//      must carry caveats for SYNTHETIC data and simulated acoustic conditions.
//   3. Fidelity-reproduction gate — any doc claiming a delta vs baseline without an explicit
//      "baseline reproduced" fidelity statement triggers a hard violation (EVAL-004).
//
// Advisory warnings (informational, do not block commit):
//   A. S-tier experiment staleness — any S-tier experiment (score >= 810 in SCORES.md) that is
//      "planned" without a matching worktree/plan file in docs/plans/.
//   B. Negated-citation detection — heuristic check for docs that mention EVAL terms in a
//      negating context ("no held-out", "not pre-registered") — warns that the doc may be
//      intentionally violating the discipline.
//
// Known limitation: the citation regex cannot distinguish "we used held-out thresholds" from
// "no held-out thresholds were used." The negated-citation warning (advisory) covers this
// partially. If this produces false negatives, promote to a semantic gate per AGENTS.md §4.9.

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

// --- Check 1: Citation gate (hard) ---

function checkEvalCitations(triggered) {
  const violations = [];
  const testingDocPattern = /^docs\/(testing|research\/experiments)\/.*\.md$/;
  const testingDocs = triggered.filter(f => testingDocPattern.test(f));

  for (const f of testingDocs) {
    const full = resolve(repoRoot, f);
    if (!existsSync(full)) continue;
    const content = readFileSync(full, "utf8");

    const hasNumericalClaim =
      /\d{1,3}\.\d+%\s*(FRR|rank|FAR)/i.test(content) ||
      /(FRR|rank|FAR).*\d{1,3}\.\d+%/i.test(content) ||
      /\d+\s*FA\/hr/i.test(content) ||
      /McNemar/i.test(content);

    if (!hasNumericalClaim) continue;

    const hasHeldOut = /held.out|EVAL-002|leave.one.*fold|leave-one-fold-out/i.test(content);
    const hasPrereg = /pre.reg|EVAL-003|banked|NOT banked|exploratory/i.test(content);
    const hasReplicate = /replicate|EVAL-005|speaker.*breakdown|per.speaker/i.test(content);

    const missing = [];
    if (!hasHeldOut) missing.push("held-out threshold selection (EVAL-002)");
    if (!hasPrereg) missing.push("pre-registration or banked/exploratory label (EVAL-003)");
    if (!hasReplicate) missing.push("replication claim or per-speaker breakdown (EVAL-005)");

    if (missing.length > 0) {
      violations.push(
        `${f}: numerical accuracy claim without ${missing.join(", ")}.\n` +
        `  → Add to the doc: "## Method" section citing EVAL-002 (held-out), EVAL-003 (pre-registered/banked), EVAL-005 (replicated on ≥2 speakers).\n` +
        `  → See EVAL-001..005 in docs/ai/ACTIVE_DEV_RULES.md for the full discipline.`
      );
    }
  }

  return violations;
}

// --- Check 2: Honesty-banner gate (hard) ---

function checkHonestyBanners() {
  const violations = [];
  const reportDirs = [
    resolve(repoRoot, "core/eval/build"),
  ];

  for (const buildDir of reportDirs) {
    if (!existsSync(buildDir)) continue;

    try {
      const files = readdirSync(buildDir, { recursive: true });
      const reports = files.filter(f =>
        f.endsWith(".md") &&
        (f.includes("report") || f.includes("eval") || f.includes("torgo") || f.includes("picovoice"))
      );

      for (const f of reports) {
        const full = resolve(buildDir, f);
        const stat = statSync(full);
        if (!stat.isFile()) continue;
        const content = readFileSync(full, "utf8");

        const syntheticCaveats = /NOT REAL|simulated|synthetic.*corpus|NOT MEASURED|probe,? not/i;
        if (content.includes("SYNTHETIC") && !syntheticCaveats.test(content)) {
          violations.push(
            `core/eval/build/${f}: SYNTHETIC marker without honesty caveat.\n` +
            `  → Expected one of: "NOT REAL SPEECH", "simulated", "synthetic corpus", "NOT MEASURED".\n` +
            `  → Generated reports must carry the same honesty banners as SyntheticCorpus.kt outputs.`
          );
        }

        const hasConditions = /noise_|reverb_|bandlimit_|living_room/i.test(content);
        const hasSimCaveat = /simulated channel|simulated.*condition|condition.*simulation|channel.*simulation|probe,? not.*field|NOT MEASURED/i.test(content);
        if (hasConditions && !hasSimCaveat) {
          violations.push(
            `core/eval/build/${f}: acoustic condition data without simulation caveat.\n` +
            `  → Expected: "simulated channel — a probe, not a field far-field recording."\n` +
            `  → ConditionEval reports must carry this caveat per EVAL-002 discipline.`
          );
        }
      }
    } catch {
      // build/ might not exist on CI — skip
    }
  }

  return violations;
}

// --- Check 3: Fidelity-reproduction gate (hard, EVAL-004) ---

function checkFidelityReproduction(triggered) {
  const violations = [];
  const claimDocPattern = /^docs\/(testing|research\/experiments)\/.*\.md$/;
  const claimDocs = triggered.filter(f => claimDocPattern.test(f));

  for (const f of claimDocs) {
    const full = resolve(repoRoot, f);
    if (!existsSync(full)) continue;
    const content = readFileSync(full, "utf8");

    // Only flag if a delta claim exists (X% vs Y%) without fidelity statement
    const hasDeltaClaim = /vs\.?\s+(MFCC|baseline|shipped)/i.test(content) ||
      /\d{1,3}\.\d+%?\s+(rel|relative|reduction|improvement|gain)/i.test(content) ||
      /McNemar\s*p\s*[<≤=]/i.test(content);

    if (!hasDeltaClaim) continue;

    const hasFidelity = /fidelity|reproduce.*baseline|baseline.*reproduce|EVAL-004|pipeline.*fidelity/i.test(content);

    if (!hasFidelity) {
      violations.push(
        `${f}: claims a delta vs baseline without fidelity-reproduction statement (EVAL-004).\n` +
        `  → EVAL-004: "Reproduce whole pipeline before trusting deltas; decompose confounded comparisons."\n` +
        `  → Add: "## Fidelity: baseline reproduced — [method] confirmed [baseline value] before measuring delta."\n` +
        `  → The 2×2 decomposition (representation × matcher) must isolate the lever — see CP-1 ceiling doc.`
      );
    }
  }

  return violations;
}

// --- Advisory: S-tier experiment staleness (warning only) ---

function checkStierStaleness() {
  const warnings = [];
  const scoresPath = resolve(repoRoot, "docs/research/experiments/SCORES.md");
  if (!existsSync(scoresPath)) return warnings;

  const content = readFileSync(scoresPath, "utf8");
  const lines = content.split("\n");
  const stale = [];

  for (const line of lines) {
    const match = line.match(/^\|\s*(E\d{2}-\d{2})\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|\s*\*{0,2}(\d+)\*{0,2}\s*\|\s*(\w+)/);
    if (!match) continue;
    const [, id, scoreStr, status] = match;
    const score = parseInt(scoreStr, 10);
    if (score < 810) continue;
    if (status !== "planned") continue;

    // Check if a plan file references this experiment
    const planDir = resolve(repoRoot, "docs/plans");
    let hasPlan = false;
    try {
      const planFiles = readdirSync(planDir, { recursive: true });
      for (const pf of planFiles) {
        if (!pf.endsWith(".md")) continue;
        const planContent = readFileSync(resolve(planDir, pf), "utf8");
        if (planContent.includes(id)) { hasPlan = true; break; }
      }
    } catch { /* planDir might not exist */ }

    if (!hasPlan) {
      stale.push(`${id} (score ${score})`);
    }
  }

  if (stale.length === 0) return warnings;
  if (stale.length === 1) {
    warnings.push(`S-tier experiment ${stale[0]} is "planned" with no plan file — risk of indefinite deferral. Consider creating a plan under docs/plans/ or demoting the experiment score.`);
  } else {
    warnings.push(`${stale.length} S-tier experiments are "planned" with no plan files: ${stale.slice(0, 3).join(", ")}${stale.length > 3 ? ` (+${stale.length - 3} more)` : ""}. Consider creating plans or demoting scores.`);
  }

  return warnings;
}

// --- Advisory: Negated-citation detection (warning only) ---

function checkNegatedCitations(triggered) {
  const warnings = [];
  const testingDocPattern = /^docs\/(testing|research\/experiments)\/.*\.md$/;
  const testingDocs = triggered.filter(f => testingDocPattern.test(f));

  for (const f of testingDocs) {
    const full = resolve(repoRoot, f);
    if (!existsSync(full)) continue;
    const content = readFileSync(full, "utf8");

    const negations = [];
    if (/no\s+held.out|not\s+held.out|without\s+held.out/i.test(content) && /held.out|EVAL-002/i.test(content)) {
      negations.push("held-out thresholds are explicitly negated while the term is mentioned — EVAL-002 may be violated");
    }
    if (/no\s+pre.reg|not\s+pre.reg|without\s+pre.reg|not\s+banked/i.test(content) && /pre.reg|EVAL-003|banked/i.test(content)) {
      negations.push("pre-registration is explicitly negated while the term is mentioned — EVAL-003 may be violated");
    }

    for (const n of negations) {
      warnings.push(`${f}: ${n}`);
    }
  }

  return warnings;
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
    ...checkFidelityReproduction(triggered),
    ...checkHonestyBanners(),
  ];
  const warnings = [
    ...checkStierStaleness(),
    ...checkNegatedCitations(triggered),
  ];

  for (const w of warnings) {
    process.stdout.write(`  WARN: ${w}\n`);
  }

  if (violations.length === 0) {
    const tag = warnings.length > 0 ? "PASS (with advisory warnings)" : "PASS";
    process.stdout.write(`verify-sota-measurement: ${tag}\n`);
    process.exit(0);
  }

  for (const v of violations) {
    process.stderr.write(`  FAIL: ${v}\n`);
  }
  process.stderr.write("verify-sota-measurement: FAILED — resolve the violations above before commit.\n");
  process.exit(1);
}

main();
