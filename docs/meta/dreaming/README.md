# Dreaming — meta-scan cadence

A recurring scan over this project's own incident/retro corpus that clusters failure classes and
proposes the next gate to promote up the ladder (`AGENTS.md` §0). Started **empty** — copy the
cadence and the taxonomy, never another project's reports (meta §5.1).

## Cadence

Run monthly alongside the retro (`docs/ai/retro/2026-06/2026-06.md`) and the maturity re-score. Each
report is dated and bucketed: `docs/meta/dreaming/<YYYY-MM>-dreaming.md`.

## Prevention Taxonomy (cluster each recurring class onto a level)

- **L0 Accept** — too rare / too cheap to guard; record and move on.
- **L1 Document** — add a behavior/technical rule (`ACTIVE_DEV_RULES`).
- **L2 Contract** — add an advisory `workflow-boundary-contracts.json` entry.
- **L3 Gate** — add a `scripts/audits/<verifier>.mjs` hard gate.
- **L4 Test** — add a RED→GREEN test that fails on the class.
- **L5 Architectural** — restructure so the class is impossible by construction.

## Promotion criteria

Promote a class up a level only when it **recurs with low false positives**. One occurrence is L0/L1;
repeated catches justify a contract, then a gate.

## Reports

_None yet._
