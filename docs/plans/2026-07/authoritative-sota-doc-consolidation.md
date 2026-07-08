# Plan: One Authoritative SOTA Document

- **Date:** 2026-07-08
- **Phase:** n/a (documentation governance)
- **Roadmap item:** Consolidate the fragmented SOTA docs into one authoritative reference (supports the
  `docs/ROADMAP.md` "SOTA competitive bar — derived items" section).
- **Status:** done (A-deliverables implemented 2026-07-08)
- **Worktree:** n/a (docs-only, on main)
- **Plan quality:** 95/100 (two adversarial reviewers + advisor-gated; working plan at
  `~/.claude/plans/foamy-splashing-koala.md`)

## Goal

Replace the fragmented SOTA material (5 docs, 3 scoring systems, a broken "supersedes" claim, cross-doc
number contradictions) with **one authoritative SOTA reference** that is factually accurate,
evidence-ranked, internally consistent, config-explicit, and liftable into the academic paper.

## Context & Constraints

- Non-negotiables: **config-explicit** numbers (name front-end/corpus/regime/on-off-device); the
  accuracy-honesty rule (FRR + FAR, never a bare %); EVAL-002/003 banked/not-banked discipline;
  on-device + language-independent framing preserved.
- **Fix-peers / flag-evidence principle:** fix contradictions in authoritative peer docs
  (`docs/product/*sota*`, the scorecards); only *flag* (never edit) contradictions living in
  `docs/testing/**` or `docs/research/experiments/**` — those trip the hard EVAL citation/fidelity gates
  in `scripts/audits/verify-sota-measurement.mjs`.
- Related: `docs/product/2026-07-08_sota-wake-word-reference.md` (the authoritative doc),
  `docs/product/2026-07-06_sota-frr-far-and-real-life-scorecard.md`,
  `docs/product/2026-07-08_sota-domain-bands.md`, `docs/product/2026-07-08_score-band-pathway.md`,
  `docs/ROADMAP.md`.

## Approach

Elevate the strongest existing artifact (`docs/product/2026-07-08_sota-wake-word-reference.md`) into the
authoritative doc: recover the retired competitive-bar's unique content (7-axis field ranking, PD-DWS
technique mining, Euphonia proof-point, governing comparability caveat, R-SOTA summary), add a short
config-explicit "where SpeechAngel stands" section (§11) with a 3-way banked/deployable honesty ledger,
reconcile the three scoring systems, and add paper-reconciliation notes. Retire the competitive-bar
(superseded header, kept on disk); repoint all inbound refs. **Rejected:** a fresh mega-doc absorbing the
scorecards — it couples the external-survey and internal-scoring update cadences; the user chose a
field-survey spine that links out.

## Steps

1. Rewrite `docs/product/2026-07-08_sota-wake-word-reference.md` → authoritative doc (retitle, §0–§14). ✓
2. Mark `docs/product/2026-07-06_sota-competitive-bar.md` SUPERSEDED (kept on disk). ✓
3. Fix the inverted baseline label in `docs/product/2026-07-08_sota-domain-bands.md` (line 72). ✓
4. Update `docs/DOC_TOC.md` (add authoritative doc + the 2 missing 07-08 docs; mark competitive-bar
   superseded). ✓
5. Repoint all inbound refs (`docs/ROADMAP.md` ×2, the frr-far scorecard,
   `docs/product/2026-07-06_cp-requirements-spec.md`, `docs/product/2026-07-08_sota-domain-bands.md`). ✓
6. Guardrails green + finished-doc number audit + peer-consistency re-check. ✓

## Definition of Done

- One authoritative SOTA doc exists, config-explicit and non-contradictory with its kept peers.
- The doc states the **shipped baseline of record as FRR 75.7% @ FAR 4.6%** (static MFCC-DTW, TORGO
  speaker-dependent, held-out EVAL-002; dysarthric rank-1 59.2%), with the `delta_delta` variant
  (FRR 78.3%) labeled as such — never as shipped. Every FRR/FAR figure names its config, corpus, regime,
  and on/off-device status.
- The banked-vs-deployable honesty ledger is present: only the MFCC-DTW floor and the Picovoice
  cross-speaker lower bound are banked-deployable; every sub-5% FRR result is labeled
  off-device/not-banked; the CP-3 = 0/200 and CP-0 = 0/200 deployment gate is stated.
- `node scripts/audits/run-all.mjs` = 11/11 PASS (especially `docs:check` + `verify-sota-measurement`).

## Risks & Mitigations

- **Risk:** the new doc contradicts a kept peer on the load-bearing baseline number. **Mitigation:** fixed
  `docs/product/2026-07-08_sota-domain-bands.md` line 72; ran a peer-consistency grep across all 3 kept
  scorecards (zero residual). **Rollback:** `git revert` the docs commits (no code touched).
- **Risk:** editing a testing doc trips the hard EVAL citation/fidelity gates. **Mitigation:**
  fix-peers/flag-evidence principle — no `docs/testing/**` file edited; contradictions there (the E17
  vocab flip, the stale `RESULTS.md` note) are only *flagged* in §11.
- **Risk:** stale/future external citations weaken the paper lift. **Mitigation:** ZP-KWS
  (arXiv 2606.20106) is flagged for re-verification before lifting.

## Test & Verification

- `node scripts/audits/run-all.mjs` → **11/11 PASS** (verified 2026-07-08; `docs:check` green after
  fixing three dangling backtick paths — the sibling `speechangel-paper` repo and an abbreviated
  `MfccExtractor.kt` path).
- Finished-doc number audit: grep of `59.2 / 55.4 / 75.7 / 78.3 / 89.2 / 87.5 / 71.9 / 3.1% / 25%` in the
  doc — each carries config + context (verified).
- Peer-consistency grep across the 3 kept scorecards — zero residual FRR/FAR contradiction after the
  `domain-bands` line-72 fix (verified).
- **No recognizer/DSP/threshold code changed** → no `make bench-picovoice` re-run needed. This is
  docs-only: the FRR/FAR figures are cited from existing `docs/testing/*` reports, not newly measured, so
  there is no benchmark delta to report.
