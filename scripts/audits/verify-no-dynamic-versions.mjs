#!/usr/bin/env node
// verify-no-dynamic-versions.mjs
// Reproducibility gate: the Gradle version catalog must contain NO dynamic versions.
// Dynamic = `+` ranges (e.g. "1.0.+"), "latest.release"/"latest.integration", or "-SNAPSHOT".
//
// IMPORTANT: comments are stripped before scanning, so the catalog's own explanatory header
// ("# No dynamic versions (no '+', no 'latest.release')") does NOT trip the gate. Only actual
// declared version *values* are tested:
//   - every `key = "value"` under the [versions] table
//   - any inline `version = "value"` anywhere in the file
//
// Exit 0 if clean, 1 if any dynamic version is found. Exits 0 (with a note) if the catalog is absent.

import { exists, read, done, info } from "../_lib.mjs";

const NAME = "verify-no-dynamic-versions";
const CATALOG = "gradle/libs.versions.toml";

const DYNAMIC = [
  { re: /\+/, why: "range '+' suffix" },
  { re: /latest\.release/i, why: "'latest.release'" },
  { re: /latest\.integration/i, why: "'latest.integration'" },
  { re: /-?snapshot/i, why: "SNAPSHOT" },
];

function stripComment(line) {
  // Remove a trailing `# ...` comment. TOML strings don't contain unescaped `#` in this catalog,
  // so a simple split is safe and is exactly what keeps the header comment from false-positiving.
  const i = line.indexOf("#");
  return i === -1 ? line : line.slice(0, i);
}

function checkValue(value, lineNo, failures, label) {
  for (const { re, why } of DYNAMIC) {
    if (re.test(value)) {
      failures.push(`${CATALOG}:${lineNo} dynamic version (${why}) in ${label}: "${value}"`);
      return;
    }
  }
}

function main() {
  const failures = [];
  if (!exists(CATALOG)) {
    info(`${NAME}: no ${CATALOG} found — nothing to check (exit 0).`);
    process.exit(0);
  }
  const lines = read(CATALOG).split("\n");
  let section = "";
  lines.forEach((raw, idx) => {
    const lineNo = idx + 1;
    const line = stripComment(raw);
    const sec = line.match(/^\s*\[([^\]]+)\]\s*$/);
    if (sec) {
      section = sec[1].trim();
      return;
    }
    // Inline version = "..." anywhere.
    const inline = line.match(/\bversion\s*=\s*"([^"]*)"/);
    if (inline) checkValue(inline[1], lineNo, failures, "inline version");
    // Every key = "..." under [versions].
    if (section === "versions") {
      const kv = line.match(/^\s*[A-Za-z0-9_.-]+\s*=\s*"([^"]*)"/);
      if (kv) checkValue(kv[1], lineNo, failures, "[versions] entry");
    }
  });
  done(NAME, failures);
}

main();
