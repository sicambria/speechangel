<!-- Plan index + feasibility triage. Exempt from the plan-workflow completeness gate (INDEX.md). -->
# Plan index & feasibility triage

Created 2026-06-28 as the backbone of the Phase 0/1/2 planning push; **extended 2026-07-05 to cover
Phase 3** (Delight & reach). Every remaining Phase 0/1/2/3 ROADMAP item is triaged by how far an
*autonomous* coding session can take it:

- **A — fully autonomous:** plan + implement + `make verify` green on this host.
- **B — code-yes / DoD-needs-external-input:** the harness/feature is buildable here, but the
  acceptance criterion needs an external input the host lacked at plan time (real dysarthric audio, a device).
- **C — external-only:** needs an account/service/large external model; plan + minimal scaffold +
  documented blocker is the honest ceiling.

> Plan quality (target **> 94/100**, independently reviewed) is orthogonal to A/B/C feasibility. A
> Phase-0 measurement plan can score 96 *and* be blocked on real audio — the plan says so explicitly.

## Triage

| ROADMAP item | Phase | Bucket | Carrying plan |
|---|---|---|---|
| Complete deltas: add ΔΔ acceleration, delta defaults | 0 | A | `docs/plans/2026-06/recognizer-eval-and-calibration.md` |
| Measure FRR/FAR (eval harness + corpus + report) | 0 | B (harness A; numbers blocked) | `docs/plans/2026-06/recognizer-eval-and-calibration.md` |
| Feature front-end bake-off (MFCC vs +Δ+ΔΔ vs PLP) | 0 | A (compare) / B (winner-on-real-voices) | `docs/plans/2026-06/recognizer-eval-and-calibration.md` |
| Per-command FAR-budget threshold tuning | 2 | A | `docs/plans/2026-06/recognizer-eval-and-calibration.md` |
| Stage-1 VAD gate → enrolled DTW wake word | 1 | A (logic) / B (battery-on-device) | `docs/plans/2026-06/stage1-wake-word-gate.md` |
| Battery-optimization exemption flow | 1 | A (code) / B (system dialog on device) | `docs/plans/2026-06/always-on-survival.md` |
| Assistant role + reboot survival (BOOT_COMPLETED) | 2 | A (code) / B (reboot on device) | `docs/plans/2026-06/always-on-survival.md` |
| Per-OEM autostart guidance (DontKillMyApp) | 2 | A | `docs/plans/2026-06/always-on-survival.md` |
| 4th screen (Always-on) + caregiver setup wizard | 1 | A (build/unit) / B (visual on device) | `docs/plans/2026-06/enrollment-adaptation-ux.md` |
| Multi-template re-enrollment + confirmation-gated adaptation | 2 | A | `docs/plans/2026-06/enrollment-adaptation-ux.md` |
| Prominent mic disclosure + Play Permission Declaration | 2 | A (in-app dialog) / C (Play form) | `docs/plans/2026-06/policy-and-path-a.md` |
| Optional Path-A intact-speech mode (Vosk/sherpa-onnx) | 2 | C | `docs/plans/2026-06/policy-and-path-a.md` |
| QbE embedding enhancement (few-shot, milder impairment) | 3 | A (seam+selector) / C (trained encoder) | `docs/plans/2026-06/phase3-matcher-enhancements.md` |
| Vocabulary-distinctness helper (warn on close commands) | 3 | A (pure) / B (confusion correlation on real voices) | `docs/plans/2026-06/phase3-matcher-enhancements.md` |
| Far-field / noise front-end | 3 | A (logic) / B (real far-field/noise gains) | `docs/plans/2026-06/phase3-matcher-enhancements.md` |
| Shareable command packs | 3 | A | `docs/plans/2026-06/phase3-reach-and-release.md` |
| F-Droid + Play release | 3 | A (scaffold) / C (accounts + signing key + RFP) | `docs/plans/2026-06/phase3-reach-and-release.md` |
| whisper.cpp batch dictation (optional) | 3 | A (interface+Noop) / C (native model+runtime) | `docs/plans/2026-06/phase3-reach-and-release.md` |
| External-asset shortlist (corpora, encoder, dictation/Path-A/far-field models) | 0/1/2/3 | B/C (all seams built; assets absent) | `docs/plans/2026-06/external-asset-acquisition.md` |

## Plans

- `docs/plans/2026-06/recognizer-eval-and-calibration.md` — the accuracy theme (new `core:eval`).
- `docs/plans/2026-06/stage1-wake-word-gate.md` — Stage-1 low-power gate + enrolled wake word.
- `docs/plans/2026-06/always-on-survival.md` — battery exemption, reboot survival, OEM autostart.
- `docs/plans/2026-06/enrollment-adaptation-ux.md` — always-on screen, caregiver wizard, adaptation.
- `docs/plans/2026-06/policy-and-path-a.md` — mic disclosure/Play + optional Path-A scaffold.
- `docs/plans/2026-06/phase3-matcher-enhancements.md` — QbE embedding, vocab-distinctness helper,
  far-field/noise front-end (Phase 3; authored 2026-07-05).
- `docs/plans/2026-06/phase3-reach-and-release.md` — shareable command packs, F-Droid/Play release
  scaffold, whisper.cpp batch dictation (Phase 3; authored 2026-07-05).
- `docs/plans/2026-06/first-real-frr-far-torgo.md` — ✅ **DONE 2026-07-06** — **the 2026-07-06 critical
  path** (self-scored 97/100, advisor-gated): pulled TORGO → ran `core:eval` speaker-dependent →
  produced the first real (non-`SYNTHETIC`) FRR/rank-1 report (**GO**: rank-1 55.4% dysarthric / 74.6%
  control, 10–40× chance — hypothesis holds, single-template baseline not yet deployable), then an
  emulated on-device e2e run + a Doze/reboot soak (both at the emulator ceiling; physical-device
  metrics documented as such). Score: evidence 29/30, structure 15/15, concreteness 20/20, risk 15/15,
  test 10/10, scope 10/10. Reports under `docs/testing/2026-07-06_*.md`.
- `docs/plans/2026-07/realistic-conditions-sim-and-rejection-scoring.md` — ✅ **DONE 2026-07-06**
  (self-scored 96/100, advisor-gated): a realistic-condition **simulation harness** (`core:eval`:
  `AudioAugment`/`Conditions`/`ConditionEval`/`AmbientFar`) + a first-principles **rejection-scoring**
  experiment. Part 1 measured the noise/reverb/band-limit degradation grid and the first **ambient
  FA/hour proxy** (~82 FA/hr, ~160× budget) on real TORGO. Part 2 pre-registered common-mode rejection
  normalization (H1) and **refuted** it (control χ²=39.7, p<0.001 — honest negative, no runtime change);
  codified EVAL-003. Reports: `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`,
  `docs/errors/2026-07/2026-07-06_common-mode-rejection-refuted.md`.
- `docs/plans/2026-06/external-asset-acquisition.md` — the cross-phase acquisition/integration runbook
  for the ROADMAP "External-asset shortlist": QbE encoder + CC-BY training data, whisper.cpp/sherpa-onnx
  dictation + Path-A models, dysarthric-inclusive corpora (TORGO/SAP/UASpeech/EasyCall), far-field
  RIR/noise augmentation. Each row = license tag + acquisition action + dormant seam (`path:line`) +
  integration check (authored 2026-07-06).

## Product maturity (2026-07-06)

The product was scored **442/1000 — pre-alpha** in `docs/product/2026-07-06_product-maturity-scorecard.md`
(a **product**-value axis, distinct from the 555/1000 AI-framework axis). Headline: the core is real
and wired, but its accuracy is unmeasured on real voices and it has never run on a device. The scorecard
resets priority: **first real FRR/FAR (TORGO) → one on-device end-to-end run → always-on survival soak**
outrank every open Phase-3 enhancement below. See `docs/ROADMAP.md` "Critical path".

## Definition of "done" for this push (honesty contract)

1. Every plan above is authored and **independently reviewed past 94/100** (defect-list driven).
2. Every **A** deliverable is implemented and `make verify` is green.
3. Every **B/C** item ships its maximal autonomous deliverable with the external blocker documented.
4. No fabricated FRR/FAR numbers, no fake corpus, no score inflation. Blocked is reported as blocked.

## Status (2026-06-28)

**(1) Plans — ✅ done.** All 5 independently confirmed > 94 over two review rounds: eval 95, wake 95,
survival 95, ux 94, policy 95.

**(2) A-deliverables implemented + verified (`make verify` green, `:core:*:test` green):**
- ✅ `core:dsp` ΔΔ acceleration (`DeltaOrder`) + `StreamingEnergyGate`.
- ✅ `core:eval` module: `Evaluator` (FRR + FA count), `ThresholdCalibrator`, `FrontEndBakeoff`,
  `SyntheticCorpus`, `EvalReport`, + `docs/testing/frr-far-report-template.md`.
- ✅ `WakeWordGate` + `ReservedCommands` (Stage-2 exclusion).
- ✅ `SpeechBackend` neutral interface + `TemplateSpeechBackend` adapter + `NoopPathABackend`.
- ✅ `decideAdaptation` (condition-aware, deterministic pruning).

**(2) A-deliverables — app layer NOW implemented (`make verify` + 9/9 guardrails green):**
- ✅ `data`: `ListeningPreferences` (DataStore enable/disclosure/setup flags) + `AudioRecorder.stream()`.
- ✅ `app` Compose: `AlwaysOnScreen`, `CaregiverWizard`, `MicDisclosureDialog`, `LicensesScreen`,
  wired into navigation; `MainActivity` now persists the listening toggle (the write-path the review
  flagged).
- ✅ `app` services: `OemAutostart` (pure, unit-tested), `BatteryOptimization`, `AssistantRole`
  (API-guarded), `BootReceiver` (legal tap-to-resume, not FGS-from-boot) + manifest registration.

- ✅ Wiring gaps (2026-06-28): `ListeningService` two-stage streaming loop (rolling 750ms wake window
  via `WakeWordGate` + `Vad`, template `StateFlow` cache, `AudioSamples.concat`); `MicDisclosureDialog`
  gated on `preferences.micDisclosed` before first mic permission; TryScreen "Remember this" affordance
  (`TryViewModel.rememberThis()` → `decideAdaptation` → `TemplateRepository`). All new tests green;
  `make test` + `make build` + 9/9 guardrails pass.

**(3) B/C blockers documented:** real FRR/FAR (needs a labeled dysarthric-inclusive corpus), on-device
survival (reboot/Doze/OEM), Play Permission Declaration Form (account), real Vosk/sherpa Path-A backend.

**(4) Honesty:** synthetic eval output is banner-marked SYNTHETIC; no real numbers fabricated.

## Phase 3 planning batch (2026-07-05)

A separate, later batch — **do not fold into the 2026-06-28 push above** (whose ">94, two-round-
reviewed, all 5" claim is about those five plans only and stays true as written).

**Provenance (honest):** the two Phase 3 plans were **authored + self-scored 93/100 and advisor-
reviewed once on 2026-07-05** — not the two-round, >94 process the Phase 0/1/2 plans went through. 93 is
the honest ceiling here: Phase 3 is exploratory and mostly **Bucket B/C** (QbE needs an external trained
encoder; far-field/dictation/release need real corpora, native models, or store accounts), so the plans
draw those boundaries rather than invent precision. Both are docs-only; no Phase 3 code was implemented
in this batch (the request stopped at "record").

- `phase3-matcher-enhancements.md` (93) — QbE embedding (A seam / C encoder), vocab-distinctness helper
  (A / B), far-field front-end (A / B). All three are opt-in; the MFCC-DTW core stays the default. Each
  item's adoption gate is an **FRR + FAR delta vs the MFCC-DTW baseline** on the landed `core:eval`
  harness — pending a real corpus.
- `phase3-reach-and-release.md` (93) — command packs (A; re-enroll model, `DeviceAction.fromId`-
  validated), F-Droid/Play scaffold (A up to the signing/account wall — C), whisper.cpp dictation (A
  interface / C model; a *new* `DictationBackend`, not the command-oriented `SpeechBackend`). None
  touches the matcher, so none changes FRR/FAR.

**Bucket-A implemented 2026-07-05.** Every autonomously-implementable Phase 3 slice is built, tested,
and committed: `VocabularyDistinctness` + its Teach-flow nudge (core:matching/app); the QbE
seam+selector+`NoopQbeEncoder` and `DictationBackend` (core:enrollment, both dormant); the
`MfccConfig.noiseReduction` far-field front-end + bake-off wiring (core:dsp/core:eval); per-command
threshold persistence + pass-through (`ListeningPreferences`/`WakeGatedRecognizer`/`ListeningService`);
`data/pack` command packs + `CommandPackScreen`/`CommandPackViewModel` (app); and the F-Droid/Play
release scaffold + R8 (`:app:assembleRelease` green). Each module's test task + detekt + spotless +
10/10 guardrails ran green per commit; `make verify` green.

**Two items reached `[x]`** (code-complete, wired to a user entry point, verify-green — only on-device
visual QA/external validation left, matching the Phase-1 enrollment-UX precedent): the
vocabulary-distinctness helper and shareable command packs. The other four stay `[~]` because the
deliverable needs an absent resource. **No B/C item is checked off** — no real FRR/FAR, no bake-off
winner, no trained encoder, no whisper model, no store account is claimed.

**Not planned (deliberate):** the Workflow-track "CI running green on a real GitHub Actions run" item is
implemented (`.github/workflows/ci.yml`), only unobserved on an actual Actions run — a full plan is
overkill; it is noted here, not planned.

## External-asset acquisition plan (2026-07-06)

`external-asset-acquisition.md` — **self-scored 96/100, advisor-cleared 2026-07-06** (planmax loop:
draft → resolve every seam `path:line` against the working tree → score → advisor gate). It fills the
one previously-unplanned ROADMAP section (the "External-asset shortlist", `ROADMAP.md:145`); the other
17 items already carry the seven plans above, so re-planning them is deliberately out of scope.

Score breakdown: evidence grounding 29/30 (every seam citation resolves; corpus size figures carried
from the roadmap sweep, not independently re-verified — the −1), structure 15/15, concreteness 18/20
(several checks are inherently deferred to when the external asset lands), risk/reversibility 15/15,
test/shift-left 10/10, scope discipline 10/10. **Docs-only + acquisition:** no ROADMAP checkbox flips —
no corpus, encoder, or model was acquired; the plan documents *how*, honoring INDEX point 4.

## Plan-body re-audit (2026-07-06)

An "implement all open plans" pass re-audited the four open plans (3 active + 1 planned)
**against the working tree, not the status lines** (a general-purpose agent cross-checked every
Bucket-A deliverable to a `path:line`). Result: all four "done"-status Phase-0/1/2 plans are accurate,
and Bucket-A across the active plans was ~complete — with **three findings** the 2026-07-05 status
lines over-implied (one built, one documented boundary, one deliberate descope):

1. **`phase3-reach-and-release` step 13 — dictation stub screen (was MISSING → now BUILT).** Only the
   `DictationBackend` seam + Noop + tests had landed; the "dictate to a text field" stub screen had not.
   Implemented 2026-07-06: `app/src/main/kotlin/com/speechangel/app/ui/dictation/DictationScreen.kt` +
   `DictationViewModel` (injects the
   neutral backend, `NoopDictationBackend`-bound in `RecognitionModule`), routed from Home, off the
   command path. `:core:enrollment:test` + `:app:assembleDebug` + `make static` + guardrails green.
2. **`phase3-matcher-enhancements` step 8 — QbE live DI binding (documented boundary, NOT built).** The
   DoD's testable clause (selector builds + unit-tested) is already met by `SpeechBackendSelector`. The
   further "DI binding selecting the backend from a persisted preference" is **structurally not
   constructible as written** (both backends need runtime-loaded data absent at Hilt graph time; nothing
   injects `SpeechBackend`) and would be dead code while the encoder is Noop. Left dormant by design;
   recorded as a boundary in that plan's Implementation note. Wiring it live = an optional future
   `ListeningService` refactor, gated on a real encoder.
3. **`phase3-reach-and-release` Item A — optional same-speaker template export (deliberate descope).** The
   Item-A DoD's *optional* "same-speaker templates via `FeatureCodec`" clause is unbuilt: `PackCommand` is
   `(label, actionId)` only. Technically Bucket A (`FeatureCodec` exists), but it adds a privacy-sensitive
   audio-derived-data export surface needing consent UX, against the plan's definitions-only-by-default
   non-negotiable, for the niche same-speaker-new-device case. Descoped consciously (the shipped
   definitions-only path is the intended default); recorded in that plan's Descope note. Buildable on
   request if a consent flow + real need justify it.

No Bucket-B/C item was touched; no FRR/FAR number, corpus, encoder, model, or store account was claimed.

## Reconciliation (2026-07-05)

The five Phase 0/1/2 plans were **reconciled 2026-07-05** (not re-reviewed — their >94 provenance
holds): stale "code is not built yet" DoD lines removed to match the code that landed 2026-06-28;
`always-on-survival` moved `planned`→`done` and `recognizer-eval-and-calibration` `planned`→`active`
(harness landed, threshold app-persistence still pending) to match reality; explicit **Rollback** lines
added to each Risks section; the `EnergyVad` ratio citation corrected to `config.energyRatioOverNoise`
(`Vad.kt:30`, applied `:57`).

## Honest TORGO improvements (2026-07-06)

`docs/plans/2026-07/torgo-eval-honest-improvements.md` — **self-scored 98/100, advisor-gated, DONE
2026-07-06**. planmax follow-through on the TORGO baseline: it does **not** invent a rosy number — it
fixes the eval's in-sample threshold-selection bias and reports the honest held-out result.
- **Correctness finding:** the report/`CLAUDE.md` "multi-template **vote**" claim was a no-op — the
  matcher is 1-NN min-distance (`TemplateMatcher.kt:42`), which the eval already models. Incident:
  `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md`; new rule **EVAL-002**.
- **D1 (held-out per-command calibration):** honest **non-improvement** — train-fit to FAR≤5%, held-out
  FAR balloons to 24–34%; global threshold wins at matched FAR (held-out FRR 78.3% ≈ in-sample 77.9%).
- **D3 (front-end bake-off, real voices):** static MFCC (`none`) is the best held-out rank-1 cell
  (59.2% vs `delta_delta` 55.4%), but the margin is within sampling error — a **directional** hypothesis
  (static best/tied and NR worse in all 3 speakers) needing a paired test, not an established gain.
- **D2 (deployment slice ≤25 cmds):** held-out FRR 70.7% (F01+F04) vs 78.3% tail-blended.
- Report regenerated: `docs/testing/2026-07-06_frr-far-torgo.md`. Items 2 & 3 (device) unchanged.

## Picovoice wake-word-benchmark placement (2026-07-06)

`docs/plans/2026-07/picovoice-wake-word-benchmark.md` — ✅ **DONE 2026-07-06**. First head-to-head
placement on a **standard, public** benchmark (the scorecard's named gap). Key call: **decompose by
metric** — FA/hour is in-regime (headline), cross-speaker miss-rate is an out-of-regime lower bound.
- **Harness (`core:eval`):** `PicovoiceCorpus` + `PicovoiceMixer` (JVM `mixer.py` reimpl) +
  `PicovoiceBenchmark` (per-window min-DTW swept analytically; reuses `AmbientFar`/`Enroller`/`Evaluator`);
  gated `PicovoiceBenchmarkTest` (`-Dpicovoice.dir`). Data via `scripts/eval/fetch-picovoice-benchmark.sh`
  (open downloads: Picovoice repo + LibriSpeech/OpenSLR + DEMAND/Zenodo; **no key, no Kaggle**).
- **Result:** discrimination strong (closed-set **rank-1 89.2%**) but **no viable always-on point**
  (0.1 FA/hr ⇒ 87.5% miss) — rejection/gating is the wall, confirming the scorecard on a standard stream.
- **Anchor:** same-host PocketSphinx (`scripts/eval/run-pocketsphinx.sh`, no key) on identical dumped
  streams. Report: `docs/testing/2026-07-06_picovoice-wake-word-benchmark.md`; scorecard factor-4 updated.

`docs/plans/2026-07/cp1-ssl-frontend-ceiling-spike.md` — ✅ **DONE 2026-07-06** (advisor-gated design +
analysis). The first **real measurement on CP-1**: a `[measure-only]` Python harness that reproduces the
committed TORGO MFCC-DTW report **to the decimal** (fidelity gate), then A/Bs classic (MFCC/LPCC) vs
frozen learned (WavLM/HuBERT/wav2vec2) front-ends under a matched matcher. **Verdict GO:** best-learned
**WavLM-L12 pooled-cosine 71.9% rank-1** vs MFCC-DTW 55.4% (−37% rel error aggregate, **≥50% on the
F01/F04 deployment slice**, McNemar **p=2×10⁻⁶**). **Key sharpening (advisor caught a confound):** the 2×2
representation×matcher decomposition shows the lever is a **fixed-dim QbE embedding + cosine prototypes**
(the dormant `QbeEncoder` seam) — *not* a front-end swap (WavLM-under-DTW ties MFCC; MFCC-under-pooling
drops to 39.3%). Banked dead-ends: LPCC≈MFCC, wav2vec2 weak, model-scale (WavLM-large) not a lever, CP-2
rejection wall still binding (FRR@FAR≤5% only 78.3%→66.3%). Report:
`docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`; harness `scripts/eval/ssl_frontend_spike/`. New
rule **EVAL-004** (decompose confounded representation×matcher comparisons).

`docs/plans/2026-07/picovoice-benchmark-operationalization.md` — ✅ **DONE 2026-07-06**. Follow-on: turns
the one-shot harness into a repeatable **build / planning / experimentation** surface. `make bench-picovoice`
(no overrides ⇒ byte-reproduces the committed report); six experiment knobs (`FRONTEND`/`DELTA`/`SNR`/
`WINDOW`/`HOP`/`TARGETFA`) wired to `-D` for CLI sweeps; advisory benchmark-impact bullet in the plan
`TEMPLATE.md` + START_HERE rows. No results ledger (declined); no CI gate (corpus is `[measure-only]`).
EVAL-003 framing throughout: pinned default is the banked baseline, sweeps are a NOT-banked family.
