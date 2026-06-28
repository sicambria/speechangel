#!/usr/bin/env node
// verify-foreground-service-types.mjs
// Android platform gate: if an AndroidManifest declares a microphone foreground service, it MUST
// declare foregroundServiceType="microphone" on that <service> AND request the
// FOREGROUND_SERVICE_MICROPHONE permission (Android 14+ requirement; the CAPTURE layer in
// research/04_build_and_reuse_plan.md §1).
//
// Skips gracefully (exit 0) if no AndroidManifest.xml exists yet — :app/:data are not scaffolded.
//
// Heuristic for "a microphone foreground service": a manifest that requests RECORD_AUDIO and
// declares at least one <service> is treated as a microphone-capture manifest and must satisfy the
// two requirements above. If neither is present we cannot assert intent, so we pass.
//
// Exit 0 if compliant or not applicable, 1 if a microphone FGS is declared without the type/perm.

import { trackedFiles, walk, read, exists, done, info } from "../_lib.mjs";

const NAME = "verify-foreground-service-types";

function manifestFiles() {
  // Prefer git-tracked manifests; fall back to a filesystem walk (covers untracked WIP).
  const tracked = trackedFiles().filter((f) => f.endsWith("AndroidManifest.xml"));
  if (tracked.length) return tracked;
  return walk(".").filter((f) => f.endsWith("AndroidManifest.xml"));
}

function main() {
  const failures = [];
  const manifests = manifestFiles().filter((f) => exists(f));

  if (manifests.length === 0) {
    info(`${NAME}: no AndroidManifest.xml found — skipped (exit 0). Re-runs once :app/:data land.`);
    process.exit(0);
  }

  for (const file of manifests) {
    const xml = read(file);
    const requestsMic = /RECORD_AUDIO/.test(xml);
    const hasService = /<service\b/.test(xml);
    if (!requestsMic || !hasService) continue; // not a microphone-capture manifest

    const hasMicType =
      /android:foregroundServiceType\s*=\s*"[^"]*microphone[^"]*"/.test(xml);
    const hasMicPerm = /FOREGROUND_SERVICE_MICROPHONE/.test(xml);

    if (!hasMicType) {
      failures.push(
        `${file}: declares a service + RECORD_AUDIO but no <service android:foregroundServiceType="microphone">.`
      );
    }
    if (!hasMicPerm) {
      failures.push(
        `${file}: declares a microphone foreground service but does not request FOREGROUND_SERVICE_MICROPHONE.`
      );
    }
  }

  done(NAME, failures);
}

main();
