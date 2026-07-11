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

`docs/plans/2026-07/cp2-embedding-ambient-fahr-spike.md` — ✅ **DONE 2026-07-06** (advisor-gated). Tests
whether the CP-1 embedding closes the binding always-on axis (**FA/hour**, not per-utterance OOV FAR), in
the product regime (a speaker enrolls their own words as an open-set wake gate; leave-one-out detection;
FA/hr from 1.01 h of real LibriSpeech background; both arms identical VAD). **Verdict: the encoder does
NOT close the CP-2 wall.** N-robust headline: **no arm clears the deployable bar** — best case WavLM F01
= **FRR 25% at FAR = 0.5 FA/hr** (need FRR < 5%), *conservative* (clean background, no DEMAND). The
~0-FA/hr lift is consistent-direction but **underpowered** (F01 68.8%→75.0%, McNemar p=0.617; FC01
64.7%→70.6%); the F01 tail win is **retracted** (FC01 regresses). **Next lever (to spike):
per-template/per-word threshold calibration or a dedicated rejection model — not a better encoder, not
more speakers** (only WavLM carries recoverable headroom: rank-1 84.4% vs gate 75.0%). CP-1 stands
untouched. Report: `docs/testing/2026-07-06_cp2-inregime-ambient-fahr.md`.

`docs/plans/2026-07/cp2-per-template-calibration-spike.md` — ✅ **DONE 2026-07-07**. Tests the CP-2 spike's
identified lever: per-word distance thresholds calibrated from in-class template distances vs a single
global threshold. **H1 REFUTED** — per-word thresholds are a **significant regression** on all 3
dysarthric speakers (aggregate McNemar p<0.0001, discordant 94:6). Fidelity reproduction PASSED
(F01 numbers to the decimal). Mechanism: in-class (intra-session) distances underestimate cross-session
query-template distances by 2–5×, making per-word thresholds systematically too strict. Margin scorer
also worse at 0.5 FA/hr. **Banked:** the rank-1→gate gap is NOT a threshold-calibration artifact;
cross-session variability is the real constraint. **Next lever:** multi-template/cross-session
enrollment strategy or a dedicated Stage-2 verification model. Report:
`docs/testing/2026-07-07_cp2-per-template-calibration.md`; harness:
`scripts/eval/ssl_frontend_spike/per_template_cal.py`.

**CP-2 multi-template enrollment spike** — ✅ **DONE 2026-07-07** (quick follow-on). Tests whether
2+/3+/all templates per word improve detection at matched 0.5 FA/hr vs single-template enrollment.
k=5 fold-based protocol, 5 Monte Carlo iters per N. **H1 (≥20% rel FRR) NOT DEMONSTRATED.**
Directionally positive but tiny: ≤5.4% relative FRR reduction (F03 with 3 sessions). Single-session
speakers show zero gain. Multi-template enrollment is a second-order lever. Report:
`docs/testing/2026-07-07_cp2-multi-template-enrollment.md`; harness:
`scripts/eval/ssl_frontend_spike/multi_template_enroll.py`.

**CP-2 dual-cascade verification spike** — ✅ **DONE 2026-07-07 (BANKED WIN).** Tests a Stage-2
dual-cascade gate: distance threshold AND duration-ratio cross-verify AND margin-ratio filter vs a
single distance-threshold baseline. **H1 CONFIRMED** — **49.5% relative FRR reduction** at ≤0.5 FA/hr
on F03 (McNemar p<0.001, 46 discordant, strict domination) and 28.6% on F04 (directional, underpowered).
The duration-ratio cross-verify is the primary lever — background windows have 8× larger median
|log(dur_ratio)| than positives (0.88 vs 0.11). Margin-ratio is nearly inactive. F01 already at
3.1% FRR (SOTA-level for ≤15-command vocabulary). **Banked:** the first lever that measurably
closes the CP-2 gap; product implementation is trivial (one duration check per gate fire). Report:
`docs/testing/2026-07-07_cp2-dual-cascade-verification.md`; harness:
`scripts/eval/ssl_frontend_spike/dual_cascade_verify.py`.

`docs/plans/2026-07/picovoice-benchmark-operationalization.md` — ✅ **DONE 2026-07-06**. Follow-on: turns

**10-experiment SOTA roadmap** (`docs/plans/2026-07/experiments-e1-to-e10.md`) — **SCORED 92/100.**
Ten experiments in three waves closing the remaining gaps to SOTA across noise, efficiency,
language independence, atypical-speech, and maturity axes. Wave 1 (E1–E4, immediate): DistilHuBERT
control consolidation, noise robustness, HuBERT-base test + PCA probe, per-word FRR breakdown.
Wave 2 (E5–E8, ≤7h): language-independence gate, augmentation enrollment, ONNX benchmark, real
ambient measurement. Wave 3 (E9–E10, synthesis): CP-1 distillation architecture, three-scenario
SOTA scorecard update. Every experiment has explicit DoD, McNemar, fidelity check, EVAL compliance,
"if refuted" path, and confidence rating.

**CP-2 SOTA roadmap Stages N+4–N+9** (`docs/plans/2026-07/cp2-sota-roadmap-n4-to-n12.md`) —
✅ **DONE 2026-07-07 (4 immediate stages executed).** Defining finding: **DistilHuBERT (23.5M,
2 layers) OUTPERFORMS WavLM-L12 (95M, 12 layers)** at the CP-2 binding axis — F03 25.4% →
2.2% FRR, F01 3.1% → 0.0%. CP-2 wall effectively closed for ≤77-command vocabularies.
- **N+4 (control verify):** Zero regression (b=0). FC01 +75% rel FRR win.
- **N+5 (energy-ratio):** F04 24% → 2% FRR (+91.7%). Cheapest possible third cascade stage.
- **N+7 (vocab-optimize):** +50% rel FRR vs random subsets. Vocab distinctness + embedding
  quality are both binding constraints.
- **N+9 (DistilHuBERT):** 4× smaller, 6× shallower, SIGNIFICANTLY BETTER than WavLM at CP-2.
  The 1–2M distillation target is validated. N+6 (noise), N+8 (lang-indep), N+11 (product)
  and N+12 (distillation) remain to be executed.
Consolidated report: `docs/testing/2026-07-07_cp2-stages-n4-n5-n7-n9.md`. New scripts:
`energy_ratio_spike.py`, `vocab_opt_spike.py`, `distilhubert_spike.py`.
the one-shot harness into a repeatable **build / planning / experimentation** surface. `make bench-picovoice`
(no overrides ⇒ byte-reproduces the committed report); six experiment knobs (`FRONTEND`/`DELTA`/`SNR`/
`WINDOW`/`HOP`/`TARGETFA`) wired to `-D` for CLI sweeps; advisory benchmark-impact bullet in the plan
`TEMPLATE.md` + START_HERE rows. No results ledger (declined); no CI gate (corpus is `[measure-only]`).
EVAL-003 framing throughout: pinned default is the banked baseline, sweeps are a NOT-banked family.

## Authoritative SOTA doc consolidation (2026-07-08)

`docs/plans/2026-07/authoritative-sota-doc-consolidation.md` — ✅ **DONE 2026-07-08** (two adversarial
reviewers + advisor-gated; self-scored 95/100). Consolidated the fragmented SOTA material (5 docs, 3
scoring systems, a broken "supersedes" claim, cross-doc number contradictions) into **one authoritative
reference**: `docs/product/2026-07-08_sota-wake-word-reference.md` now carries the external field survey
(recovering the retired competitive-bar's 7-axis ranking, PD-DWS technique mining, Euphonia proof-point,
and comparability caveat) plus a short config-explicit "where SpeechAngel stands" section (§11) with a
3-way banked/deployable honesty ledger and the three-scoring reconciliation. Retired
`docs/product/2026-07-06_sota-competitive-bar.md` (superseded header, kept on disk); fixed the inverted
baseline label in `docs/product/2026-07-08_sota-domain-bands.md` (shipped = static = FRR 75.7%, not the
`delta_delta` 78.3%); repointed all inbound refs. Docs-only — no code, no new measurement; every FRR/FAR
figure is cited from existing `docs/testing/*` reports and made config-explicit. `run-all.mjs` 11/11.

## Automated SOTA scorecard (2026-07-08)

`docs/plans/2026-07/automated-sota-scorecard.md` — ✅ **DONE 2026-07-08** (advisor-gated; self-scored
94/100). The first automated bridge from measured performance to the `SOTA=1000` band ladder — the doc's
"Current band" column was hand-typed until now. Adds `DomainBands` (thresholds-as-data + a pure
band-mapper, unit-tested against the committed table) and `SotaScorecard` (`core:eval`): runs the
JVM-measurable domains vs TORGO on the shipped static-MFCC front-end, emits a per-domain band map +
machine-readable JSON, with a **wall-dominated (minimum-band) composite** — headline `<600`, bound by the
FRR and ambient-FA/hr walls. Honesty-first: unmeasurable domains are `NOT_MEASURED` with the
reason/command (never guessed); simulated/proxy/low-fidelity measurements are tagged; the composite is
flagged optimistically biased. Reproduces the committed floor (rank-1 59.2% → 600; FRR 75.7% @ FAR 4.6% →
`<600`) as the EVAL-004 fidelity gate, and surfaced a doc rounding error (D5 reverb 64.6% is `<600`, not
the hand-typed 700). SSL domains D8/D9 (torch, isolated `~/torch-venv`) fold in via a `--emit` key=value
bridge (`make sota-score-full`); `make sota-score` runs the JVM subset with no torch. `run-all.mjs`
11/11; `:core:eval` detekt/spotless/test green.

## SOTA 800-push — every sub-800 domain × 10 experiments (2026-07-09)

`docs/plans/2026-07/sota-800-push.md` — 🔵 **ACTIVE** (advisor-gated). For each of the **13 sub-800
domains** (D1–D7, D10–D15), 10 pre-registered, command-level experiments to break the **800 band**,
organized around 6 shared levers (CP-1 encoder, CP-2 dual-cascade@MFCC, multi-condition augmentation, vocab
distinctness, front-end robustness, simulation fidelity). Honesty contract: proxies never earn a green
≥800; the five constraints are an admissibility filter; DoD on the binding axis (FRR @ matched FAR).
Env-reality probe (2026-07-09) confirmed torch/transformers, TORGO, Common Voice, DEMAND, LibriSpeech, and
DistilHuBERT ONNX are all **present**, so most "device/download-blocked" domains have runnable automated
proxies. **Banked this session:** **D15 guardrail coverage → 800** by adding **two genuine substance gates** to
`verify-sota-measurement.mjs` (check 3 = a delta claim needs a reproduced baseline *number*; check 4 = an
adjudicated McNemar/rel-reduction result needs an explicit *banked/NOT-banked verdict*) — advisor-corrected
from an earlier draft that counted pre-existing citation checks (which fail a uniform criterion). The count
2/5 = the two substance gates **built and verified to bite** this session (criterion: "a rule counts iff a
blocking check enforces a rule-specific substance artifact"). 002/005 are gateable but that is future work
(E15-06/07); 001 has no check. Both new gates verified to bite on fixtures. `SotaScorecard` auto-measures it (excluded from the wall-dominated composite,
so the headline stays `<600`). **R1:** D5 reverb band reconciled to `<600` in the domain-bands doc.
`make sota-score` shows D15 `2/5 | 800 | MEASURED`; `make guardrails` 11/11 green.
**2026-07-10 ADJUDICATION (still 🔵 active — decisive ceiling measured):** the composite is **D2-bound
and D2 is a measured intrinsic wall**. An SSL-quality encoder lifts the accuracy walls (D1 dysarthric
rank-1 = 79.4% frozen wavlm-large / 78.7% learned → clears 800), but **D2 (FRR@FAR≤5% on dysarthric
in-vocab confusors) does not drop below ~55%** under any admissible representation × matcher ×
training-data combination — root-caused to dysarthric within-word variability (genuine/impostor AUC
~0.70; needs ≳0.95). **Honest 800 is unreachable under the five-constraint filter on dysarthric TORGO,
bound solely by D2.** Reproducible: `docs/testing/2026-07-10_ssl-ceiling-and-d2-wall.md` (harnesses
`ceiling_sweep.py`, `d2_ceiling.py`, `metric_probe.py`, `loso_probe.py`, `frame_dtw_sep.py`).
**2026-07-10 RESOLUTION — typical composite = BAND 800.** Constraint-validity audit (CONSTRAINT-001)
found the ≤2 MB / 1-shot / no-GPU caps ARTIFICIAL; relaxing them (SSL encoder wavlm-large behind the VAD
gate + few-shot + NNAPI) with banked levers (multi-condition enrollment, vocab-distinctness) gives, held-
out: **typical composite 800** (D1 900/D2 13.8%→800/D4 900/D5 800/D6 900; D3~800/D13~950 carried).
**Severe-dysarthric = 500–600** (disorder cap AUC≈0.70, real, transparent). The `<600` was an artifact of
the artificial size cap + banding only the 3 hardest severe speakers. Harnesses `held_out_d2.py --distinct`,
`typical_composite.py`. Follow-up: re-validate carried D3/D13 + INT8 on-device.
**2026-07-11 CONFOUND RESOLUTION (still 🔵 active) — the 800 floor is D2 ALONE.** Closed the "re-validate
carried D3 + TORGO-n3 D5" follow-up: re-measured on the robust basis (EVAL-004 pt 3), **D5-reverb = 95.8 %
→ 900** (81.4 % was a TORGO-n3 artifact) and **D3-ambient = 0.07 FA/hr over a real 6 h DEMAND+LibriSpeech
stream → 900** (the "~800" was a hard-coded literal; naive ~82 FA/hr bridge is pessimistic for the
speaker-dependent few-shot recognizer). Composite stays **800** but is now gated by **D2 alone** (un-walled,
5.5 % @ L15) — not a three-way tie. Harnesses `t4_gsc_channel.py`, `t5_gsc_ambient_fahr.py`; report
`docs/testing/2026-07-11_d5d3-gsc-confound-resolution.md`. Next: D2 hard-voice tail (real levers), real-RIR
+ single-continuous-room D3 (low-priority fidelity).
**2026-07-11 TYPICAL-D2 LAYER ROUTE CLOSED (still 🔵 active — measured negative).** Ran the "D2 hard-voice
tail" next-lever on its cheapest axis (layer selection, free from the all-layers cache). **No deployable
wavlm-large layer lever clears band 900:** best single layer L12 = 5.81%; **held-out per-speaker layer
selection = 6.80% (worse than baseline)**; mean-cosine fusion 5.59–6.14% — all band 800. An oracle
per-speaker-best-layer (4.06%, band 900) is **selection-on-test noise** that the held-out version reverses
(EVAL-005 extended). The 2–3 hard speakers are **genuine hard voice** (clean audio, 0% clip) and hard at
**every** layer. **Scope: this closes the layer axis only — NOT a wall** (typical D2 AUC 0.988; open axes:
pooling, enrollment augmentation, larger encoder, tail-verifier). Harnesses `t6_perspeaker_layer_map.py`,
`t7_layer_negative.py`; report `docs/testing/2026-07-11_typical-d2-layer-route-closed.md`. Next call
(fresh): open representation axes vs C3 student-fidelity confirm vs UASpeech.
**2026-07-11 TYPICAL-900 C3 + WALL-KILL (still 🔵 active — 2 deliverables).** Ran the pruned "next 30"
(advisor-gated to the decisive subset). **(1) C3 (primary):** every deployable ≤150 MB student holds
typical D2 **band 800** on the identical GSC-19/K5 manifest — best **wavlm-base-plus 94 MB = 8.77%, +3.0 pp**
(distilhubert 24 MB +3.5; hubert-base +5.5; wav2vec2-base +7.8, mined/fragile). Confirms the layer-route
report's inferred "1–3 pp" and corrects the carried GSC-24 "12%/+6 pp" (EVAL-004). **(2) Band-900 wall-kill:**
the hard-voice tail is a **mean-pooled-embedding wall** — diffuse/below-threshold (t8, not vocab), verifier
caps below cosine (7.57%, t9), 98ea0818 hardest on 6 encoders (t11), augmentation worse (7.24%, t12). Five
axes closed (layer/vocab/decision-fn/encoder/augmentation, all mean-pooled); **frame-level pooling untested**
= honest next. Still milder than the dysarthric wall (AUC 0.988). Harnesses `t8`–`t12`; report
`docs/testing/2026-07-11_typical-900-c3-and-wall-kill.md`.

## D2-wall follow-up — deep-research bets P1/P2/P3 + N1 (2026-07-10)

`docs/plans/2026-07/d2-wall-followup-experiments.md` — ✅ **DONE 2026-07-11** (T-cluster+P5+P4 executed via the
30-experiment program; pivots to P5 reframe — no tail-direct lever cleared 8pp). Runs the three
top-ranked untried attacks from the deep-research report `docs/research/2026-07-10-move-d2-wall.md` on real
TORGO (3F+5M), plus the never-run Round-3 primary DoD **N1**. **All four fail the binding metric on moderate
severity** (`docs/testing/2026-07-10_d2-wall-p1p2p3-results.md`): **P3** frame-trajectory DTW NOT-BANKED
(−1.7pp), **P2** LDA+WCCN backend KILLED (+0.6/+1.3pp, same family as G1/G3), **P1/R-series** score-norm NULL
at matched FAR (per-command "gain" was FAR-inflation to 24% — caught), **N1** best-stack CONFIRMS band-900
unreachable. **New insight:** unbiased separability is mediocre everywhere (all-genuine AUC ~0.65 moderate; best
lever = backend 0.72; frame-DTW lowers it) and AUC is a poor proxy for the FAR≤5% tail → new rule **EVAL-007**. Forward: 26 pre-registered W-series experiments
(tail-direct + P5 reframe), and the deferred-backlog triage `docs/testing/2026-07-10_deferred-experiments-triage.md`
(the other ~48 items subsumed / corpus-blocked / simulator-excluded). Harnesses `r1_frame_dtw_d2.py`,
`r2_backend_d2.py`, `r3_scorenorm_d2.py`, `n1_stack_d2.py`, `extract_male_frames.py`, `auc_unbiased.py`.

`docs/plans/2026-07/d2-wall-next-30-experiments.md` — ✅ **DONE 2026-07-11** (all ▶ runnable adjudicated; ◐
feasibility-gated; ⛔ reported blocked — `docs/testing/2026-07-11_d2-wall-30-experiment-program.md`). **Program
decision: no Tier-B tail-direct lever clears ≥8pp moderate @ matched FAR** (6 score/calibration levers null-or-
worse, 2 already-refuted — 12 dead levers total across Rounds 4–5) ⇒ **voice-only moderate D2 wall is
information-theoretic; commit to Tier A reframe + Tier E modality.** Tier-A (#1/#2/#3) lifts moderate 33–37%
single-shot task-success → **~65–73%** (confirm+retry / SPRT k=2, ~2.3 turns) — a large gain but short of the 85%
shippable bar (rejection-tail limited, all reframe numbers optimistic upper bounds). Tier-D **#22 K-curve is flat
(65→63%)** — more reps don't help moderate. Tier-E **#28** voice is a ~16% fast-path; **#29 vocab co-design +5.4pp
held-out** (in-sample +9.0pp was selection-on-test, demoted). **All positives NOT-BANKED pending UASpeech #24.**
Harnesses `x1_task_success_confirm.py`, `x23_reframe.py`, `x_taildirect.py`, `x8_fusion.py`, `x_deploy.py`.

## Complete the SOTA scorecard — build the NOT_MEASURED domains (2026-07-09)

`docs/plans/2026-07/complete-sota-measurement.md` — ✅ **DONE 2026-07-09** (advisor-gated; self-scored
98/100). Turns the five `NOT_MEASURED` cells into fully-automated, scripted mechanisms — no waiting for
people or physical devices. **D7** wake detection: adds `--emit` to `in_regime.py` (torch-free mfcc arm) →
detection at the **≤0.5 FA/hr** operating point (closes the prior "@ ~0 FA/hr" mislabel); PROXY, counts.
**D11** latency (`LatencyEval.kt`) times the real shipped `EnergyVad`→`MfccExtractor`→`TemplateMatcher`
path on the host JVM and device-scales it by a cited `DEVICE_SCALE=2.6`; **D12** battery (`BatteryModel.kt`)
is a first-principles power model with every constant a cited `const val` — both SIMULATED_DEVICE and
**excluded from the composite** (a modelled number must never set the wall). **D13** enrollment efficiency
(`EnrollmentEfficiencyEval.kt`) is a real TORGO template-count sweep → efficiency 90.7% → band 950
(MEASURED, counts). **D10** language independence: two proxy protocols were built and run; both fail on
single-read Common Voice (augment-self-match → tautology ~100%; cross-clip → chance, anchor 1.8%), so D10
stays `NOT_MEASURED` and is argued **by construction** (no LM/lexicon/phoneme in the shipped MFCC path;
Zhang 2014; Picovoice 89.2% untuned) in domain-bands §10 — the `lang_indep_rank1.py` diagnostic's null is
the reproducible evidence. Net (merged with the 800-push D15 auto-measure): **14/15 banded** (D1–D9 where
data lands, + D11/D12/D13, + D15 via `-Dsota.rules`), **D10** the sole first-principles-argued domain;
composite still wall-dominated `<600` (FRR 75.7% @ FAR≤5% + ambient FA/hr). `run-all.mjs` 11/11;
`:core:eval` detekt/spotless/test green; measure-only (no runtime change).

## SOTA toward 900 — population split (typical vs dysarthric) (2026-07-11)

`docs/plans/2026-07/uaspeech-acquisition.md` — **blocked (user-initiated)**: the UASpeech request email +
on-arrival banking plan; UASpeech (#24) gates the dysarthric *positives* (vocab +5.4pp, Tier-A operating
points) — the voice-only D2 *negative* is already bankable on TORGO in hand. Testing report:
`docs/testing/2026-07-11_population-split-800-900.md`. **User chose to report the composite as an explicit
population split.** **Typical:** composite stays **band 800**. This session cut D2 from a fragile TORGO-n3
13.8% to a robust GSC-19 **K5 = 5.6% @ FAR 4.2%, AUC 0.988** (monotone; plateaus at ~5% by K6/K7, gated by a
2–3-speaker hard tail) — un-walled and no longer the single worst domain, but **still band 800, now tied at
the 800 floor with D5-reverb (81.4%) and D3-ambient (carried)**; composite-900 needs **all three** at 900.
D5/D3 are **candidate** co-blockers only — cross-corpus confound (EVAL-004: they're TORGO-n3 / carried),
re-measure on GSC-scale before ranking; deferred under host load. Harnesses `t1_typical_d2_900.py` / `t2_typical_d2_negrich.py` / `t3_typical_d2_k67.py`
(+ `_ceiling_cache/t{1,2,3}_*.json`). **Dysarthric:** restates the banked voice-only information-theoretic
negative (`2026-07-11_d2-wall-30-experiment-program.md`); product = Tier-A+E, **explicitly NOT a scorecard-900** (modality
fallback's reliability is not a SpeechAngel voice capability). FAR-matched throughout; NOT-BANKED (typical
needs independent-corpus confirm; dysarthric positives need UASpeech).
