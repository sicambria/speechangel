# Plan: realistic-condition simulation harness + common-mode rejection scoring

- **Date:** 2026-07-06
- **Phase:** 0/3 (Phase-0 "Measure FRR/FAR" — the ambient axis; Phase-3 far-field/noise + matcher enhancement)
- **Roadmap item:** Phase 0 "Measure FRR/FAR" (the always-on **ambient FAR/hour** half, still open —
  TORGO has no continuous stream); Phase 3 "Far-field / noise front-end" (measurement rig); a new
  first-principles **rejection-scoring** matcher enhancement aimed at the open-set FRR gap.
- **Status:** done (A-deliverables implemented 2026-07-06; Part 1 harness landed + measured; Part 2
  pre-registered H1 **refuted** — honest negative, no runtime change; real-far-field + real-ambient
  numbers remain Bucket B). See `docs/testing/2026-07-06_realistic-conditions-and-rejection-scoring.md`
  and `docs/errors/2026-07/2026-07-06_common-mode-rejection-refuted.md`.
- **Worktree:** `sim-and-rejection-scoring` (substantive core-code change — worktree off `main` per AGENTS.md)
- **Plan quality:** 96/100 — self-scored 2026-07-06 (breakdown at foot); advisor-gated before implementation.

## Outcome (2026-07-06)

- **Part 1 (delivered):** `AudioAugment` (noise@SNR / Schroeder reverb / band-limit / gain-clip),
  `Conditions`, `ConditionEval`, `AmbientFar` — a realistic-condition simulation harness over real TORGO.
  Measured: additive noise is the dominant degrader (deployment-slice rank-1 64.6%→34.1%→8.5% at
  20/10/5 dB SNR), reverb and telephone band-limit mild. First **ambient FA/hour proxy** = ~82 FA/hr
  (optimistically biased) — ~160× the Phase-0 budget, quantifying the always-on gap on real audio.
- **Part 2 (honest negative):** pre-registered H1 = common-mode rejection normalization, adjudicated by
  held-out McNemar on the **shipped** static front-end. **Refuted** — significant regression on control
  (χ²=39.7, p<0.001), directionally worse on dysarthric. §9 conditional adoption did **not** fire; the
  matcher is unchanged. The `raw` baseline agrees with the trusted `TorgoEval` path to one-decimal
  (both 75.7%/4.6%; per-speaker vs pooled fitting coincide at this resolution, not byte-identical).
  `margin` is a documented future pre-registered hypothesis (EVAL-003), not adopted.

## Goal

Two coupled outcomes, in the user's stated order:

1. **A realistic-condition simulation harness** in the dev environment so recognizer performance is
   measured under home-like acoustics — additive noise at controlled SNR, room reverberation, and
   mic/channel band-limiting applied to the **real** TORGO speech — plus the project's first
   **ambient FAR-per-hour proxy** (the always-on number the repo currently *cannot* measure, because
   TORGO has no continuous stream — `core/eval/.../TorgoEval.kt:423`).

2. **A significant, first-principles accuracy improvement aimed at the honest product number** — the
   open-set rejection FRR (held-out **78.3%** @ FAR≤5%, `docs/testing/2026-07-06_frr-far-torgo.md`).
   The improvement is a **common-mode (cohort) normalization of the accept/reject score**, pre-registered
   as a single a-priori hypothesis and adjudicated by a McNemar paired test on **clean real TORGO**.
   Adopt into the runtime matcher **iff** it clears significance at matched FAR; an honest negative
   result (like the D1 per-command-calibration finding) is a valid deliverable.

## Context & Constraints

- **The two questions are two different problems (first-principles frame).** "Pick the right command"
  is closed-set discrimination (rank-1: 55.4% dysarthric / 74.6% control, held-out). "Ignore everything
  that isn't a command" is open-set verification (FRR 78.3% @ FAR≤5%). The gap between rank-1 *error*
  (44.6%) and FRR@FAR (78.3%) — **~34 points** — is pure **threshold cost**: the argmin command is
  correct but the raw min-DTW distance `d1` of a true match overlaps the `d1` of OOV false matches, so
  the single global cutoff throws correct positives away to hold FAR. This gap is the lever.

- **The decision rule today thresholds `d1` alone.** `DistanceRow.decide` (`core/eval/.../Evaluator.kt:25`)
  and `TemplateMatcher.match` (`core/matching/.../TemplateMatcher.kt:60`) accept iff the winner's
  distance ≤ its threshold. The **runner-up margin is computed but never gates acceptance** — it feeds
  only display confidence (`TemplateMatcher.kt:78-86`). So a normalized-score decision rule is a
  genuinely unbuilt lever, not a re-description of what ships (this is explicitly *not* the "voting"
  no-op of `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md`: that lever equalled an
  already-computed quantity; a normalized score uses quantities `decide()` currently ignores).

- **Accuracy honesty (non-negotiable, enforced by `scripts/audits/verify-plan-workflow-guardrails.mjs`).**
  Every accuracy claim is an **FRR + FAR** delta on a named corpus at **matched, held-out FAR**
  (EVAL-002, `docs/ai/ACTIVE_DEV_RULES.md`), never a bare percentage. No gain is claimed from synthetic
  or simulated audio; simulated-channel results are a **probe**, banner-labelled "real speech, simulated
  channel — not field far-field."

- **Pre-registration (the honesty blocker).** Evaluating a *family* of scorers and reporting the best is
  selection-on-test — the exact best-of-grid optimism D3 (`…frr-far-torgo.md` §D3) and EVAL-002 exist to
  strip out. Therefore **one** scorer is pre-registered as the hypothesis (common-mode normalization,
  §Approach), McNemar-tested vs baseline; any other scorers are reported as an **exploratory full family**
  (all cells shown, like the D3 grid), explicitly **not banked**.

- **Rank-1 is invariant by construction.** Winner selection stays `argmin d1`; only the *accept/reject
  score of that winner* is normalized. So the scorer moves FRR@FAR and nothing else — rank-1 stays a
  fixed reference and the experiment cleanly isolates threshold cost.

- **Measure against the shipped front-end.** The product `MfccConfig` default is `deltaOrder = NONE`
  (`core/dsp/.../MfccExtractor.kt:49`) but `TorgoEval`'s default is `delta_delta`
  (`core/eval/.../TorgoEval.kt:28`). The rejection experiment is baselined on the **shipped** static-MFCC
  front-end, so the baseline is a config the product actually ships.

- **Threshold-scale coupling (do not disturb).** DTW uses plain Euclidean local cost (`Dtw.kt:18`) with
  `(n+m)` length-normalization (`Dtw.kt:74`); every acceptance threshold lives on that exact scale
  (audit `2026-06-28_dtw-length-normalization-convention`). The rejection scorer operates **at the
  decision layer** (a transform of the already-computed per-command distances), so it introduces **no**
  change to the DTW metric or the enrollment path — its own threshold is fit held-out, sidestepping the
  recalibration coupling entirely.

- **On-device, deterministic, language-independent.** All new code is pure Kotlin/JVM in
  `core:eval`/`core:dsp`/`core:matching` (fast `:core:*:test` gate, no device). No cloud, no LLM, no
  normal-speech prior — common-mode normalization uses only the user's **own** enrolled commands'
  distances within a trial (needs no external cohort model, so it stays dysarthria-safe and is
  **orthogonal to why D1 failed**: it requires no per-command negative data, whereas D1's per-command
  calibration collapsed to accept-all on commands with no train negatives).

## Approach

Two modules of work, sequenced so the accuracy claim rests on the most defensible data.

**Part 2's flagship, pre-registered hypothesis (H1).** For each utterance the evaluator already produces
`bestByCommand` = the min-DTW distance to every command (`Evaluator.kt:19`). Let `d1` be the winner's
distance and `C = {d_c : c ≠ winner}` the other commands' distances in the **same** trial. The
common-mode score is

> **s = d1 − median(C)**   (per-utterance; `median(C)` = the "how far is this audio from *everything*"
> common-mode offset).

First-principles justification: the dominant driver of the 34-point gap on dysarthric speech is
**utterance-level distance inflation** — a correct match has large `d1` because the whole utterance is
far from *every* template today (high within-speaker variability). Subtracting the per-trial common mode
removes exactly that offset: a true command is close to its own command *and* far from the others → very
negative `s` → accept; generic OOV audio is roughly equidistant from everything → `s ≈ 0` → reject.
Crucially this rescues "far-from-everything" positives that a runner-up **margin** (`d2 − d1`) cannot
(there both `d1` and `d2` are large → small margin → still rejected) — which is why cohort, not margin,
is the pre-registered pick.

**Isolation of the change.** Thread a `score: (DistanceRow) -> Float?` selector through the existing
held-out machinery (`heldOut`/`fitGlobal`/`farOf`, `TorgoEval.kt:117-166`) so the *same* leave-one-fold-out,
matched-FAR discipline scores any rejection rule. Baseline = the identity scorer `s = d1` (must reproduce
the committed **55.4% / 78.3%** headline exactly — the regression guard). H1 = `s = d1 − median(C)`.
Winner = argmin d1 for **both** (rank-1 unchanged). Report FRR at matched held-out FAR≤5% and a **McNemar**
paired test on the per-utterance correct-accept outcomes of the positives. Adopt into runtime only if H1
wins at significance.

**Part 1's realistic-condition harness.** A pure, deterministic (seeded) audio-augmentation layer over
`AudioSamples` (FloatArray + rate; `WavFile.read` already yields it): additive noise at a target SNR,
O(n) Schroeder reverberation (parallel combs + series allpass, RT60-parameterised — a plausible tail
without O(n·k) convolution cost), and a biquad band-pass mic/channel colouration. A `ConditionGrid`
re-runs the TORGO eval with **queries** degraded (enrol-clean / test-degraded — the real deployment
asymmetry), reporting rank-1 + held-out FRR@FAR per condition. The priority piece is the **ambient
FAR/hour proxy**: concatenate real OOV speech + noise into a simulated continuous stream, window it, and
count false accepts → the first FA/hour figure — with a drop-in ambient-wav seam so the proxy becomes a
real measurement the moment the user supplies a recording.

**Sequencing.** Build Part 1 first (the user's order) but run H1 on **clean** real TORGO as the primary
result — it does not depend on simulation realism, so the go/no-go for the accuracy claim rests on the
cleanest data. Then use the simulator to test the *winner's robustness* under noise/reverb/band-limiting.

**Rejected alternatives.** (a) Reporting the best of a scorer family — selection-on-test (the blocker
above); mitigated by pre-registering H1. (b) Runner-up **margin** as the flagship — does not rescue the
far-from-everything failure mode that dominates the gap. (c) A bundled generic "filler/UBM" cohort —
imports a normal-speech prior (dysarthria-unsafe) and external assets; the per-trial own-command cohort
needs neither. (d) Changing the DTW metric / adding CMVN to chase rank-1 — recalibrates every threshold
(threshold-scale coupling) for the *discrimination* problem, when the honest product number is
*rejection*; deferred. (e) O(n·k) RIR convolution — too slow for a grid over hundreds of utterances;
Schroeder is the right dev-environment cost/realism trade. (f) Wiring the scorer into `:app`'s
`ListeningService` before it wins the McNemar — building on an unproven lever.

## Steps

### Part 1 — realistic-condition simulation harness (`core:eval`, `core:dsp`)

1. **Audio augmentation primitives.** New `core/eval/src/main/kotlin/com/speechangel/core/eval/AudioAugment.kt`
   — pure, deterministic `object`/functions on `AudioSamples`:
   - `addNoise(signal, noise, snrDb, seed)`: scales a noise source to a target SNR measured over the
     VAD-active region (reuse `EnergyVad`); noise source is generated (white/pink via a seeded LCG) or a
     supplied `AudioSamples` (drop-in babble/TV).
   - `reverb(signal, rt60Ms, mix)`: O(n) Schroeder reverberator (4 parallel feedback combs + 2 series
     allpass, delays/feedback derived from `rt60Ms`), deterministic.
   - `bandLimit(signal, lowHz, highHz)`: cascaded one-pole/biquad band-pass (telephone 300–3400 Hz and a
     wider "small-speaker" preset).
   - `gainClip(signal, gainDb, clipCeil)`: gain + `tanh` soft-clip (AGC/overload).
   - **Check:** unit tests assert SNR is hit within tolerance, reverb preserves length/energy sanity,
     band-limit attenuates out-of-band tones, all bit-deterministic across two runs (`:core:eval:test`).
2. **Named conditions.** `core/eval/src/main/kotlin/com/speechangel/core/eval/Conditions.kt`: `enum`/list of `Condition(name, transform:
   (AudioSamples, seed) -> AudioSamples)` — `CLEAN`, `NOISE_20DB/10DB/5DB`, `REVERB_SMALL/MEDIUM`,
   `BANDLIMIT_TELEPHONE`, and a combined `LIVING_ROOM` (mild reverb + 15 dB noise + band-limit). `CLEAN`
   is the identity transform (regression anchor).
3. **Condition grid runner + report.** Extend `TorgoEval` (or a sibling `ConditionEval.kt`) to run the
   held-out eval per condition with **queries** degraded and enrollment clean, producing a
   condition × {rank-1, held-out FRR@FAR, realized FAR} table. Banner: "real speech, simulated channel —
   a controlled robustness probe, **not** a field far-field measurement."
   **Check:** `-Dtorgo.conditions=true` emits a populated table; `CLEAN` row reproduces the headline
   (identity-transform regression).
4. **Ambient FAR/hour proxy.** `core/eval/src/main/kotlin/com/speechangel/core/eval/AmbientFar.kt`: concatenate real OOV utterances + seeded
   noise (or a drop-in `-Dambient.wav=…`) into an N-minute stream, slide the command window
   (`WakeGatedRecognizer` geometry), count accepts against enrolled templates → **false-accepts per
   hour**. Honest caveats emitted in the report: (a) concatenated isolated OOV words ≠ continuous
   TV/dialogue → the proxy is **optimistically biased** (gaps make it less command-like than real
   speech); (b) a supplied ambient recording replaces the proxy with a real measurement.
   **Check:** proxy runs, reports FA/hour + total simulated minutes; a drop-in wav path is honoured.

### Part 2 — common-mode rejection scoring (`core:eval`, then conditionally `core:matching`)

5. **Score selector seam (measurement).** Add `RejectionScore` in `core:eval` (a
   `fun interface (DistanceRow) -> Float?`) with `RawDistance` (`s=d1`, the baseline) and `CommonMode`
   (`s = d1 − median(other-command distances)`). Winner command remains `argmin d1` in both — only the
   thresholded score changes. **Check:** unit tests on hand-built rows (`:core:eval:test`).
6. **Thread the scorer through the held-out machinery.** Generalise `farOf`/`heldOut`/`fitGlobal`
   (`TorgoEval.kt:117-166`) to sweep candidate thresholds over `RejectionScore` instead of raw `d1`.
   **Regression guard (must pass before any delta is trusted):** with `RawDistance` on the shipped
   `deltaOrder=NONE` front-end, `TorgoEval` reproduces the committed headline **55.4% / 78.3%** exactly.
7. **Pre-registered adjudication.** Run baseline vs H1 (`CommonMode`) on clean real TORGO
   (dysarthric + control) at matched held-out FAR≤5%; compute a **McNemar** paired test on the positives'
   correct-accept outcomes (report both realized FARs; interpret at approximately-matched FAR, caveat
   stated). Emit an exploratory full-family table (RawDistance / CommonMode / margin / ratio) with all
   cells shown and a "**not banked — exploratory**" label.
   **Check:** `-Dtorgo.reject=true` emits the H1-vs-baseline McNemar verdict + the exploratory table.
8. **Robustness of the winner (uses Part 1).** If H1 wins on clean TORGO, re-run baseline-vs-H1 across the
   condition grid (§3) and the ambient proxy (§4) to report whether the gain **holds** under simulated
   noise/reverb. If H1 does **not** win clean, record the honest negative result and stop (no runtime
   change) — the harness is still delivered.
9. **Conditional runtime adoption (gated on §7).** *Only if* H1 clears significance: promote the
   common-mode formula into `core:matching` as an **additive, default-preserving** `MatcherConfig` option
   (`rejectionScore: RAW | COMMON_MODE`, default `RAW` unless the gain is robust across conditions), used
   in `TemplateMatcher.match`'s accept gate (`TemplateMatcher.kt:60`). Byte-identical when `RAW`.
   `:app`/`ListeningService` wiring is **Bucket B** (documented, verified with the full toolchain, not the
   `:core:*` gate) — not claimed built here.
10. **Regenerate reports + incident/rules.** Update `docs/testing/2026-07-06_frr-far-torgo.md` (or a new
    dated report) with the condition grid, ambient proxy, and the H1 verdict; if H1 is a negative result
    or the refactor surfaced a bug, write the `docs/errors/2026-07/` incident and any `ACTIVE_DEV_RULES.md`
    rule (e.g. an EVAL-003 "pre-register one hypothesis; report families as exploratory").

## Definition of Done

- **Part 1 (autonomous, this host):** `AudioAugment` (noise@SNR, Schroeder reverb, band-limit, gain/clip)
  + named `Conditions` + a condition-grid runner emit a **rank-1 + held-out FRR@FAR** table per condition
  over real TORGO, with the `CLEAN` row reproducing the committed headline (identity-transform regression
  proven). The **ambient FAR/hour proxy** produces a false-accepts-per-hour figure with its
  optimistic-bias caveat and a drop-in ambient-wav seam. All simulated-channel output carries the
  "real speech, simulated channel — probe, not field" banner. `:core:eval:test` + `:core:dsp:test` green.
- **Part 2 (autonomous adjudication):** the baseline (`RawDistance`) reproduces **55.4% / 78.3%** exactly
  on the shipped front-end (regression guard); the pre-registered H1 (`CommonMode`) is reported as an
  **FRR delta at matched held-out FAR≤5%** vs that baseline on clean real TORGO (dysarthric + control),
  with a McNemar verdict. **Success is a statistically-significant FRR reduction at matched FAR**, not a
  bare percentage; a non-significant result is recorded as an honest negative (valid DoD outcome). Rank-1
  is unchanged by construction (asserted). Runtime adoption (§9) happens **iff** H1 wins, as an additive
  default-`RAW` `MatcherConfig` option (byte-identical when off); otherwise no runtime change.
- **Honesty gates:** no gain claimed from simulated audio; the scorer family is reported exploratory /
  not-banked with the single pre-registered hypothesis called out; the ambient proxy is labelled a proxy
  with its bias direction. Guardrail bundle green (`node scripts/audits/run-all.mjs`, incl.
  `verify-plan-workflow-guardrails.mjs`); the four `:core:*` tests green; `make verify` re-run after code.
- **Blocked (needs the world, disclosed):** true far-field/reverberant recordings and a real continuous
  ambient stream (Bucket B) to convert the simulated-channel probe and the ambient proxy into field
  numbers; on-device mic/CPU validation (Bucket B). Recorded as blocked — no field numbers fabricated.

## Risks & Mitigations

- **Risk: manufacturing an illusory gain by best-of-family selection.** Mitigation: **one** pre-registered
  hypothesis (H1 = common-mode), McNemar only H1-vs-baseline; the rest exploratory/not-banked (mirrors the
  D3 grid discipline). The pre-registration is written before any run.
- **Risk: the held-out refactor silently changes the baseline.** Mitigation: the identity scorer must
  reproduce the committed **55.4% / 78.3%** headline exactly on the shipped front-end before any delta is
  read (regression guard, §6).
- **Risk: common-mode is a no-op (like "voting").** Mitigation: the current decision uses only `d1`
  (`Evaluator.kt:25`, `TemplateMatcher.kt:60`); common-mode adds `median(other-command distances)` — a
  quantity `decide()` ignores — so it is a genuinely different decision function, verified by a unit test
  where a raw-`d1`-rejected positive is accepted under common-mode.
- **Risk: simulated conditions mistaken for field far-field measurement.** Mitigation: hard banner + the
  primary accuracy claim rests on **clean** TORGO; conditions test *robustness of the winner*, not the
  headline. Ambient proxy carries its optimistic-bias caveat.
- **Risk: rank-1 accidentally changes (masking the effect).** Mitigation: winner = `argmin d1` for every
  scorer; a test asserts rank-1 is identical across scorers.
- **Risk: threshold-scale coupling disturbed.** Mitigation: the scorer lives at the decision layer with
  its own held-out-fit threshold; the DTW metric, `(n+m)` normalization, and enrollment path are
  untouched (byte-identical extraction).
- **Rollback:** Part 1 is a new leaf (`AudioAugment`/`Conditions`/`AmbientFar` + a gated `-Dtorgo.*`
  code-path) — delete → eval unchanged. Part 2's measurement is `core:eval`-only; the sole runtime change
  (§9) is an additive `MatcherConfig` option defaulting to `RAW` (byte-identical) — revert = drop the
  field. No schema/template/threshold migration in any step.

## Test & Verification

- **Autonomous (this host):** `:core:eval:test` (augmentation determinism + SNR/reverb/band-limit sanity;
  condition-grid `CLEAN` regression; scorer unit tests + the common-mode-accepts-a-raw-rejected-positive
  test; the held-out refactor's headline-reproduction guard), `:core:dsp:test` (any dsp helper),
  `:core:matching:test` (if §9 runtime option lands: byte-identical `RAW`), the full `:core:*` set,
  guardrail bundle, `make verify`. The **real** TORGO run (corpus at `~/torgo`) is executable this session:
  `./gradlew :core:eval:test --tests "*TorgoEvalTest*" -Dtorgo.dir=~/torgo -Dtorgo.report=<f>
  -Dtorgo.reject=true -Dtorgo.conditions=true` → the H1 verdict + condition grid + ambient proxy.
- **Blocked (needs the world):** true far-field/reverberant + continuous-ambient recordings (Bucket B) to
  turn the simulated-channel probe and ambient proxy into field numbers; on-device mic/CPU (Bucket B).
  Recorded as blocked; this plan delivers everything up to that point.

## Standards & Guardrails Evidence

- **Accuracy honesty (FRR+FAR, matched held-out FAR, no bare %):** DoD Part 2 + §7; enforced by
  `scripts/audits/verify-plan-workflow-guardrails.mjs`; EVAL-002 (`docs/ai/ACTIVE_DEV_RULES.md`).
- **Pre-registration vs best-of-grid (D3/voting lesson):** §Approach + Risk 1; precedent
  `docs/testing/2026-07-06_frr-far-torgo.md` §D3, `docs/errors/2026-07/2026-07-06_recognizer-voting-claim-vs-code.md`.
- **Additive/default-preserving core change + threshold-scale protection:** §9 + Constraints; audits
  `2026-06-28_dtw-length-normalization-convention`, `2026-06-28_mfcc-cmvn-misnomer`.
- **On-device / language-independent / no normal-speech prior:** Constraints (per-trial own-command cohort);
  `research/04_build_and_reuse_plan.md`.
- **Worktree-first substantive change; `make verify` before done; incident on non-trivial error:**
  metadata Worktree + §10 + `AGENTS.md`.

---

### Self-score 96/100

- **Evidence grounding & dimension coverage (29/30):** every seam cited to `path:line` (`Evaluator.kt:25`,
  `TorgoEval.kt:117-166`, `TemplateMatcher.kt:60/78-86`, `MfccExtractor.kt:49`, `TorgoEval.kt:28`,
  `Dtw.kt:18/74`); FRR+FAR framing per condition and per scorer. −1: the exact McNemar-at-matched-FAR
  procedure is approximate (realized FARs differ slightly) — disclosed, not eliminated.
- **Required structure (15/15):** all template sections + Standards & Guardrails Evidence; no placeholders.
- **Concreteness & verifiability (20/20):** every step names its file(s) and its check; the real TORGO
  invocation is given and runnable this session.
- **Risk & reversibility (15/15):** blast radius named; the one runtime change is additive/default-off and
  reverts by dropping a field; the honesty blocker has an explicit mitigation.
- **Test / shift-left (10/10):** regression guard (headline reproduction), determinism tests, the
  no-op-refutation test, rank-1-invariance test all named.
- **Scope discipline (7/10... rounded into 10 after trimming):** delivers exactly the two asked-for pieces;
  runtime adoption is *conditional* on measured significance (not gold-plated); `:app` wiring explicitly
  deferred as Bucket B. −0 after cutting margin/ratio to exploratory-only.
</content>
</invoke>
