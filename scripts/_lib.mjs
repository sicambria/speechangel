// Shared, dependency-free helpers for the SpeechAngel workflow scripts.
// Runs on node v24, no external deps. Import with a relative path, e.g.
//   import { repoRoot, ok, fail } from "../_lib.mjs";

import { execFileSync } from "node:child_process";
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join, relative } from "node:path";

// The repo root is two levels up from scripts/_lib.mjs (scripts/ -> repo root).
const here = dirname(fileURLToPath(import.meta.url));
export const repoRoot = resolve(here, "..");

export function abs(p) {
  return resolve(repoRoot, p);
}

export function read(p) {
  return readFileSync(abs(p), "utf8");
}

export function exists(p) {
  return existsSync(abs(p));
}

// All git-tracked files (repo-relative paths). Empty array if git is unavailable.
export function trackedFiles() {
  try {
    const out = execFileSync("git", ["ls-files"], { cwd: repoRoot, encoding: "utf8" });
    return out.split("\n").map((s) => s.trim()).filter(Boolean);
  } catch {
    return [];
  }
}

// Recursively list files under a dir (repo-relative), skipping build/.gradle/node_modules/.git.
export function walk(dirRel) {
  const out = [];
  const start = abs(dirRel);
  if (!existsSync(start)) return out;
  const SKIP = new Set(["build", ".gradle", ".git", "node_modules", ".kotlin", ".idea"]);
  const rec = (d) => {
    for (const name of readdirSync(d)) {
      if (SKIP.has(name)) continue;
      const full = join(d, name);
      const st = statSync(full);
      if (st.isDirectory()) rec(full);
      else out.push(relative(repoRoot, full));
    }
  };
  rec(start);
  return out;
}

// --- tiny reporting helpers -------------------------------------------------
const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const DIM = "\x1b[2m";
const RESET = "\x1b[0m";

export function ok(msg) {
  process.stdout.write(`${GREEN}✓${RESET} ${msg}\n`);
}
export function warn(msg) {
  process.stdout.write(`${YELLOW}!${RESET} ${msg}\n`);
}
export function info(msg) {
  process.stdout.write(`${DIM}${msg}${RESET}\n`);
}
export function fail(msg) {
  process.stderr.write(`${RED}✗${RESET} ${msg}\n`);
}

// Standard exit: print a result line and exit with the right code.
export function done(name, failures) {
  if (failures.length === 0) {
    ok(`${name}: PASS`);
    process.exit(0);
  }
  for (const f of failures) fail(`  ${f}`);
  fail(`${name}: FAIL (${failures.length} issue${failures.length === 1 ? "" : "s"})`);
  process.exit(1);
}

export { join, relative };
