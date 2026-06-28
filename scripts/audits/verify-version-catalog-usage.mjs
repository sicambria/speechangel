#!/usr/bin/env node
// verify-version-catalog-usage.mjs
// Reproducibility gate: dependencies must go through the version catalog (gradle/libs.versions.toml),
// never a hardcoded "group:artifact:version" coordinate string inside a module build.gradle.kts.
//
// Detection matches the COORDINATE SHAPE only — a quoted "group:artifact:version" with two colons
// whose third (version) segment contains a digit. This deliberately does NOT trip on:
//   - catalog accessors:  alias(libs.plugins...), libs.kotlinx.coroutines.core, libs.versions.ktlint.get()
//   - project accessors:  api(projects.core.model)
//   - plugin ids:         id = "speechangel.android.application"   (no colon)
//   - paths / config:     "src/**/*.kt", "$rootDir/config/detekt/detekt.yml", minBound(70)
//
// Comments are stripped first so a commented-out example does not trip the gate.
// Scope: every tracked *.gradle.kts (build files), excluding anything under build/.
// Exit 0 if clean, 1 if a hardcoded coordinate is found.

import { trackedFiles, read, done } from "../_lib.mjs";

const NAME = "verify-version-catalog-usage";

// "group:artifact:version" — two colons; segments are dotted/dashed identifiers; the third segment
// must contain at least one digit (so it reads as a version, not a 3-part identifier).
const COORD = /"([A-Za-z0-9_.-]+):([A-Za-z0-9_.-]+):([A-Za-z0-9_.${}+-]*[0-9][A-Za-z0-9_.${}+-]*)"/g;

function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "") // block comments
    .replace(/(^|[^:])\/\/.*$/gm, "$1"); // line comments (avoid eating "://" in any URL)
}

function main() {
  const failures = [];
  const buildFiles = trackedFiles().filter(
    (f) => f.endsWith(".gradle.kts") && !f.includes("/build/")
  );

  for (const file of buildFiles) {
    const lines = stripComments(read(file)).split("\n");
    lines.forEach((line, idx) => {
      COORD.lastIndex = 0;
      let m;
      while ((m = COORD.exec(line)) !== null) {
        failures.push(
          `${file}:${idx + 1} hardcoded dependency coordinate "${m[1]}:${m[2]}:${m[3]}" — ` +
            `move it into gradle/libs.versions.toml and reference via the catalog.`
        );
      }
    });
  }

  done(NAME, failures);
}

main();
