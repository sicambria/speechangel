#!/usr/bin/env node
// create-audit-finding.mjs
// Scaffolds an audit finding at docs/audits/findings/<YYYY-MM>/<YYYY-MM-DD>_<slug>.md with every
// section verify-audit-loop.mjs requires. Like incidents, the scaffold contains placeholders so an
// unfilled finding fails the audit gate until dispositioned.
//
// Usage:
//   node scripts/ops/create-audit-finding.mjs --slug <slug> --area <area> --severity <low|medium|high|critical>

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

const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");

function today() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return { iso: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`, month: `${d.getFullYear()}-${p(d.getMonth() + 1)}` };
}

function template({ title, area, severity, iso }) {
  return `# Audit Finding: ${title}

- **Date:** ${iso}
- **Area:** ${area}
- **Severity:** ${severity}
- **Disposition:** open

## Summary

<TODO: what the audit found, one paragraph>

## Evidence

<TODO: cite the concrete repo file(s)/lines, e.g. scripts/audits/<x>.mjs, gradle/libs.versions.toml>

## Recommendation

<TODO: the concrete remediation>

## Disposition Decision

- **Decision:** <accept|fix|wontfix|skip> — <reason>
- **Follow-up:** <TODO: linked plan/incident, or 'none'>
`;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const slugRaw = args.slug;
  const area = args.area || "general";
  const severity = args.severity && args.severity !== "true" ? args.severity : "medium";
  if (!slugRaw || slugRaw === "true") {
    fail("create-audit-finding: --slug is required, e.g. --slug catalog-drift");
    process.exit(2);
  }
  const slug = slugify(slugRaw);
  const { iso, month } = today();
  const dir = join(repoRoot, "docs", "audits", "findings", month);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, `${iso}_${slug}.md`);
  if (existsSync(file)) {
    fail(`create-audit-finding: ${file} already exists — refusing to overwrite.`);
    process.exit(1);
  }
  const title = slugRaw.replace(/[-_]+/g, " ");
  writeFileSync(file, template({ title, area, severity, iso }));
  ok(`scaffolded docs/audits/findings/${month}/${iso}_${slug}.md`);
  info("Fill every section + disposition, then run `node scripts/audits/verify-audit-loop.mjs`.");
}

main();
