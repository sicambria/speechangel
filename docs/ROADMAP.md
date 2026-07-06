# SpeechAngel Roadmap

Derived from `research/04_build_and_reuse_plan.md` §5 (phased plan) and §7 (non-negotiables). The
trackable artifact: each item has a checkbox and a status. Update status as work lands; keep
acceptance criteria honest (FRR + FAR/hour, never a bare "99 %").

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done · status tags: `planned` /
`active` / `blocked` / `done`.

> **Last reconciled: 2026-06-28** against the actual codebase. Basis: `make verify` ran green on this
> host (`detekt spotlessCheck :app:lintDebug test :app:assembleDebug` → BUILD SUCCESSFUL, debug APK
> produced) and an evidence-based source inventory. Checkboxes below reflect *verified code state*,
> not aspiration. Per-item plans live under `docs/plans/2026-06/`.
>
> **Phase 3 planned + Bucket-A implemented 2026-07-05:** the six Phase 3 items each carry a plan
> (self-scored 93, advisor-reviewed) — see `docs/plans/INDEX.md` "Phase 3 planning batch" — and every
> autonomously-implementable slice is built, tested, and committed. Two items are code-complete + wired
> to a user entry point (`[x]`, on-device visual QA noted Bucket B): the vocabulary-distinctness helper
> and shareable command packs. The other four stay `[~]` because the deliverable itself needs an absent
> resource (trained QbE encoder, whisper.cpp native model, Play/F-Droid accounts + signing key) or an
> external quality measurement (a real dysarthric-inclusive corpus for far-field gains). No FRR/FAR
> number, bake-off winner, or B/C completion is claimed._
>
> **Strategic rethink 2026-07-06 (this revision):** the first real numbers + the SOTA sweep inverted the
> risk model. The phase ladder below is now a **capability inventory ("what is built")**, not the forward
> plan — Phases 0–2 are code-complete to the emulator ceiling, so the remaining risk is no longer "can we
> build it" but **"does the core hit deployable numbers, and can it stay always-on without false-firing."**
> The forward plan is **Critical Path v2** (next section). Two items were re-classified: **QbE / a learned
> encoder is promoted from "Phase-3 delight" to the core accuracy bet (CP-1)**, and the **always-on FAR
> blocker is elevated to CP-2**. Nothing built was discarded; the *sequencing* changed.

---

## ⭐ Critical path v1 (2026-07-06 product scorecard) — EXECUTED

> _Superseded by Critical Path v2 below. Retained because all three items executed and are re-score
> triggers; v2 picks up where these left off._

> The product was scored **442/1000 — pre-alpha** (`docs/product/2026-07-06_product-maturity-scorecard.md`).
> The gating risk is **not** any single feature: it is that the core hypothesis — MFCC-DTW template
> matching hitting a usable FRR/FAR *on atypical/dysarthric speech* — is **unmeasured**, and the app
> has **never run on a device end to end**. No Phase-3 enhancement (QbE, far-field, packs, dictation)
> should jump ahead of these three. In order:
>
> 1. **First real FRR/FAR.** Pull **TORGO** (free, ~a day; `docs/plans/2026-06/external-asset-acquisition.md`),
>    run the built `core:eval` harness, produce the first *real* number and kill the `SYNTHETIC` banner.
>    Cheapest possible retirement of the existential risk — do this first.
> 2. **One end-to-end on-device run.** Use `make emulator` + install/launch and watch the
>    `ListeningService → WakeGatedRecognizer → CommandActionBus → SpeechAngelAccessibilityService`
>    loop actually fire against real audio (latency, false-fire rate, CPU).
> 3. **Minimal always-on survival soak** (Doze / OEM task-kill / reboot) on a device.
>
> Each of (1) and (2) is a re-score trigger — they move the product from pre-alpha to alpha.

> **Results (2026-07-06 — `docs/plans/2026-06/first-real-frr-far-torgo.md`, all three executed):**
>
> 1. **First real FRR/FAR — DONE.** TORGO (dysarthric F01/F03/F04) run through the built `core:eval`
>    harness, **speaker-dependent**, via a new `WavFile`/`TorgoCorpus`/`TorgoEval` seam. `SYNTHETIC`
>    banner gone. **Verdict: GO** — rank-1 (nearest-template) accuracy **55.4%** dysarthric / **74.6%**
>    control, **10–40× chance**, so the MFCC-DTW hypothesis holds; but the single-template un-calibrated
>    baseline is **60–79% FRR at FAR ≤ 5%** — real signal, not yet deployable. Full numbers +
>    methodology: `docs/testing/2026-07-06_frr-far-torgo.md`. *Only the FRR half of Phase-0's "Measure
>    FRR/FAR" is retired; the always-on ambient FAR/hour budget is not measured (TORGO has no continuous
>    ambient stream).*
>
>    **Follow-through (`docs/plans/2026-07/torgo-eval-honest-improvements.md`, DONE 2026-07-06):** the
>    eval was made **held-out** (leave-one-fold-out threshold selection, rule EVAL-002) and a docs-vs-code
>    error corrected — the matcher is **1-NN min-distance, not a "vote"** (that claimed lever was a no-op;
>    incident `2026-07-06_recognizer-voting-claim-vs-code.md`). Held-out results: global-threshold FRR
>    **78.3%** @ FAR 5.1% (≈ in-sample, so the baseline held); **per-command calibration is a
>    non-improvement** (held-out FAR balloons to 24–34%); the deployment slice (≤25 cmds) is **70.7%**;
>    and the front-end bake-off surfaced a **directional** hypothesis — static MFCC is best/tied in all
>    3 speakers and noise reduction is consistently worse — but the aggregate margin (59.2% vs 55.4%) is
>    within sampling error, so it needs a **paired test** before adoption, not a best-of-grid pick. The
>    real improvement path is more enrolled templates + QbE, **not** per-command threshold tuning.
> 2. **On-device e2e — DONE at the emulator ceiling.** Build/install/launch (no crash), full UI +
>    navigation, `SpeechAngelAccessibilityService` **bound & running**, `Try`→`Recognizer` reactive.
>    Real audio→action fire, latency, false-fire, CPU need a **physical device** (silent emulator mic).
>    `docs/testing/2026-07-06_on-device-e2e.md`. Phase-1 exit **not** flipped.
> 3. **Always-on soak — DONE at the emulator ceiling.** Survived forced deep Doze; after reboot
>    `BootReceiver` posted the legal "Tap to resume listening" notification (SDK-35-legal path).
>    OEM task-kill + battery soak are physical-device-only. `docs/testing/2026-07-06_always-on-soak.md`.
>    Phase-2 exit **not** flipped.

---

## ⭐⭐ Critical path v2 — the two bets that decide the product (2026-07-06 rethink)

> **The reframe.** v1 retired "is the hypothesis alive" (yes — 10–40× chance) and "is it wired" (yes — to
> the emulator ceiling). What it *revealed* is that the shipped MFCC-DTW core is **~1–3 orders of
> magnitude from deployable** (76%/62% FRR @ ~5% FAR; **~82 FA/hr** ambient), while modest neural KWS
> baselines get ~10% FRR on dysarthric — *but* those baselines are closed-vocabulary, trained on that
> vocabulary, and not language-independent, so 10-vs-76 **bounds the opportunity, not a proven model gap**
> (the "non-comparable protocols" caveat of `…sota-competitive-bar.md`). What *is* supported is that the
> **population is tractable** — Euphonia's 13.9% WER *personalized* dysarthric ASR, and personalization is
> exactly what SpeechAngel does. So the product now lives or dies on **two bets**, both gated on **real
> data** — not on building more features. Everything in Phases 0–3 is a means to
> these; nothing below Phase-3 "reach" should jump ahead of CP-1/CP-2.

- [ ] **CP-0 — Acquire real data (the prerequisite for every number below).** TORGO is in hand (done);
      the gating long-lead asset is now the **Speech Accessibility Project (SAP)** DUA — it has a
      "digital-assistant commands" category and is the only corpus that makes CP-1/CP-2 trustworthy.
      **Start the DUA immediately** (lead time is the real cost); add EasyCall (built-in OOV split) and
      UASpeech (per-severity) in parallel. *Without CP-0, CP-1 and CP-2 are unfalsifiable.*
- [ ] **CP-1 — The accuracy bet: does a learned encoder beat MFCC-DTW *while preserving our
      differentiators*?** The **gating condition is constraint-preservation — language-independence +
      1-shot arbitrary-word enrollment** (our 95/85 axes, the whole reason to exist); an option that erodes
      them is out no matter its FRR. Within that box, test a learned few-shot encoder
      (ZP-KWS/PhonMatchNet-class phoneme-supervised — R-SOTA-1) against MFCC-DTW at matched, held-out FAR on
      real dysarthric audio (CP-0). The opportunity is real but **not a proven model gap**: the ~10% FRR
      neural baselines win partly by solving an easier (closed-vocab, trained) task; the genuinely
      constraint-matched SOTA point is **ZP-KWS at ~29–33% FRR@1%FAR** — far better than 76%, nowhere near
      10%. Success = a significant FRR reduction at matched FAR, at shippable size, **with
      language-independence + 1-shot intact**. This is the promoted QbE work (Phase 3 → here).
      **↳ First measurement (2026-07-06, `docs/testing/2026-07-06_cp1-ssl-frontend-ceiling.md`):** a
      `[measure-only]` ceiling spike (harness reproduces the committed baseline to the decimal) gives a
      **GO** — best-learned **WavLM-L12 pooled-cosine 71.9% rank-1** vs MFCC-DTW 55.4% (−37% rel error
      agg, **≥50% on the F01/F04 deployment slice**, McNemar **p=2×10⁻⁶**). The 2×2 decomposition sharpens
      the target: **the lever is a fixed-dim QbE embedding + cosine prototypes (`QbeEncoder` seam), not a
      front-end swap** (WavLM-under-DTW ties MFCC; MFCC-under-pooling drops to 39.3%). Model scale is not a
      lever (WavLM-large ≈ base-plus). **Next = the CP-1 build:** distill the deep-SSL pooled embedding
      into a ~1–2M student, gated on language-independence (untested on English TORGO) + on-device
      size/latency. NB **CP-2 stays independent + binding** — even the maximal encoder leaves FRR@FAR≤5%
      at 66% (78.3%→66.3%), so a better encoder does not fix the always-on FAR wall.
- [ ] **CP-2 — The deployability bet: a Stage-1 wake cascade to ≤0.5 FA/hr on real ambient.** The
      always-on false-fire rate (~82 FA/hr today, ~160× budget) is what kills always-on assistants and no
      Stage-2 accuracy matters until it's fixed. Use openWakeWord as a **benchmark reference** for the
      achievable FA/hr (it scores low on language-independence, so it's a yardstick, **not necessarily the
      adopted gate**); the **constraint-preserving Stage-1 option is the enrolled-DTW / personalized wake
      template** already built (`WakeWordGate`). Target **≤0.5 FA/hr at the wake stage alone** on a real
      recording (R-SOTA-2; `-Dambient.wav` seam is built).
- [ ] **CP-3 — Real-device audio metrics (the alpha gate).** Latency, CPU, battery drain, and real
      false-fire rate on a **physical device** — the numbers the emulator's silent mic cannot produce
      (unblocks the frozen Phase-1/Phase-2 exits). A debug `AudioRecorder` WAV-injection binding makes
      CP-1/CP-2 measurable on-device before hardware.

> **Release posture (ethics + product).** A *marketed, general* F-Droid/Play release is **frozen behind
> CP-1/CP-2** — shipping a 76%-FRR / 82-FA/hr assistant to immobilised, speech-atypical users would erode
> trust with exactly the people it exists to serve. What is *not* frozen: an **honestly-labelled,
> opt-in "experimental" build** whose purpose is to gather consented real-world audio/telemetry — that
> would directly feed CP-0 and is a legitimate parallel track, not a product claim.

**Sequencing:** CP-0 (data, long lead) starts now and runs under everything · CP-2 (deployability) and
CP-1 (accuracy) proceed in parallel once data lands — CP-2 has the nearer, cheaper win; CP-1 has the
higher ceiling · CP-3 gates the pre-alpha→alpha crossing. The R-SOTA-1..6 items below are the detailed
backing for CP-1/CP-2.

> **Exactly what each CP needs** — corpora, audio formats, model params, target ranges, error margins, and
> the honest "unknown, needs measurement" register — is specified in
> `docs/product/2026-07-06_cp-requirements-spec.md`.

---

## ⭐ SOTA competitive bar — derived items · status: `planned`

> Added 2026-07-06 from a competitive-landscape sweep of on-device wake-word / command spotting
> (`docs/product/2026-07-06_sota-competitive-bar.md`). That doc pins the external SOTA as concrete
> sourced numbers and places SpeechAngel in the same 7-axis ranking (**overall 59** — best-in-field on
> language-independence + trainability + transparency, worst on maturity + noise). **Acceptance targets
> adopted from the bar:** always-on **≤0.5 FA/hr** (openWakeWord) → stretch **≤0.1 FA/hr** (Porcupine);
> **FRR <5%** at that FAR, production-real **10% FRR @ 4 FA/hr** (Howl); **~97% @ 10 dB SNR** noise
> (Porcupine); atypical **FRR ~0.5%/FAR ~0.3%** is *achievable* closed-vocab (LRDWWS'24).
>
> **Caveat (governs all targets):** no system is verified across noisy + atypical + language-independent
> + user-trainable *simultaneously*; the bars come from non-comparable protocols (EVAL-002/003 discipline).

- [ ] **R-SOTA-1 — Zero-shot phoneme-matching encoder (ZP-KWS / PhonMatchNet-class).** Evaluate as an
      alternative/augmentation to MFCC-DTW in the dormant `QbeEncoder` seam — the SOTA that *shares* our
      language-independent + user-trainable constraints, at an **edge-deployable 1.55M params**
      (ZP-KWS, arXiv 2606.20106; FRR@1%FAR cut ~60% rel). Optional text-independent speaker-verifier veto
      branch. `planned` — research + `core:eval` A/B, gated on a corpus + license clearance.
- [ ] **R-SOTA-2 — Stage-1 wake cascade to fix the ~82 FA/hr blocker.** Benchmark openWakeWord + a
      personalized wake template as the always-on gate; target **≤0.5 FA/hr at the wake stage alone** on a
      real ambient recording (`-Dambient.wav` seam is built). **The deployability gate — highest priority.**
- [ ] **R-SOTA-3 — Adopt the Picovoice `wake-word-benchmark` protocol** (detection @ fixed FA/hr @ SNR)
      as SpeechAngel's reporting standard, folded into the `core:eval` condition grid, so our numbers are
      externally comparable. Cheap; unblocks comparable reporting now.
- [ ] **R-SOTA-4 — Adopt the LRDWWS'24 winner (PD-DWS) constraint-respecting techniques**
      (`research/word-spotting2409.10076v1.pdf`, FAR 0.32%/FRR 0.5%): (a) small SSL front-end for the QbE
      encoder [→ R-SOTA-1], (b) a **dual-filter cascade** — a length/second-opinion cross-verify at the
      decision layer as an FAR-cutting rejection stage (the honest `margin` lever), (c) TTS-dysarthric +
      MUSAN augmentation [→ R-SOTA-6]. Skip the ASR-branch default (breaks language-independence →
      Path-A only). NB: PD-DWS's *baseline* DS-TCN hits ~10% FRR on dysarthric, but it is closed-vocab,
      trained on that vocabulary, and not language-independent — so it **bounds the opportunity, not a
      proven model gap**. What *is* supported: the population is tractable (Euphonia's 13.9% WER
      *personalized* dysarthric ASR — personalization is what we do). The constraint-matched reference is
      ZP-KWS (~29–33% FRR@1%FAR), not 10%.
- [ ] **R-SOTA-5 — Common Voice (multilingual, CC0) as a language-independence eval corpus**; set
      **10% FRR @ 4 FA/hr** (Howl production) as the realistic milestone before the <5% stretch.
- [ ] **R-SOTA-6 — Attack the noise axis directly** (we score 25/100 vs mature-shipped 45–85): multi-condition
      enrollment/augmentation (RIR + MUSAN) + SNR-adaptive accept threshold, measured on the existing
      condition grid. The sim harness already proves noise is the dominant degrader.

**Sequencing:** R-SOTA-2 (FAR/deployability) first · R-SOTA-1 (accuracy ceiling) highest-ceiling · both
gated on R-SOTA-5's corpus + the SAP acquisition already listed below · R-SOTA-3 is cheap and immediate.

---

## Phase 0 — Matcher spike (2–3 wks) · status: `active`

Prove the core no OSS app has: record N commands on-device → MFCC + VAD + DTW match → multi-template
+ per-command threshold + reject, on one phone, ugly UI. De-risk before any UX investment.

- [x] `core:model` — domain types (commands, templates, match results). _done — JVM-tested; `core/model/src/main/kotlin/com/speechangel/core/model/Domain.kt`._
- [x] `core:dsp` — MFCC extractor (concatenate static+Δ+ΔΔ, never sum — LIVE BUG #1), mel filterbank,
      FFT, Silero-style VAD endpointing. _done 2026-06-28 — FFT, mel filterbank, energy VAD, static MFCC,
      and now **ΔΔ acceleration** (`DeltaOrder { NONE, DELTA, DELTA_DELTA }`, widths 13/26/39, concatenated
      not summed; tested). Also added a streaming `StreamingEnergyGate` (running noise floor) for Stage-1._
- [x] `core:matching` — DTW distance, `argmin` over templates, per-command distance threshold,
      OOV/reject. _done — length-normalised DTW + Sakoe–Chiba band, per-command thresholds, OOV reject
      (`RejectionReason.BELOW_CONFIDENCE`); JVM-tested incl. command discrimination._
- [x] `core:enrollment` — multi-template enroll, recognizer, repositories. _done — `Enroller`,
      `Recognizer`, repository interfaces; JVM-tested._
- [~] Measure FRR / FAR on real (incl. dysarthric) voices, quiet + home noise. _**FRR half DONE
      2026-07-06** — TORGO (dysarthric F01/F03/F04 + control FC01/FC02/FC03) run through `core:eval`
      speaker-dependent via new `WavFile`/`TorgoCorpus`/`TorgoEval`; `SYNTHETIC` banner gone; real rank-1
      **55.4% dysarthric / 74.6% control** (10–40× chance) + FRR/FAR at EER & low-FAR operating points
      (`docs/testing/2026-07-06_frr-far-torgo.md`). Still `[~]`: the **always-on ambient FAR/hour budget**
      (≤0.5 FA/hr on continuous audio) is unmeasured — TORGO has no ambient stream (Bucket B). Verdict:
      real signal, single-template untuned baseline not yet deployable._
- [~] Feature front-end bake-off (plain MFCC vs PLP vs robust embedding). _harness DONE & tested —
      `FrontEndBakeoff` computes an FRR + FA comparison across static / +Δ / +Δ+ΔΔ. Winner-on-real-voices
      blocked on the corpus; PLP deliberately descoped (MFCC variants only)._

**Phase 0 exit:** measured FRR/FAR on a real ~few-dozen-command set; the matcher beats a documented
FAR budget (≤0.5 false accepts/hr) for at least the in-quiet, distinct-command case. _NOT yet met —
gated on real recordings; the measurement machinery is the autonomous part._

---

## Phase 1 — Hands-free MVP (6–8 wks) · status: `active`

Fork the GUI skeleton; ship the core promise for non-rooted phones with cooperative OEMs.

- [x] `:app` module scaffolded + re-enabled in `settings.gradle.kts`. _done — built green._
- [x] `:data` module (Room persistence for enrolled templates). _done — Room entities/DAO +
      `RoomCommandRepository`/`RoomTemplateRepository`; Robolectric round-trip tested._
- [x] Microphone foreground service (`foregroundServiceType="microphone"` +
      `FOREGROUND_SERVICE_MICROPHONE`) — gate: `verify-foreground-service-types.mjs`. _done —
      `ListeningService`; manifest declares both; gate green._
- [~] Stage-1 (24/7) Silero VAD gate → software wake word (enrolled DTW wake OR microWakeWord).
      **↑ ELEVATED to Critical Path v2 / CP-2 — the ~82 FA/hr blocker is the deployability gate.** _core logic
      DONE & tested — `WakeWordGate` (matches wake templates only, gates Stage-2), `StreamingEnergyGate`
      (running-floor energy gate for short frames), and `ReservedCommands.commandTemplates()` (excludes the
      `__wake__` template from Stage-2 so it can't suppress real commands). PENDING (app/Bucket-B):
      `AudioRecorder.stream()` + `ListeningService` wiring (same-stream drain — note `StreamingEnergyGate`
      is built but not yet injected), a benchmarked openWakeWord/personalized wake stage (R-SOTA-2),
      battery measurement._
- [x] Stage-2 command matcher wired to the `core:*` engine. _done — `Recognizer` injected into
      `ListeningService`; Match → in-process `CommandActionBus`._
- [x] AccessibilityService — deterministic command→action table (`isAccessibilityTool="true"`). _done —
      `SpeechAngelAccessibilityService` + `DeviceAction` fixed table; no LLM in the loop._
- [x] 4-screen enrollment UX (Teach / Name-Map / Try / Always-on) + caregiver setup wizard. _built &
      `make verify` green — `AlwaysOnScreen` + `CaregiverWizard` added and wired into navigation (Name-Map
      folded into Teach/wizard). On-device visual/UX QA + real-caregiver usability are Bucket B._
- [x] Battery-optimization exemption flow. _built — `BatteryOptimization` (Play-permitted settings
      intent) + an Always-on entry point. The system dialog only appears on a device (Bucket B)._

**Phase 1 exit:** a non-rooted phone runs the full Teach→Try→hands-free loop end to end. _Core loop
is wired and builds; the always-on/battery/wake-word robustness pieces remain._

---

## Phase 2 — Persistence & policy hardening (6–8 wks) · status: `planned`

- [x] Assistant role (`RoleManager.ROLE_ASSISTANT`) for reboot survival. _built — `BootReceiver`
      (exported, `goAsync`) posts a **legal tap-to-resume** notification on boot (a `microphone` FGS
      cannot be started from BOOT_COMPLETED on SDK 35), reading the persisted enable flag; `AssistantRole`
      offers the API-29-guarded role request as optional hardening. Real reboot survival is Bucket B._
- [x] Per-OEM autostart handling (DontKillMyApp guidance). _built — `OemAutostart.resolve` (pure,
      unit-tested for Xiaomi/Huawei/Oppo/Vivo/Samsung/generic) + the Always-on guidance UI with fail-soft
      deep links. Actual OEM settings screens vary per device (Bucket B)._
- [~] Play Permission Declaration Form + prominent mic disclosure. _in-app parts built + wired —
      `MicDisclosureDialog` gated on `preferences.micDisclosed` before the first mic-permission flow
      (`MainActivity`) + `LicensesScreen` (correct license wording incl. Silero-STT exclusion). Remaining:
      the Play Console Permission Declaration form itself is external (Bucket C)._
- [~] FAR-budget threshold tuning per command. _calibration logic DONE & tested — `core:eval`
      `ThresholdCalibrator` (aggregate FA budget, equal split, per-command thresholds bounding false
      accepts) returns the `Map<CommandId, Float>` the matcher already accepts. **App persistence + pass-through
      LANDED 2026-07-05** — `ListeningPreferences.commandThresholds` (JSON pref via `CommandThresholdCodec`),
      `WakeGatedRecognizer.onFrame` forwards the map, `ListeningService` collects + passes it. Remaining `[~]`:
      the calibrated numbers themselves need a real labeled corpus (Bucket B)._
- [x] Multi-template re-enrollment polish + confirmation-gated adaptation. _decision logic + app wiring
      complete & tested — `decideAdaptation` (condition-aware pruning that never evicts a sole-condition
      example, DTW-redundancy selection, deterministic tiebreak) + the "remember this" UI
      (`TryViewModel.rememberThis()` → `decideAdaptation` → `TemplateRepository`); `make verify` green.
      The adaptation *benefit* (FRR reduction at fixed FAR on a voice-drift corpus) still needs real audio
      to quantify (Bucket B) — the mechanism is done, the measurement is external._
- [~] Optional Path-A intact-speech mode (Vosk grammar / sherpa-onnx KWS). _interface + scaffold DONE &
      tested — backend-neutral `SpeechBackend` + `BackendResult`/`BackendRejection`, `TemplateSpeechBackend`
      adapter, `NoopPathABackend`. A real Vosk/sherpa backend remains BLOCKED (large external model — Bucket C)._

---

## Phase 3 — Delight & reach (ongoing) · status: `active`

- [~] QbE embedding enhancement (few-shot). **↑ PROMOTED to Critical Path v2 / CP-1 — this is the core
      accuracy bet, no longer "delight."** _Bucket-A seam LANDED 2026-07-05 — `QbeEncoder`/`QbeSpeechBackend`
      (few-shot cosine prototypes) + `SpeechBackendSelector` + dormant `NoopQbeEncoder` DI binding; the
      template engine stays the default *for now*. Remaining: a real trained encoder + its FRR+FAR-vs-baseline
      measurement (Bucket C). **Scope under review (see the external-asset QbE note): the original
      "24k-param, milder-impairment, never-default, normal-speech" framing is likely too timid — but any
      replacement is **gated on preserving language-independence + 1-shot enrollment (CP-1's condition)**,
      so the lead candidate is a phoneme-supervised / few-shot encoder (ZP-KWS-class), with a pure-SSL
      front-end adopted only if it clears that gate.** `docs/plans/2026-06/phase3-matcher-enhancements.md`._
- [x] Vocabulary-distinctness helper (warn on acoustically-close commands). _`core:matching`
      `VocabularyDistinctness.analyze` (scale-relative DTW + shared-onset, advisory-only) + the
      enrollment-UI nudge wired into `TeachViewModel`/`TeachScreen`; unit-tested, `make verify` green
      (2026-07-05). On-device visual QA + confusion-correlation tuning on real voices are Bucket B.
      `docs/plans/2026-06/phase3-matcher-enhancements.md`._
- [~] Far-field / noise front-end. _logic LANDED 2026-07-05 — `MfccConfig.noiseReduction`
      (SPECTRAL_SUBTRACTION, default-off, byte-identical when off) + bake-off wiring. Remaining: the
      FRR+FAR gain vs baseline on real far-field/noise audio (Bucket B).
      `docs/plans/2026-06/phase3-matcher-enhancements.md`._
- [~] whisper.cpp batch dictation (optional). _interface LANDED 2026-07-05 — `DictationBackend`
      (transcript-returning, not `SpeechBackend`) + `NoopDictationBackend`; the text-entry **stub screen**
      LANDED 2026-07-06 — `app/src/main/kotlin/com/speechangel/app/ui/dictation/DictationScreen.kt` +
      `DictationViewModel`, routed from Home,
      off the command path. Remaining: the native model + runtime + real audio capture (Bucket C).
      `docs/plans/2026-06/phase3-reach-and-release.md`._
- [x] Shareable command packs. _`data/pack` `CommandPack` (versioned JSON), `DeviceAction`-validated
      import, definitions-only re-enroll model + `CommandPackScreen`/`CommandPackViewModel` (import/export)
      routed from Home; unit-tested, `make verify` green (2026-07-05). A polished share-sheet/SAF file
      picker + on-device visual QA are Bucket B. `docs/plans/2026-06/phase3-reach-and-release.md`._
- [~] F-Droid + Play release. _scaffold + R8 LANDED 2026-07-05 — conditional signing, release shrink
      (`:app:assembleRelease` green), `fastlane` + F-Droid metadata, `docs/release/RELEASE.md`. Remaining:
      the keystore, Play/F-Droid accounts + RFP (Bucket C). `docs/plans/2026-06/phase3-reach-and-release.md`._

---

## External-asset shortlist (unblocks the `[~]` Bucket-B/C items) · status: `planned`

> Added 2026-07-06 from a license-vetted internet sweep. The four remaining `[~]` items are each blocked
> on an **absent external asset, not on code** — the seams (`QbeEncoder`, `DictationBackend`,
> `SpeechBackend`/Path-A, `MfccConfig.noiseReduction`, `core:eval`) are built and dormant. This section
> pins concrete candidates so acquisition is a lookup, not a research task.
>
> **Carrying plan:** `docs/plans/2026-06/external-asset-acquisition.md` (self-scored 96, advisor-cleared
> 2026-07-06) — the acquisition/integration runbook for every row below: license tag + acquisition
> action + the dormant seam (`path:line`) each plugs into + the check that proves integration.

**License filter (non-negotiable §Licensing): permissive only — MIT / Apache-2.0 for code+models,
CC-BY-4.0 / CC0 for training data. NC-licensed *or unlicensed* models are never bundled.** Tags below:
**[bundleable]** = license permits shipping inside the AGPL-3.0 app · **[measure-only]** = usable
off-device to compute FRR/FAR or as a training-data source, never redistributed in the APK.

### QbE encoder — CP-1 (was `[~]` Phase 3 "QbE embedding enhancement")

> **Scope under strategic review (2026-07-06).** The original target profile below (~24k params, normal
> speech, *milder-impairment enhancement, never the default*) was set before the real numbers. The CP-1
> evidence argues for a **larger-but-still-small encoder trained/adapted toward dysarthric speech,
> evaluated as a candidate *default*, not a normal-speech-only side path** — but **gated on preserving
> language-independence + 1-shot enrollment (CP-1)**: the ~10% neural baselines win partly by solving an
> easier closed-vocab task, so that gap bounds the opportunity, not a settled target. The two candidate
> architectures to bake off: (a) the 24k on-device-learnable design below; (b) a ZP-KWS/PhonMatchNet-class
> **phoneme-supervised** encoder (~1.55M params, R-SOTA-1 — more language-agnostic than a pure-SSL front
> end). Decide by measured FRR+FAR on real dysarthric audio (CP-0), against the constraint gate, not by
> the pre-measurement spec. The two profiles below are
> retained as the *lower-bound* option, not the settled target.

Original target profile (`Qbe.kt`, `docs/plans/2026-06/phase3-matcher-enhancements.md`): ~24k params, <4 kB,
MFCC-fed, few-shot cosine prototypes, trained on *normal* speech (was framed as a milder-impairment
enhancement, never the default matcher — **now under review per the note above**).

- [ ] **Train the 24k encoder** — reimplement arXiv 2403.07802 ("Boosting keyword spotting through
      on-device learnable user speech characteristics"; ~23.7k params, 1 MFLOP/epoch, TinyML) against the
      existing `MfccExtractor` front-end. **[bundleable]** — a paper is architecture-only, no code-license
      entanglement.
- [ ] **Training data** — MSWC (Multilingual Spoken Word Corpus, 50 langs, ~6000 h) **CC-BY-4.0,
      commercial-OK** + Google Speech Commands v2 **CC-BY-4.0**. **[bundleable]** with attribution.
- [ ] **Research baseline only** — `harvard-edge/multilingual_kws` pretrained embedding (5-shot F1 ≈ 0.75).
      **Repo has NO LICENSE file ⇒ all-rights-reserved ⇒ [measure-only], never bundle.** Use it once to
      sanity-check the seam + bake-off, then ship the self-trained encoder.

### Dictation + Path-A models — `[~]` Phase 3 whisper.cpp · `[~]` Phase 2 Path-A

- [ ] **Dictation** — whisper.cpp (MIT) Android AAR + OpenAI `tiny`/`base` GGML weights (MIT), q5_1
      quantized, JNI, batch (not streaming). **[bundleable].** → `DictationBackend`.
- [ ] **Path-A word-list** — sherpa-onnx (Apache-2.0) keyword-spotter + its pretrained KWS models
      (Apache-2.0); Android KWS demo exists. Cleaner interface fit than Vosk grammar (no
      `templateId`/`distance` mismatch flagged as the Path-A #1 risk). **[bundleable].** → `SpeechBackend`.
- [ ] **Path-A fallback** — Vosk small models (Apache-2.0, ~40 MB, official Android demo). **[bundleable].**

### Dysarthric-inclusive corpora — the non-code items (unblocks far-field gain, thresholds, bake-off winner, real FRR/FAR)

`core:eval` (`Evaluator`/`ThresholdCalibrator`/`FrontEndBakeoff`) is built + tested; only real labeled
audio is missing. These are research corpora used **off-device to produce numbers — never shipped**, so
their research DUAs don't touch the app license; noted per-corpus regardless.

- [ ] **Speech Accessibility Project (SAP)** — UIUC. Largest (959 speakers, 5 etiologies, 400+ h, ~190k
      utterances) **with a "digital-assistant commands" category** → best fit for command FRR/FAR. Access:
      sign UIUC Data Use Agreement + application review (**start now — DUA lead time is the real cost**).
      **[measure-only]**; check the DUA's commercial clause.
- [ ] **UASpeech** — 16 dysarthric speakers, isolated words + intelligibility labels (VL/L/M/H) → the
      per-severity FRR table. Register with H. Kim, UIUC. **[measure-only].**
- [x] **TORGO** — 15 speakers, ~21 h, freely downloadable → immediate harness validation on real voices,
      kills the `SYNTHETIC` banner. **[measure-only]. DONE 2026-07-06** — in hand at `~/torgo`; first real
      FRR/FAR + the realistic-condition sim ran on it. SAP is now the gating long-lead corpus (CP-0).
- [ ] **EasyCall** — 55 speakers, 37 commands + 30 non-commands (mirrors the `truth=null` OOV/FAR split);
      Italian. Contact authors. **[measure-only].**
- [ ] **Voice-drift gap** — none of the above carry `VoiceCondition` (NORMAL/TIRED/ILL) labels; map severity
      → condition or collect a small in-house drift set to exercise the adaptation-benefit measurement.

### Far-field / noise augmentation — `[~]` Phase 3 far-field front-end

Real far-field *dysarthric* audio barely exists → synthesize the far-field/home-noise conditions the
harness expects by convolving the corpora above.

- [ ] **RIRs** — OpenSLR "RIR and Noise" (Apache-2.0). **[bundleable]**/measure.
- [ ] **Noise** — MUSAN (OpenSLR) for home-noise mixing. **[measure-only]** — verify the exact license
      before any redistribution.

**Acquisition ordering (revised 2026-07-06):** TORGO is **done** (in hand). The critical-path unblock is
now **(1) the SAP DUA — start immediately, it is the longest lead and gates CP-1/CP-2 trust; (2) the
self-trained / ZP-KWS-class encoder (obtainable within ~a day) → the first real MFCC-DTW-vs-learned-encoder
bake-off (CP-1); (3) EasyCall + UASpeech in parallel for the OOV split and per-severity table.**
whisper.cpp / sherpa-onnx (dictation / Path-A) are lower priority — off the CP-1/CP-2 path.

---

## Cross-cutting non-negotiables (carry into every phase)

- [x] Deterministic action layer — **never** an autonomous LLM agent. _held — `DeviceAction` fixed
      table; verified no LLM in the action path._
- [ ] Accuracy always reported as FRR + FAR/hour. _enforced for plans by
      `verify-plan-workflow-guardrails.mjs`; awaiting real measurement._
- [x] On-device enrollment stays the core — no regression to a language-dependent STT core. _held —
      recognizer is speaker-dependent template matching; no STT/phoneme model._
- [x] Licensing: keep Silero VAD/whisper.cpp (MIT), Vosk/sherpa-onnx (Apache-2.0); avoid NC-licensed
      models; ship a third-party-licenses screen. _held — `LicensesScreen` ships (AndroidX/Kotlin/Hilt
      Apache-2.0; planned models MIT/Apache only); no NC-licensed model is bundled; app is AGPL-3.0
      (`LICENSE`). The permissive-only policy is documented for any future model add. **Training data for
      any bundled model must be CC-BY-4.0/CC0 (approved: MSWC, Google Speech Commands v2); an unlicensed
      pretrained model (e.g. `multilingual_kws`) is measure-only, never bundled** — see the External-asset
      shortlist._

---

## Workflow / framework track (this port)

- [x] AI workflow + guardrail system transplanted (Wave 0/2/3 + Android guardrails). _status: done_
- [x] Install git hooks (`git config core.hooksPath .husky`) to make gates Enforced. _done 2026-06-28 —
      hooks active; pre-commit + pre-push run green._
- [x] Port worktree/plan tooling (Wave 1). _done — `docs/plans/TEMPLATE.md`, `scripts/ops/create-plan.mjs`,
      `scripts/audits/verify-plan-workflow-guardrails.mjs` (wired into the bundle)._
- [~] CI workflow running the guardrail + core-test subset. _present — `.github/workflows/ci.yml`
      (build-test + guardrails jobs); not yet observed green on a GitHub Actions run._

See `docs/meta/port-status.md` for the honest wave-by-wave status.
