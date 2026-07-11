# Piping a long-running background job through `tail -N` buffers all output — lost the composite result on session teardown

**2026-07-11.** During the population-split journey I launched `typical_composite.py` (the ~15 min
wavlm-large × 4-condition embedding job) in the background as `... python typical_composite.py 2>&1 |
/usr/bin/tail -30`. `tail -N` (unlike `tail -f`) is a **batch** filter: it buffers all stdin and prints
only at EOF, so the task output file stayed **0 bytes** for the whole run (no progress visibility), and when
the session was **torn down mid-run** the job was killed before EOF and the entire computed result was lost.
The one missing deliverable piece (fresh per-domain D5/D1/D4/D6 typical bands) was salvaged from the carried,
committed 2026-07-10 composite numbers rather than re-run — correct and honest, but a fresh run was lost, and
re-running under the then-high host load (`loadavg` 28.9) was ruled out per the user's "do not risk host
instability." Cost ~10 min salvage; severity low (reconstructable, no corruption).

- **Trigger:** every `Read` of the background job's output file showed it empty (indistinguishable from
  "not started"); the process-liveness check (`ps -o %cpu,etime,stat`) showed it alive at 388% CPU, then a
  session teardown killed it with no flushed output.
- **Automation Links:** `CLAUDE.md` §1.3 (background-work hygiene), `scripts/eval/ssl_frontend_spike/`
  (`_ceiling_cache/*.json` incremental-checkpoint pattern).

## Summary
A multi-minute compute job's stdout was pipelined through a batch `tail -N`, so it produced no interim
output and lost everything when the session tore it down before EOF. The result had to be reconstructed
from prior committed numbers.

## Root Cause
`tail -N` must see EOF to know which N lines are last, so it holds all stdout in a buffer and prints once at
exit — the opposite of `tail -f`. The buffering was masked because the short T2/T3 harnesses in the same
session completed normally and printed, so the trap only surfaced on the one long job that hit a teardown.

## Rerun Analysis
Correct pattern for a long background job I want to watch: let it write full stdout to the task file (no
`tail`), or `stdbuf -oL … | tee <file>` so lines flush as produced. For results that must survive a
teardown: checkpoint each domain to the `_ceiling_cache` JSON as it completes, not only at `main()` exit (the
harnesses `json.dump` only at the end — also lost if killed mid-run). Monitoring an empty *buffered* file is
a false "not started" signal; process liveness is the source of truth (CLAUDE.md §1.3).

## Prevention
Never pipe a long-running background job through `tail -N`. Redirect full stdout to the output file; cap
size at read time (`Read` the tail) or use `tee` + line-buffering. Prefer incremental checkpointing for
multi-minute compute whose result must survive a teardown.

## Guardrail Updates
No new automated gate (shell hygiene, not a repo invariant — a short job with `tail -N` is fine). Captured
as an operating-rule cross-reference: `CLAUDE.md` §1.3 (background-work hygiene) is the home for the "don't
batch-`tail` a long background job; use process liveness + incremental checkpoints" habit, and the
`_ceiling_cache/*.json` pattern under `scripts/eval/ssl_frontend_spike/` is the checkpoint mechanism to
extend (write per-domain, not per-run).

## Planning Integration
Concrete artifact: the deferred **D5-reverb / D3-ambient robust-corpus re-measurement** (the honest typical
800→900 next lever, `docs/testing/2026-07-11_population-split-800-900.md` §5, tracked under
`docs/plans/2026-07/uaspeech-acquisition.md`'s sibling typical-track work) gains a **Definition of Done**
clause — when run, it must **write each domain's band to its `_ceiling_cache` JSON as it completes**, so a
teardown mid-run costs at most one domain rather than the whole run.

## Shift-Left Decision
**Decision: skip (advisory habit, no gate).** A `tail -N` in a background pipeline is a judgement smell, not
a mechanically-detectable defect (short jobs use it correctly), so a hard gate would false-positive. Shift
left via the CLAUDE.md §1.3 habit + the per-domain checkpoint DoD clause above, not a verifier.

## Automation Follow-Up
Optional low-value: a `scripts/eval/run_bg.sh` wrapper that runs a python job with `stdbuf -oL … | tee
<file>` and rejects a bare `tail -N`. Deferred in favour of the habit.
