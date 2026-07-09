# Plan: Complete the automated SOTA scorecard — build the five NOT_MEASURED domains

- **Date:** 2026-07-09
- **Phase:** n/a (measurement tooling — extends the automated-SOTA-scorecard plan, done 2026-07-08)
- **Roadmap item:** Turn every `NOT_MEASURED` cell of the automated SOTA scorecard into a real,
  fully-automated, scripted measurement — no waiting for people, no waiting for physical devices.
  Simulate what cannot be measured directly, with every assumption and limitation made explicit.
- **Status:** done (A-deliverables implemented 2026-07-09; D7/D11/D12/D13 band, D10 first-principles-argued,
  all guardrails + `:core:eval` static/test green)
- **Worktree:** `.claude/worktrees/sota-measurement-complete` (measure-only tooling; no product-runtime change)
- **Plan quality:** 98/100 (advisor-gated; two blocking design fixes applied — composite = measurement-backed
  domains only; D10 recast as by-construction + non-tautological proxy, excluded from composite)

## Goal

`make sota-score-full` currently leaves **5 of 15 domains `NOT_MEASURED`** (D7 wake detection,
D10 language independence, D11 latency, D12 battery, D13 enrollment efficiency) and one (D7)
carries a **broken mechanism reference** — `SotaScorecard.kt:139` names `in_regime.py mfcc --emit`,
but `in_regime.py` has no `--emit` (verified: `grep -n emit scripts/eval/ssl_frontend_spike/in_regime.py`
returns nothing). D15 (guardrail coverage) is structural-by-design, not a performance gap — it stays
NOT_MEASURED-by-design with a doc note, not a fabricated band.

Deliver a real scripted measurement for **D7, D11, D12, D13** (which now land a band) and a scripted
**diagnostic** for **D10** that empirically justifies arguing it from first principles. Result:
**13/15 domains banded** (D1–D9 minus none, + D11/D12/D13), **D10 first-principles-argued** (NOT_MEASURED
with a rich reason + by-construction prose), **D15 structural** — each with config-explicit provenance and
an honest fidelity tag.

> **D10 note (advisor-gated):** two proxy protocols were built and run; both fail for the same
> first-principles reason — DTW distance is only informative for *same-content* pairs and single-read
> Common Voice has no repeated command-words. augment-self-match → ~100% (tautology); cross-clip
> identification → chance in every language (English anchor ≈ 1/N). A cross-language Δ of two noise values
> is the **null**, not "a measurable signal" — mapping it to *any* band (600 or 1000) launders noise. So
> D10 stays NOT_MEASURED; the `lang_indep_rank1.py` diagnostic's null output is kept as the reproducible
> evidence, and language independence is argued by-construction (no LM/lexicon/phoneme in the shipped MFCC
> path; Zhang 2014; Picovoice 89.2% untuned English corroboration) in doc prose — never in the band table.

## Context & Constraints (inherited from the automated-SOTA-scorecard plan)

- **Wall-dominated composite = measurement-backed domains ONLY.** The headline is the *minimum* band
  over the composite pool, so the pool must contain only domains whose value comes from a **real run on
  the shipped (or faithful-mirror) front-end** — otherwise a derived/scaled number can later *set* the
  wall as the FRR/ambient walls are fixed, fabricating the very number the scorecard exists to report
  honestly. The domain-bands doc is explicit: D11/D12 are "physical device only" and the method note bars
  "theoretical derivations, no hand-waves" from the bands. Counting rule applied per domain — *is the
  value backed by a real run on real data?*:
  - **count:** D1–D6 (existing), **D7** (real TORGO+LibriSpeech, MFCC mirror, PROXY like D3), **D13**
    (real TORGO template sweep, shipped front-end).
  - **show + band + tag, but EXCLUDE:** **D10** (proxy + by-construction), **D11** (host-timing × scaling
    constant), **D12** (pure analytical derivation), and the pre-existing **D14** (confounded,
    `SotaScorecard.kt:57`). Excluding is not hiding — each is displayed with a band and an explicit
    provenance; it just cannot *set* the composite wall.
  - This satisfies the task ("mechanisms 100% done, scripted, documented for all unmeasured domains") —
    the mechanism existing is orthogonal to whether it may set the wall.
- **No fabrication** — every emitted value comes from a real run on real data present on this host; a
  domain we genuinely cannot even simulate stays `NOT_MEASURED` with the exact reason. D15 is the only
  such case and it is structural (guardrail count), not a performance metric.
- **Fidelity is first-class** — each new domain gets an explicit `Status`
  (`MEASURED`/`PROXY`/`SIMULATED_CHANNEL`/`SIMULATED_DEVICE`/`LOW_FIDELITY`) and a provenance string that
  names the front-end, corpus, simulated element, and off-/on-device status. New enum value
  `SIMULATED_DEVICE` for host-measured-then-device-scaled domains (D11/D12).
- **MFCC fidelity anchor** — the Python spikes' `harness.py` MFCC is built to match the shipped Kotlin
  `MfccExtractor` (`n_mfcc=13, n_mel=26, frame 25ms/shift 10ms`, orthonormal DCT-II; the source comment
  reads "matches Kotlin dct() exactly" — `scripts/eval/ssl_frontend_spike/harness.py:159`). So the
  off-device numpy MFCC arm is a faithful mirror of shipped `none`; stated as the fidelity caveat, not
  claimed bit-identical.
- **EVAL discipline (EVAL-002/003/004/005)** — new simulated numbers are exploratory/NOT-banked; the
  measurement docs cite the held-out/label/replication/fidelity rules; `verify-sota-measurement.mjs`
  guardrail must stay green.
- **Simulate, don't wait** — D11/D12 are documented as "physical device only." First-principles route:
  measure the shipped compute on the host JVM, scale to a Pixel 6 via a *documented, cited* CPU factor
  and power model; the assumption (host→device scaling constant) is explicit and adjustable.

## Approach — one harness per domain, reusing the existing entry points

Two integration seams already exist and are reused verbatim (no new plumbing invented):
1. **JVM domains** run inside `SotaScorecard.run()` via real `core:eval` entry points (like D1–D6).
2. **Off-device domains** arrive through the existing `--emit` key=value bridge (`domainN_value=`,
   `domainN_config=`) that `readMetrics()` already parses (like D8/D9).

| Domain | Metric (from domain-bands doc) | Route | Data (verified present) | Status tag |
|---|---|---|---|---|
| **D7** Wake detection @ ≤0.5 FA/hr | detection rate of speaker's own template in bg at ≤0.5 FA/hr | `in_regime.py --emit` (mfcc arm, torch-free) | `~/torgo` + `~/picovoice-benchmark/LibriSpeech` | PROXY |
| **D10** Language independence | rank-1 Δ (pp) non-English vs English | `lang_indep_rank1.py` **diagnostic** (no band-feeding emit) → argued by-construction in prose | CV `{6 langs × 50 wav}` + LibriSpeech anchor | **NOT_MEASURED** (null proxy) + first-principles prose |
| **D11** Latency P50 | end-to-end P50 ms | new `LatencyEval.kt` (host timing, device-scaled) | `~/torgo` | SIMULATED_DEVICE — **excluded** |
| **D12** Battery %/hr | active-listening %/hr | new `BatteryModel.kt` (first-principles) | derives from D11 duty cycle + cited constants | SIMULATED_DEVICE — **excluded** |
| **D13** Enrollment efficiency | rank-1(1 template) as fraction of k=5 saturation | new `EnrollmentEfficiencyEval.kt` | `~/torgo` | MEASURED — counts |

### D7 — in-regime wake detection (`in_regime.py --emit`, torch-free)
- `in_regime.py mfcc <spk> <bg_min>` already does LOO detection of a speaker's own words against
  LibriSpeech background with per-window VAD (the doc's exact protocol, §183–206 of domain-bands). It is
  numpy-only (no torch) — confirmed by its imports (`import numpy as np; import harness as H`).
- **Add** `--emit=<file>` (mirroring `sweep_ssl.py`/`dual_cascade_verify.py`): after computing the
  detection/FA-hr curve, find the operating point with **FA/hr ≤ 0.5** and write
  `domain7_value=<detection fraction>` + `domain7_config=in-regime MFCC-DTW, speaker <spk>, LibriSpeech
  bg <h>h, per-window VAD, detection @ ≤0.5 FA/hr (off-device numpy MFCC mirrors shipped none)`.
- If no threshold reaches FA/hr ≤ 0.5 (all-or-nothing), emit the detection at the tightest achievable
  FA/hr and record the achieved FA/hr in the config — never silently report the ~0-FA/hr number as if it
  were the ≤0.5 point (the doc explicitly flags that current numbers are @ ~0 FA/hr, not the matched
  point). This closes the honesty gap the doc names.
- `SotaScorecard.sslDomain(7)`: fix the config/howto to the real `--emit` command; keep `counts=true`,
  `Status.PROXY` (synthetic-ish in-regime, optimistically biased vs real household audio).

### D10 — language independence (NOT_MEASURED: null proxy → argued by-construction in prose)
- **Empirically-confirmed conclusion (advisor-gated, after building & running two protocols):** single-read
  Common Voice cannot support a Domain-1-style rank-1, because **DTW distance is only informative for
  same-content pairs** and CV has no repeated command-words per speaker. Evidence:
  - augment-self-match (enroll clip, query augmented copy of itself) → **~100%** for every language: a
    tautology (audio fingerprinting), zero discrimination. Rejected.
  - cross-clip identification (enroll one word-window per clip, query a *different* window, rank-1 =
    nearest template is own clip) → **chance** (English anchor **1.8% ≈ 1/40**) in every language.
  A cross-language Δ of two noise values is the **null**, not "any measurable signal"; mapping it to a
  band (whether Δ=0→1000, or a gated→600 floor) launders noise. Both are rejected.
- **Deliverable = the by-construction argument in doc prose, not a table cell.** The shipped path is 13
  MFCC + DTW with **no LM, lexicon, or phoneme layer** — identical code for every language
  (`core/dsp/src/main/kotlin/com/speechangel/core/dsp/MfccExtractor.kt`). External support: Zhang (2014) language-independent DTW (PLOS ONE);
  the same MFCC-DTW family scoring **89.2% cross-speaker English rank-1 on Picovoice, untuned**. This is
  exactly the task's "no direct evidence → first-principles + real-life data + infer" instruction. Lives
  in `docs/product/2026-07-08_sota-domain-bands.md` §10; the doc's own rule bars derivations from the
  *band table*, so the inference is prose and the band cell stays measurement-only.
- **Script kept as a DIAGNOSTIC:** `lang_indep_rank1.py` runs the cross-clip protocol and, via `--emit`,
  writes a **`#`-commented** diagnostic line (skipped by `readMetrics`) — its null output is the
  reproducible evidence justifying the first-principles route. It never emits a `domain10_value`.
- **Status:** `NOT_MEASURED` with a rich reason; **excluded** from the composite by construction.

### D11 — latency P50 (`LatencyEval.kt`, host-measured, device-scaled)
- Enroll templates for a representative TORGO speaker; for each held-out utterance, time the **shipped
  decide path** end to end: `MfccExtractor` over the utterance + `TemplateMatcher` DTW against all
  templates (the real `Recognizer` inner loop). JVM warmup iterations, then N timed reps; report host
  **P50** (and P99) in ms via `System.nanoTime()`.
- **Device scaling (explicit, cited):** `device_P50 = host_P50 × DEVICE_SCALE`. `DEVICE_SCALE` is a
  named constant = (host single-core throughput) / (Pixel 6 Tensor Cortex-X1 single-core throughput),
  using Geekbench-6 single-core as the common yardstick. Host CPU model is read from `/proc/cpuinfo` at
  measurement time and echoed into the provenance; Pixel 6 GB6 single-core ≈ 1050 (published). Provisional
  `DEVICE_SCALE ≈ 2.5` for a modern desktop x86 core (GB6 ≈ 2500), **finalized from the actual host
  `/proc/cpuinfo` at implementation** and rounded conservatively (bias the device *slower*). The constant,
  its source, and the rounding direction live in the file header and the provenance string.
- **Status:** `SIMULATED_DEVICE`, **`counts=false`** (host-scaled, not a device measurement — excluded).

### D12 — battery %/hr (`BatteryModel.kt`, first-principles)
- Analytical model consuming D11's measured **per-second compute cost** (frames/s × ms/frame ⇒ CPU
  active fraction = duty cycle) plus documented Pixel 6 constants:
  `battery_Wh = 4614 mAh × 3.85 V ≈ 17.8 Wh` (Pixel 6 spec); `%/hr = (P_capture + P_active × duty) /
  battery_Wh × 100`, where `P_capture` (always-on mic + light DSP) and `P_active` (full pipeline burst)
  are named constants sourced from published always-on-audio/SoC power figures (cited in the header,
  with a ±band).
- Every constant is a `const val` with an inline source comment; the model is deterministic and unit-
  tested against the band cutoffs. Provenance string names each assumption.
- **Status:** `SIMULATED_DEVICE`, **`counts=false`** (pure analytical derivation — excluded).

### D13 — enrollment efficiency (`EnrollmentEfficiencyEval.kt`, TORGO template sweep)
- Monte Carlo template-count sweep: for `k ∈ 1..5`, repeatedly (fixed seeds) sample k templates/command,
  measure aggregate rank-1 on the held-out remainder; average over iterations. **Efficiency =
  rank1(k=1) / rank1(k=max)** (the domain-bands "1-shot FRR as % of saturation", expressed on the rank-1
  axis so it reuses the existing `Evaluator`/`TorgoEval` machinery).
- **Status:** `MEASURED` (real TORGO, on the shipped front-end), `counts=true`.

Rejected alternatives: (a) a JVM Common Voice corpus reader for D10 — the CV clips need arbitrary-rate
WAV handling + the single-read shape still forces a synthetic protocol, so the numpy spike (which already
has the matched MFCC + augmentation math) is less code and reuses the proven bridge; (b) waiting for a
physical device for D11/D12 — explicitly out of scope per the task; (c) fabricating D15 a band — it is a
structural count, kept NOT_MEASURED-by-design with a doc note.

## Steps (each ⇒ one logical commit)

1. **D13 JVM** — `core/eval/src/main/kotlin/com/speechangel/core/eval/EnrollmentEfficiencyEval.kt`
   (+ unit test). Simplest, pure-TORGO, establishes the JVM-domain pattern for the sweep.
2. **D11+D12 JVM** — `LatencyEval.kt` + `BatteryModel.kt` (+ unit tests for the band math and the model
   constants). Add `SIMULATED_DEVICE` to `SotaScorecard.Status`.
3. **D7 Python** — add `--emit` to `in_regime.py` (mfcc arm) with the ≤0.5-FA/hr operating-point logic.
4. **D10 Python** — new `lang_indep_rank1.py` with `--emit`; reuse `harness.py` MFCC + augmentation.
5. **Scorecard wiring** — `SotaScorecard.run()` folds D7/D10 from the bridge and D11/D12/D13 from the new
   JVM harnesses; fix the D7 broken-reference config; update `renderMarkdown/renderJson`. Update
   `SotaScorecardTest` (band-mapper fidelity for the 5 new domains + integration assertions that they are
   no longer NOT_MEASURED and the composite stays `<600`).
6. **Makefile + docs** — extend `sota-score-ssl` to run the D7/D10 spikes (torch-free, so also runnable
   with plain numpy); add a new measurement doc `docs/testing/2026-07-09_sota-domains-completed.md`
   (EVAL-cited, honesty-bannered); update the "Current band" cells and validation-script index in
   `docs/product/2026-07-08_sota-domain-bands.md` + the D7 note; update
   `docs/product/2026-07-08_sota-wake-word-reference.md` §11 coverage; mark this plan `done`; update
   `docs/plans/INDEX.md`.

## Definition of Done

- **Accuracy-honesty framing (FRR + FAR):** this is measurement tooling, not a recognizer change — it does
  not move any FRR or FAR. The binding walls it must preserve are the **held-out FRR 75.7% @ FAR ≤ 5%**
  (D2) and the **ambient FA/hr ~82/hr** (D3, the per-hour FAR proxy); the new domains must leave both, and
  therefore the composite, unchanged. Success is *reproducing* those FRR/FAR walls, never improving a
  bare-% number.
- `make sota-score-full SOTA_PY=$(HOME)/torch-venv/bin/python` bands **13/15 domains** (D1–D9 land where
  their data allows, + D11/D12/D13); **D10 is NOT_MEASURED with a first-principles reason** and **D15 is
  structural**. The composite stays **wall-dominated `<600`** (the FRR @ FAR≤5% and ambient-FAR walls are
  unchanged — the new domains cannot raise it).
- **D7** emits a real detection-@-≤0.5-FA/hr fraction from `in_regime.py --emit` (or, if unreachable, the
  tightest-FA/hr detection with the achieved FA/hr named in the provenance — never mislabeled). Counts.
- **D10** runs `lang_indep_rank1.py` as a **diagnostic**: it writes only a `#`-commented null-result line,
  emits **no** `domain10_value`, and D10 stays NOT_MEASURED; language independence is argued
  by-construction + Zhang-2014 + Picovoice-89.2%-untuned in domain-bands §10 prose.
- **D11/D12** emit host-measured, device-scaled P50 ms and %/hr with every scaling/power constant a cited
  `const val`, **excluded from the composite**; unit tests assert the band math and that the provenance
  names the assumptions.
- **D13** emits a real TORGO template-sweep efficiency fraction (counts); unit test on the sweep
  aggregation.
- **Composite invariant:** the counting pool is exactly the measurement-backed domains (D1–D7, + D13);
  D11/D12/D14 are `countsForComposite=false`; D10 is NOT_MEASURED. `SotaScorecardTest` asserts this
  per-domain and that the composite stays wall-dominated **`<600`**.
- Every new value is config-explicit; the report keeps the SYNTHETIC/SIMULATED honesty banner and adds a
  SIMULATED_DEVICE + "excluded-from-composite" caveat line.
- `node scripts/audits/run-all.mjs` = all checks PASS (incl. `verify-sota-measurement.mjs`);
  `:core:eval:test` green (unit tests always; integration tests when `~/torgo` present — verified present).
- No product-runtime / matcher / DSP / threshold code changed → no `make bench-picovoice` re-run needed.

## Risks & Mitigations

- **R1 — a simulated/derived domain silently *sets the wall*.** The composite is a living instrument: as
  the FRR/ambient walls get fixed, the headline shifts to the next-lowest counting domain. A
  theoretically-derived D12 or host-scaled D11 sitting in the pool could later fabricate the reported
  number. *Mitigation:* the composite pool is **measurement-backed domains only** — D10/D11/D12 are
  `counts=false` (shown, banded, tagged, but never eligible to set the wall), exactly as D14 already is
  (`SotaScorecard.kt:57`). Only D7 (real corpora) and D13 (real TORGO) join the counting pool.
- **R2 — device scaling constant is wrong.** *Mitigation:* the constant is a single documented, cited
  `const val` with a conservative (device-slower) default and a ±note; a wrong constant moves D11/D12 by a
  band at most and never affects the `<600` composite. Rollback = revert the constant.
- **R3 — D7 ≤0.5-FA/hr point unreachable for MFCC.** *Mitigation:* explicit fallback that reports the
  achieved FA/hr in provenance rather than the ~0-FA/hr number, closing (not repeating) the doc's known
  mislabel.
- **R4 — D10 proxy is tautological / misleadingly high.** *Mitigation (advisor):* the augment-self-match
  design is rejected; the proxy is a genuinely-failable cross-clip identification task, tagged
  LOW-FIDELITY and **excluded from the composite**; language independence is carried by the
  by-construction argument + Zhang 2014, with the proxy explicitly subordinate; per-language absolute
  rank-1 is shown in the doc, not just Δ.
- **R5 — guardrail (`verify-sota-measurement.mjs`) blocks the new doc.** *Mitigation:* the new testing doc
  carries EVAL-002/003/004/005 citations + the honesty banner by construction; run the guardrail before
  each commit (session-close protocol §5).
- **R6 — flaky/slow timing (D11) or CV augmentation (D10) in CI.** *Mitigation:* both are `[measure-only]`,
  gated behind `-D` props / corpus presence with `assumeTrue` skips, exactly like the existing
  `picovoice.dir` gate — never a CI gate; `make test` stays green without the corpora.
- **Blast radius:** measure-only tooling; no runtime/matcher/DSP/threshold change. **Rollback:**
  `git revert` the worktree merge.

## Test & Verification

- **Unit (always, no corpus):** band-mapper fidelity for D7/D10/D11/D12/D13 in `SotaScorecardTest`;
  `EnrollmentEfficiencyEval` sweep aggregation; `LatencyEval` percentile + scaling math; `BatteryModel`
  band math + constant sanity. `./gradlew :core:eval:test --tests "*SotaScorecardTest*"` etc.
- **Integration (corpora present — all verified on host):** `make sota-score-full
  SOTA_PY=$HOME/torch-venv/bin/python` produces 14/15 measured, composite `<600`, report written.
- **Python spikes:** `in_regime.py mfcc F01 60 --emit=/tmp/m.txt` and `lang_indep_rank1.py --emit=/tmp/m.txt`
  run torch-free and write parseable `domain7_value=`/`domain10_value=` lines.
- **Guardrails:** `node scripts/audits/run-all.mjs` all-PASS before every commit.
- **`verify` skill:** drive `make sota-score-full` end-to-end and read the generated `sota-scorecard.md`
  to confirm the 5 cells are populated with the expected bands + tags (observed behavior, not just tests).

## Standards & Guardrails Evidence

- Wall-dominated composite is preserved: `SotaScorecard.kt:60` (`bindingBand = minOf`).
- Emit bridge reused, not reinvented: `SotaScorecard.kt:222` (`readMetrics`), `sweep_ssl.py:112`,
  `dual_cascade_verify.py:319` (existing `domainN_value=` writers).
- MFCC fidelity anchor: `scripts/eval/ssl_frontend_spike/harness.py:159` ("matches Kotlin dct() exactly").
- Metric definitions taken verbatim from `docs/product/2026-07-08_sota-domain-bands.md` (D7 §183, D10
  §266, D11 §291, D12 §316, D13 §337); band cutoffs from `DomainBands.kt:78–126`.
- EVAL discipline enforced by `scripts/audits/verify-sota-measurement.mjs`; session-close protocol from
  `CLAUDE.md §8`.
