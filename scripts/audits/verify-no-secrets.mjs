#!/usr/bin/env node
// verify-no-secrets.mjs
// Best-effort secret scan over git-tracked text files. Catches obvious credential/key material that
// must never be committed. Language-agnostic; deliberately conservative (tight patterns) to keep
// false positives low — prose mentioning "secret"/"key" must NOT trip it.
//
// Checks:
//   - tracked keystore/credential files by name/extension (*.jks, *.keystore except debug.keystore,
//     *.p12, *.pfx, keystore.properties, secrets.properties)
//   - PEM private-key headers, AWS access-key ids, Google API keys, GitHub/Slack tokens
//   - explicit `secret|token|password|api_key = "<16+ char value>"` assignments
//
// Skips binaries (e.g. gradle-wrapper.jar) and build/.gradle output. Exit 0 if clean, 1 otherwise.

import { trackedFiles, read, done } from "../_lib.mjs";

const NAME = "verify-no-secrets";

const BINARY_EXT = new Set([
  ".jar", ".zip", ".gz", ".tgz", ".apk", ".aab", ".so", ".bin", ".dex", ".class",
  ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".ttf", ".otf", ".woff", ".woff2",
  ".pdf", ".keystore", ".jks", ".p12", ".pfx", // credential binaries handled by name-check below
]);

// Filename-based credential material that should never be tracked.
const SECRET_FILE = [
  { re: /(^|\/)[^/]+\.jks$/i, why: "Java keystore (.jks)" },
  { re: /(^|\/)[^/]+\.keystore$/i, why: "keystore", allow: /(^|\/)debug\.keystore$/i },
  { re: /(^|\/)[^/]+\.(p12|pfx)$/i, why: "PKCS#12 keystore" },
  { re: /(^|\/)keystore\.properties$/i, why: "keystore.properties" },
  { re: /(^|\/)secrets\.properties$/i, why: "secrets.properties" },
];

// Content-based patterns (run against text files only).
const CONTENT = [
  { re: /-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----/, why: "PEM private key" },
  { re: /\bAKIA[0-9A-Z]{16}\b/, why: "AWS access key id" },
  { re: /\bAIza[0-9A-Za-z_\-]{35}\b/, why: "Google API key" },
  { re: /\bgh[pousr]_[0-9A-Za-z]{36}\b/, why: "GitHub token" },
  { re: /\bxox[baprs]-[0-9A-Za-z-]{10,}\b/, why: "Slack token" },
  {
    re: /\b(?:secret|token|password|passwd|api[_-]?key)\b\s*[:=]\s*["'][A-Za-z0-9/+_\-]{16,}["']/i,
    why: "hardcoded credential assignment",
  },
];

function ext(p) {
  const i = p.lastIndexOf(".");
  return i === -1 ? "" : p.slice(i).toLowerCase();
}

function main() {
  const failures = [];
  const files = trackedFiles().filter((f) => !f.includes("/build/") && !f.startsWith("build/"));

  for (const file of files) {
    // 1) filename-based credential files
    for (const { re, why, allow } of SECRET_FILE) {
      if (re.test(file) && !(allow && allow.test(file))) {
        failures.push(`${file}: tracked ${why} — credential material must not be committed.`);
      }
    }
    // 2) content-based — text files only
    if (BINARY_EXT.has(ext(file))) continue;
    let text;
    try {
      text = read(file);
    } catch {
      continue;
    }
    // skip files that look binary (NUL byte)
    if (text.includes("\u0000")) continue;
    for (const { re, why } of CONTENT) {
      const m = text.match(re);
      if (m) {
        const lineNo = text.slice(0, m.index).split("\n").length;
        failures.push(`${file}:${lineNo} possible secret (${why}).`);
      }
    }
  }

  done(NAME, failures);
}

main();
