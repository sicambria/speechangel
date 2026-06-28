#!/usr/bin/env node
// verify-listening-offmain.mjs
// Performance/architecture gate for the always-on listen loop.
//
// The per-frame wake-gating + recognition path (MFCC + DTW) is CPU-heavy and runs on every audio
// frame (~every 150 ms). It MUST NOT run on the main thread, or it janks the UI / risks an ANR and
// can starve the single AudioRecord (dropping audio / clipping a command onset). The loop is
// collected on the lifecycle (main) dispatcher, so the heavy step has to be offloaded explicitly.
//
// The heavy work is encapsulated in core:enrollment's pure `WakeGatedRecognizer.onFrame`. This gate
// enforces that ListeningService:
//   (a) routes recognition through that state machine (`pipeline.onFrame` / `.onFrame(`), and
//   (b) wraps that call in `withContext(Dispatchers.Default)`, and
//   (c) does NOT re-inline the heavy primitives on the collector (`.recognize(` / `.evaluate(`).
//
// Skips gracefully (exit 0) if ListeningService.kt doesn't exist. Exit 0 if compliant, 1 otherwise.

import { trackedFiles, walk, read, exists, done, info } from "../_lib.mjs";

const NAME = "verify-listening-offmain";

function serviceFiles() {
  const tracked = trackedFiles().filter((f) => f.endsWith("ListeningService.kt"));
  if (tracked.length) return tracked;
  return walk(".").filter((f) => f.endsWith("ListeningService.kt"));
}

function main() {
  const files = serviceFiles().filter((f) => exists(f));
  if (files.length === 0) {
    info(`${NAME}: no ListeningService.kt found — skipped (exit 0).`);
    process.exit(0);
  }

  const failures = [];
  for (const file of files) {
    const src = read(file);

    const callsOnFrame = /\.onFrame\s*\(/.test(src);
    if (!callsOnFrame) {
      failures.push(
        `${file}: recognition is not routed through WakeGatedRecognizer.onFrame — the heavy ` +
          `wake/recognition path must go through the off-main state machine.`
      );
    }

    // The onFrame call must be wrapped in withContext(Dispatchers.Default) { ... onFrame ... }.
    const wrappedOffMain =
      /withContext\s*\(\s*Dispatchers\.Default\s*\)\s*\{[^}]*\.onFrame\s*\(/s.test(src);
    if (callsOnFrame && !wrappedOffMain) {
      failures.push(
        `${file}: .onFrame(...) must run inside withContext(Dispatchers.Default){ ... } so the ` +
          `per-frame MFCC/DTW work stays off the main thread.`
      );
    }

    // Recognition primitives must NOT be re-inlined on the collector — they belong inside the pipeline.
    for (const [re, what] of [
      [/\.recognize\s*\(/, "recognizer.recognize(...)"],
      [/\.evaluate\s*\(/, "wakeWordGate.evaluate(...)"],
    ]) {
      if (re.test(src)) {
        failures.push(
          `${file}: calls ${what} directly — recognition must be encapsulated in ` +
            `WakeGatedRecognizer (kept off the main thread via one withContext boundary).`
        );
      }
    }
  }

  done(NAME, failures);
}

main();
