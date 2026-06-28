#!/usr/bin/env node
// verify-docs-integrity.mjs
// Docs integrity gate (adapted to this repo's conventions in docs/standards/documentation-governance.md):
//   1) the required temporal-bucket directories + generated indexes exist
//   2) link-safety: NO relative markdown links to internal files (use backtick code-paths instead)
//   3) backtick code-paths that look like real repo files/dirs actually exist (no broken references)
//
// Fenced ``` code blocks are excluded from the inline-backtick scan (they hold commands + dir trees).
// Tokens with placeholders/globs (< > * { } $ **), absolute paths (/…), home paths (~…), and
// multi-word commands (containing spaces) are skipped — they are not literal repo references.
//
// Exit 0 if clean, 1 otherwise.

import { exists, read, walk, done } from "../_lib.mjs";

const NAME = "verify-docs-integrity";

const REQUIRED_DIRS = [
  "docs/errors/2026-06",
  "docs/errors/rca/rca-plan-done/2026-06",
  "docs/plans/2026-06",
  "docs/plans/done/2026-06",
  "docs/plans/worktrees",
  "docs/audits/findings/2026-06",
  "docs/ai/retro/2026-06",
  "docs/meta/dreaming",
];

const REQUIRED_FILES = [
  "docs/errors/INDEX.md",
  "docs/audits/INDEX.md",
  "docs/DOC_TOC.md",
  "docs/standards/documentation-governance.md",
];

function stripFences(text) {
  // Drop ```…``` fenced blocks (keep line count irrelevant — we only scan inline backticks).
  return text.replace(/```[\s\S]*?```/g, "");
}

function looksLikeRepoPath(tok) {
  if (!tok.includes("/")) return false; // single-token names like Domain.kt are not validated
  if (/[\s<>*{}$]/.test(tok)) return false; // placeholders, globs, multi-word commands
  if (tok.includes("**")) return false;
  if (/YYYY|MM-DD/.test(tok)) return false; // temporal placeholders, not literal paths
  if (tok.startsWith("/") || tok.startsWith("~") || tok.startsWith("./") || tok.startsWith("http")) return false;
  if (tok.includes(":")) return false; // gradle coords / URLs / module paths
  // must end in a known doc/code extension OR be a directory path (trailing /)
  return /\.(md|mjs|json|kts|toml|properties|ya?ml|xml|kt|txt|nvmrc)$/.test(tok) || tok.endsWith("/");
}

function main() {
  const failures = [];

  // 1) required structure
  for (const d of REQUIRED_DIRS) {
    if (!exists(d)) failures.push(`missing required temporal-bucket dir: ${d}/`);
  }
  for (const f of REQUIRED_FILES) {
    if (!exists(f)) failures.push(`missing required doc: ${f}`);
  }

  // gather the docs to scan straight from disk (these files may be untracked on a fresh transplant)
  const docs = walk("docs").filter((f) => f.endsWith(".md"));
  for (const k of ["AGENTS.md", "CLAUDE.md"]) if (exists(k)) docs.push(k);

  for (const file of docs) {
    if (!exists(file)) continue;
    const raw = read(file);
    const text = stripFences(raw);

    // 2) relative internal markdown links are forbidden. Strip inline-code spans first so that a
    //    doc *documenting* the bad pattern inside backticks (e.g. `[x](../y.md)`) is not flagged.
    const textNoCode = text.replace(/`[^`\n]+`/g, "");
    const linkRe = /\[[^\]]*\]\(([^)]+)\)/g;
    let lm;
    while ((lm = linkRe.exec(textNoCode)) !== null) {
      const target = lm[1].trim();
      if (/^(https?:|mailto:|#)/.test(target)) continue; // external / anchor are fine
      failures.push(
        `${file}: relative markdown link to "${target}" — use a backtick code-path instead (link-safety).`
      );
    }

    // 3) backtick code-paths must resolve
    const tickRe = /`([^`\n]+)`/g;
    let tm;
    while ((tm = tickRe.exec(text)) !== null) {
      const tok = tm[1].trim();
      if (!looksLikeRepoPath(tok)) continue;
      const clean = tok.replace(/\/$/, "");
      if (!exists(clean)) {
        failures.push(`${file}: backtick code-path \`${tok}\` does not exist in the repo.`);
      }
    }
  }

  done(NAME, failures);
}

main();
