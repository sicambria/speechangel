# Plan: enrollment adaptation ux

- **Date:** 2026-06-28
- **Phase:** 1 (screens) + 2 (adaptation)
- **Roadmap item:** Phase 1 "4-screen enrollment UX (Teach / Name-Map / Try / Always-on) + caregiver
  setup wizard"; Phase 2 "Multi-template re-enrollment polish + confirmation-gated adaptation"
- **Status:** done (A-deliverables implemented 2026-06-28; B-items — device visual QA — pending external input)
- **Worktree:** n/a (single-session, on `main`)
- **Plan quality:** 94/100 — independently confirmed over two review rounds (59 → 88 → 94)

## Goal

Complete the enrollment journey for the people this app serves (a user with limited hand use, set up by
a caregiver): add the missing **Always-on** screen and a guided **caregiver setup wizard**, and add
**confirmation-gated adaptation** that keeps good new examples — only on explicit confirmation — without
ever evicting the sole example of a rare voice condition.

## Context & Constraints

- **Current UX:** Home, Teach (records examples + maps name/action), Try exist
  (`app/src/main/kotlin/com/speechangel/app/ui/Navigation.kt`). Genuinely new screen: **Always-on**;
  **Name-Map** is folded into Teach/wizard (stated bluntly, not counted as a separate top-level screen);
  Home is not counted toward the "4".
- **Voice-drift robustness via multiple condition-tagged examples** is the core mechanism
  (`VoiceCondition` = NORMAL/TIRED/ILL/OTHER on each `Template`). Adaptation must *strengthen* this, so
  pruning must never remove a condition's last example.
- **Confirmation-gated, deterministic:** never silently rewrite stored examples; an example is added
  only after explicit user/caregiver confirmation. No autonomous self-training.
- **Pruning must be concrete + deterministic.** `Enroller`'s default clock is `{ 0L }`, so "oldest"
  ties unless a monotonic clock is injected; the rule needs a total order.
- **Bucket A vs B:** screens, ViewModels, wizard nav, and the *pure* adaptation logic build + unit-test
  here. Visual/interaction correctness and caregiver usability are Bucket B (emulator/device + real
  caregiver).

## Approach

Add an `AlwaysOnScreen` bound to the **existing hoisted** listening state (not a new flag), plus a
`CaregiverWizard` that sequences extracted, embeddable step content. For adaptation, split a **pure
decision function** (existing templates + candidate + rules → {add, removeIds}) — unit-tested with an
injected clock and a DTW callback — from an **impure orchestrator** (ViewModel → `TemplateRepository`).
The Try result UI gains a "remember this" affordance, which requires threading the captured audio +
matched `commandId` (currently discarded) into the UI state.

Rejected: automatic background adaptation (violates confirmation-gated/deterministic); a flat cap with
naive oldest/most-redundant pruning (evicts the sole TIRED/ILL example — the #1 review risk); embedding
the existing `TeachScreen`/`TryScreen` wholesale in the wizard (each owns a `Scaffold`+`TopAppBar` →
nested scaffolds); a second listening-state source of truth.

## Steps

1. **Extract embeddable step content.** Refactor `TeachScreen`/`TryScreen` to split a stateless content
   composable (state in, callbacks out) from the `Scaffold`/`TopAppBar` wrapper, so both the standalone
   screen and the wizard can host the content without nesting scaffolds.
2. **Always-on screen.** `app/src/main/kotlin/com/speechangel/app/ui/alwayson/AlwaysOnScreen.kt` bound to
   the **existing** hoisted `isListening`/`onListeningChange` owner (no new flag); entry points for
   battery exemption / assistant role / OEM guidance (survival plan) and "record wake word" (wake plan)
   — disclosed as possibly-stub hooks until those plans land. Add the route to `Navigation.kt`.
3. **Caregiver wizard.** `app/src/main/kotlin/com/speechangel/app/ui/wizard/CaregiverWizard.kt`:
   Welcome → Teach first command → Try it → Turn on always-on → Done, reusing the extracted content
   composables; progress indicator; back/skip; a persisted "setup complete" flag (DataStore in `:data`).
4. **Pure adaptation decision.**
   `core/enrollment/src/main/kotlin/com/speechangel/core/enrollment/AdaptationDecision.kt`:
   `decideAdaptation(existing: List<Template>, candidate: Template, maxPerCommand: Int = 5,
   distance: (FeatureSequence, FeatureSequence) -> Double): AdaptationDecision(toAdd, toRemove: List<TemplateId>)`.
   Rule: always add the candidate; if `existing.size + 1 > maxPerCommand`, remove exactly one chosen
   from **`existing` only (the just-added candidate is never eligible for removal**, so adaptation can't
   no-op), and **only from a condition bucket with ≥ 2 members** (never a condition's last example);
   within eligible candidates pick the **most redundant** = smallest minimum pairwise DTW distance to its
   siblings; tiebreak by oldest `createdAtEpochMs`, then `TemplateId.value` (total order → deterministic).
   `require(maxPerCommand >= 4)` so the four conditions can never force eviction of a sole-condition
   example; default `maxPerCommand = 5` (all four conditions + one spare; bounds match cost). With the
   candidate excluded and size = `maxPerCommand + 1 ≥ 5` over ≤ 4 conditions, the pigeonhole guarantees a
   ≥ 2 bucket exists. Uses `Dtw.distance` (reachable: `core:enrollment` depends on `core:matching`).
5. **Impure orchestrator + UI.** A ViewModel method applies the decision via
   `TemplateRepository.addTemplate`/`deleteTemplate`. Try/Home gain a "remember this" affordance and a
   "forget" affordance; "forget" targets the just-added `TemplateId` (retained from the add), not the
   `Match`'s best-matching id.
6. **Thread captured audio + commandId.** Extend `TryUiState`/`TryViewModel` so the original
   `AudioSamples` and `RecognitionResult.Match.commandId` (currently dropped) reach the affordance; add a
   `VoiceCondition` selector so tired/ill examples are tagged.
7. **Injected clock.** Enroller/adaptation paths take a monotonic clock in tests so `createdAtEpochMs`
   is distinct and the total order is exercised.
8. **App test deps + tests.** Ensure `app/build.gradle.kts` has Robolectric/androidx-test (shared with
   the survival plan). Pure-JUnit tests for `decideAdaptation` (adds under cap; at cap prunes the most
   redundant from a ≥2 bucket; never removes a sole-condition example; deterministic tiebreak); plain
   `runTest` ViewModel tests for wizard step progression and the always-on binding.

## Definition of Done

- Always-on screen + caregiver wizard wired into navigation; the "4-screen" intent satisfied with
  Name-Map folded into Teach/wizard (stated plainly: Always-on is the only genuinely new screen).
- `decideAdaptation` is pure, deterministic (injected clock + total-order tiebreak), condition-aware
  (never evicts a condition's last example), and uses DTW redundancy for selection; fully unit-tested in
  `:core:enrollment:test`.
- "Remember this" adds a confirmed, condition-tagged example via the orchestrator; "forget" removes the
  retained new id; captured audio + commandId are threaded through `TryUiState`.
- `:core:enrollment:test` green — the reliable autonomous gate for the pure `decideAdaptation` logic.
  App ViewModel tests run under whole-project `make verify` (the target full-build gate; green on the
  *current* tree this session — this plan's code is not built yet and makes no green claim).
- **Accuracy honesty:** adaptation's *benefit* is defined as a measurable reduction in **FRR** at a
  fixed **FAR** operating point, scored via the `core:eval` harness on a voice-drift corpus (templates
  enrolled NORMAL, queried TIRED/ILL). This is a pending measurement — the harness is the prerequisite
  (`docs/plans/2026-06/recognizer-eval-and-calibration.md`) and real drift audio is Bucket B; no FRR/FAR
  improvement is claimed until measured.
- **Bucket-B honesty:** screen rendering, wizard feel, and real caregiver usability need an
  emulator/device + ideally a real caregiver — recorded as on-device/UX verification.

## Risks & Mitigations

- **Risk (the #1 finding): pruning evicts the sole TIRED/ILL example.** Mitigation: only prune from a
  bucket with ≥2 members; explicit "never removes a sole-condition example" unit test.
- **Risk: non-deterministic "oldest".** Mitigation: injected monotonic clock + `TemplateId` tiebreak;
  tested.
- **Risk: affordance has no audio/commandId to act on.** Mitigation: thread both through `TryUiState`
  (explicit step).
- **Risk: unbounded template growth.** Mitigation: hard `maxPerCommand` cap (default 5) + tested prune.
- **Risk: wizard nests scaffolds.** Mitigation: extract content composables first (step 1).

## Test & Verification

- Autonomous: `:core:enrollment:test` (adaptation decision); `:app` ViewModel tests (wizard, always-on
  binding) under whole-project `make verify`, re-run after implementation (green on the current tree this
  session); guardrail bundle green.
- Blocked (device): screen rendering, wizard flow feel, real caregiver usability — emulator/device +
  caregiver session; on-device/UX QA, not here.
