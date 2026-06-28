#!/usr/bin/env node
// verify-gradle-wrapper-pinned.mjs
// Reproducibility gate: the Gradle wrapper must be pinned to an explicit distribution version,
// and distribution-URL validation must be on.
//
// Fails if:
//   - gradle-wrapper.properties is missing
//   - distributionUrl is absent, or does not contain a pinned `gradle-<x.y[.z]>-(all|bin).zip`
//   - distributionUrl uses a non-pinned reference (e.g. "-latest-", "-nightly-", "-snapshot-")
//   - validateDistributionUrl is explicitly set to false
//
// Exit 0 if clean, 1 otherwise.

import { exists, read, done } from "../_lib.mjs";

const NAME = "verify-gradle-wrapper-pinned";
const PROPS = "gradle/wrapper/gradle-wrapper.properties";

function main() {
  const failures = [];
  if (!exists(PROPS)) {
    done(NAME, [`${PROPS} missing — the Gradle wrapper is not pinned/committed.`]);
    return;
  }
  const text = read(PROPS);
  const props = {};
  for (const line of text.split("\n")) {
    const m = line.match(/^\s*([\w.]+)\s*=\s*(.*)\s*$/);
    if (m) props[m[1]] = m[2].trim();
  }

  const url = props.distributionUrl || "";
  if (!url) {
    failures.push(`${PROPS}: no distributionUrl set.`);
  } else {
    // Properties files escape ':' as '\:' — normalize before matching.
    const normalized = url.replace(/\\:/g, ":");
    const pinned = /gradle-\d+\.\d+(?:\.\d+)?-(?:all|bin)\.zip/.test(normalized);
    const unpinned = /-(latest|nightly|snapshot|rc|milestone)-/i.test(normalized);
    if (!pinned || unpinned) {
      failures.push(`${PROPS}: distributionUrl is not pinned to an explicit version: "${url}"`);
    }
  }

  if (String(props.validateDistributionUrl).toLowerCase() === "false") {
    failures.push(`${PROPS}: validateDistributionUrl=false — distribution-URL validation must stay on.`);
  }

  done(NAME, failures);
}

main();
