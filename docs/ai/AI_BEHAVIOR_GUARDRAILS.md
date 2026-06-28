# AI Behavior Guardrails (agent-neutral)

These are the **universal** behavior rules — they apply to any AI agent working in this repo,
independent of which model or harness is driving. They are about *how* to work, not *what* the code
does. Technical, code-level rules live in `docs/ai/ACTIVE_DEV_RULES.md` and are promoted there only
after an incident justifies them.

<!-- BUG_RCA_DISCOVERY_GATE: ANY failure found ANY way triggers the Incident Protocol in
     AGENTS.md §4. "Found incidentally" is never an exemption. -->

---

## The rules

1. **Read before you write.** Start every session at `docs/ai/START_HERE.md`, then `AGENTS.md`.
   After a context compaction, re-read both (the session-start invariant). Never act on a stale
   mental model of the repo.

2. **Ground every claim in the repo or a primary source.** Cite the file/line or the
   `research/*.md` finding. Do not assert behavior you have not checked. "I believe" is a signal to
   go verify, not to proceed.

3. **A failure is structured data — never a silent fix.** Any bug, build break, red gate, or
   console error triggers the 9-step Incident Protocol (`AGENTS.md` §4). Check `docs/errors/INDEX.md`
   first; you may already have the answer.

4. **Root-cause, then scan for the class.** Fix *why*, not just *where*, and search the whole
   codebase for the same failure class before closing. One missing foreground-service type usually
   means another manifest is wrong too.

5. **RED→GREEN.** Write the failing test first where a test applies; watch it fail; then fix. A fix
   without a test is an unguarded fix.

6. **Close the loop or the commit is blocked.** An incident note with TBD prevention links, missing
   sections, or template placeholders fails `knowledge:check`. Document → prevent → integrate into
   planning → decide on a guardrail. Skipping a dimension must be an on-record `skip`, never an
   accident.

7. **Reproducibility is non-negotiable.** No dynamic dependency versions, pinned Gradle wrapper, all
   deps through the version catalog. These are gate-enforced (`scripts/audits/*`) — do not work
   around them.

8. **Stay deterministic where the product demands it.** SpeechAngel's action layer is a fixed
   command→action table, never an autonomous agent. Do not introduce autonomy into the action path —
   it is a Play-policy make-or-break line (`research/04_build_and_reuse_plan.md` §7).

9. **Plan inside a worktree for substantive work.** Non-docs changes belong in a plan inside a
   worktree, not directly on `main`. Name the Definition of Done (tests + the relevant gate).

10. **One commit closes one loop.** Fix + tests + incident note + rule/contract updates land
    together, so the memory and the code never drift apart.

11. **Promote on evidence, not intuition.** A rule climbs the ladder (known-error → ACTIVE_DEV_RULES
    → contract → hard gate) only after it catches a recurring class with low false positives. Do not
    pre-emptively add a gate that cannot yet fire.

12. **Prefer backtick code-paths to relative links in docs.** Write `docs/errors/INDEX.md`, not a
    relative markdown link. Relative links break when files move and red the docs-integrity gate.
    Use temporal `YYYY-MM` buckets for dated artifacts.

13. **Be honest about "done".** "Validated a lesson" is not "validated a port" (meta §10.1). Report
    what actually ran green standalone, and name what was deferred. A partial result logged as
    partial is fine; a partial result claimed as complete is the rot the system exists to prevent.
