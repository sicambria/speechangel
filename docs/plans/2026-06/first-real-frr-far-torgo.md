# Plan: first real FRR/FAR from TORGO → one on-device run → always-on soak

- **Date:** 2026-07-06
- **Phase:** 0 → 1 → 2 (the 2026-07-06 product-scorecard critical path, in order)
- **Roadmap item:** `docs/ROADMAP.md` "⭐ Critical path" items 1–3 — first real FRR/FAR (TORGO),
  one end-to-end on-device run, minimal always-on survival soak.
- **Status:** done (D1–D3 implemented 2026-07-06; D1 real FRR/FAR produced — `SYNTHETIC` gone, rank-1
  55.4% dysarthric / 74.6% control; D2 on-device e2e + D3 Doze/reboot soak at the emulator ceiling,
  physical-device metrics documented as such)
- **Worktree:** `frr-far-torgo` (off `main`; substantive non-docs code lands here per AGENTS.md)
- **Plan quality:** 96/100 — self-scored 2026-07-06 (breakdown in `docs/plans/INDEX.md` scoring row)

## Goal

Retire the single gating risk on the product (accuracy **unmeasured on real/dysarthric voices**;
app **never run end to end**) with three real artifacts, in priority order:

1. **A real, non-`SYNTHETIC` FRR + false-accept report** produced by running the built `core:eval`
   harness over the **TORGO** dysarthric-speech corpus, **speaker-dependent** (enroll and test within
   each speaker — the product's actual "teach it *your* voice" deployment condition).
2. **One emulated end-to-end run** of the `ListeningService → WakeGatedRecognizer →
   CommandActionBus → SpeechAngelAccessibilityService` loop on the `changemappers-test` AVD.
3. **A minimal always-on survival soak** (Doze + reboot) on that emulator, with the OEM-task-kill
   boundary documented as physical-device-only.

Deliverable 1 is a **go/no-go gate** (the roadmap's own words: it "tells you whether the rest of the
roadmap is even worth executing"). A catastrophic FRR is still a *successful* outcome — the
existential hypothesis gets a real answer — and it reshapes 2–3.

## Context & Constraints

- **Host capability (probed 2026-07-06 — the facts that make the Bucket-B acquisition executable):**
  - `curl -sSI http://www.cs.toronto.edu/~complingweb/data/TORGO/F.tar.bz2` → `200 OK`,
    `Content-Length: 1139746435` (1.14 GB, dysarthric female). Sibling archives 200 OK too:
    `FC.tar.bz2` 2.53 GB (control F), `M.tar.bz2` 2.51 GB (dysarthric M), `MC.tar.bz2` 3.40 GB
    (control M). TORGO is direct-download, **no DUA** — it is `[measure-only]` (used off-device to
    compute FRR/FAR; never bundled in the AGPL-3.0 APK).
  - `emulator -list-avds` → `changemappers-test` (Pixel 6, API 35) is present (CLAUDE.md §3).
  - The roadmap correctly triaged this item as Bucket B (needs real audio, then a device); this plan
    executes that acquisition now that the corpus is fetchable and the AVD is available here.
- **Accuracy honesty (non-negotiable — `research/04_build_and_reuse_plan.md:108`).** The result is
  reported as **FRR + false-accept count** (and FAR/hour only where the negative-audio duration makes
  it meaningful — the renderer already caveats this, `EvalReport.kt:46`). Never a bare percentage.
  The exact command-selection and enroll/test-split rules are documented **in the report itself**, or
  the number is meaningless.
- **Speaker-dependent is load-bearing, not a convenience.** SpeechAngel is a per-user template
  matcher (`Recognizer`, `core:enrollment`): each user enrolls their own voice. The eval **must**
  enroll and test within one speaker. Cross-speaker enrollment would produce a catastrophic FRR that
  is a false negative on the whole hypothesis — worse than no number.
- **The harness already exists — this plan wires *real audio* into it, it does not re-architect it.**
  `core:eval` operates on `Corpus` of raw `AudioSamples` (`Corpus.kt:31`,
  `core/model/.../Domain.kt:12`); `Evaluator.evaluate` (`Evaluator.kt:91`) enrolls → distance-table →
  `EvalReport.from` (`EvalReport.kt:60`). The only missing pieces are a WAV→`AudioSamples` loader, a
  TORGO→`Corpus` builder, and a `synthetic=false` path (`EvalReport.kt:27`, banner `:35`).
- **`core:eval` stays green without the corpus.** TORGO is `[measure-only]` and multi-GB — it is
  **never committed** (gitignored + lives outside the working tree) and the real-corpus run is gated
  on a system property so `:core:eval:test` passes on any host with the corpus absent.
- **Deterministic action layer untouched.** No change to `SpeechAngelAccessibilityService`, the
  `DeviceAction` table, or the on-device/no-cloud invariants. D1 is pure JVM measurement; D2/D3 only
  run the *existing* app.
- **Emulator ≠ physical device (honesty on D2/D3).** Injecting real audio into the emulator's
  `AudioRecord` is not turnkey; the honest D2 deliverable is build+install+launch + drive the
  enrollment UI + fire the loop from a **debug file-audio source**, not a claim of mic-real e2e. For
  D3, Doze (`dumpsys deviceidle force-idle`) and reboot survival **are** emulable; per-OEM task-kill
  is **not** — that boundary is stated, not papered over.

## Approach

**Three staged deliverables, D1 shipped and committed independently as the gate.** D1 is the whole
point; D2/D3 build on a green D1 and carry explicit emulator-ceiling caveats. Modules touched: only
`core:eval` gets new code (`WavFile`, `TorgoCorpus`, a real-run entry point, a `synthetic` flag);
`docs/testing/` gets the produced report; no app/service code changes.

**Loader built against the *real* layout, not from memory (de-risks the day).** I cannot verify
TORGO's 2026 on-disk layout, prompt-file format, or speaker IDs without looking. Sequence:
HEAD-confirmed archives (done) → pull **F.tar.bz2** (smallest, dysarthric) + one control speaker from
**FC** → inspect the actual `Session*/wav_headMic` + `prompts` structure → *then* write `TorgoCorpus`
against what is physically there. A loader hardcoded to a remembered layout is the top day-burner.

**Validate the pipeline on one speaker before trusting any aggregate.** `EnergyVad` +
`minSpeechFrames = 8` (`Evaluator.kt:41`) were tuned on synthetic silence-padded tones. Real
dysarthric speech (long pauses, breathy low-energy onsets) can be mis-endpointed → a garbage FRR that
is a *trimming* artifact, not the matcher. First implementation step after the loader: dump
`enrollmentFailures` and VAD-trimmed lengths for one speaker; if failures are high or trims near-empty,
fix endpointing (raise silence tolerance / lower `minSpeechFrames`) before believing a number. Use
**head-mic** for the first number (cleanest — "does the hypothesis hold at all"); array-mic is a later
far-field condition, not the headline.

**Vocabulary & negatives — where the number's honesty lives.** TORGO prompts are heterogeneous
(single words, sentences, non-word stimuli); most sentences occur once. Selection rule (documented in
the report): **commands = prompts that repeat enough within a speaker** (the repeated
word-intelligibility items, not one-off sentences); **all other of that speaker's utterances → OOV
negatives** (`truth = null`, which the matcher already rejects on, `Evaluator.kt` negatives path /
`EvalReport.kt:91`). The enroll/test split is chosen from the *measured* per-speaker repetition depth
(step 1): a fixed 2-enroll/2-test split when words are plentiful, else leave-one-out / k-fold within
speaker. Where a word spans multiple TORGO sessions, enroll and test are drawn from **different
sessions** (matches the enroll-once-use-later product reality; same-session splits bias FRR
optimistically). Because negative audio may be modest, the headline is the **false-accept count**;
FAR/hour is reported with its duration caveat, not leaned on — and it is an OOV-utterance false-accept
count, **not** the always-on ambient FAR/hour of the Phase-0 exit budget (see DoD).

**Rejected approaches.** (1) Cross-speaker enrollment — wrong deployment model, manufactures a
false-negative FRR. (2) Committing TORGO or a trimmed WAV subset — `[measure-only]` license + repo
bloat; gitignore + sys-prop gate instead. (3) Blocking the D1 commit on D2/D3 emulator uncertainty —
the real number is the highest-value artifact and ships on its own. (4) Claiming mic-real e2e on the
emulator — dishonest; the debug file-audio source is the truthful D2. (5) Adding a WAV/DSP dependency
— a 16-bit-PCM reader is ~40 lines, keeping `core:eval` dependency-free (CLAUDE.md §5).

## Steps

### D1 — first real FRR/FAR (the gate)

1. **Acquire + inspect one speaker, and gate the split design on the real repetition counts.**
   Download `F.tar.bz2` (1.14 GB) and one control archive to a scratch dir **outside the repo**
   (e.g. `~/torgo/`); extract; `find` one speaker's tree. **Check (a) — layout:** the real
   `Session*/wav_headMic/*.wav` + `prompts/*.txt` (or actual equivalent) paths are listed and a
   sample WAV header confirms 16 kHz mono 16-bit PCM. **Check (b) — the load-bearing count:** for that
   speaker, count how many distinct prompts have **≥4 utterances** (the minimum for a 2-enroll + 2-test
   split). This is the make-or-break unknown — TORGO is heterogeneous (non-words, one-off sentences, a
   repeated word list) and the per-speaker repetition depth is not knowable without looking. **Decide
   the split design here, before writing `TorgoCorpus`:** if ≥5 prompts clear ≥4 reps per speaker, use
   the fixed 2-enroll/2-test split; **if fewer, switch to leave-one-out / k-fold within speaker**
   (uses every repetition of every word that appears ≥2×, standard for thin speaker-dependent samples)
   so D1 does not dead-end on a near-empty vocabulary after a 1.14 GB download. Add `**/torgo/**` and
   `*.tar.bz2` to `.gitignore`. **Deliverable:** the confirmed layout + the chosen split design (with
   the actual counts) recorded in the report's Methodology.
2. **WAV loader.** New `core/eval/src/main/kotlin/com/speechangel/core/eval/WavFile.kt` — parse a
   canonical PCM WAV (fmt + data chunks, 16-bit mono, arbitrary sample rate) → `AudioSamples`
   (FloatArray normalized to [-1,1], `Domain.kt:12`); throw a clear error on unsupported formats. New
   `WavFileTest` round-trips a byte-built WAV (no corpus needed). **Check:** `:core:eval:test` green.
3. **TORGO corpus builder.** New `core/eval/src/main/kotlin/com/speechangel/core/eval/TorgoCorpus.kt`
   — walk a TORGO root, group by speaker, parse prompts, apply the vocabulary/negatives rule above,
   emit a **per-speaker** `Corpus` (enroll + test within-speaker) plus a `Map<speaker, severity>`
   (dysarthric F/M vs control FC/MC; TORGO intelligibility label where available). Pure, deterministic
   (no clock/RNG). **Check:** a `TorgoCorpusTest` over a tiny hand-built fixture dir (a few synthetic
   WAVs written to a temp dir) verifies the split + OOV rule without the real corpus.
4. **`synthetic=false` path (kill the banner on real runs).** Thread a `synthetic` flag through
   `EvalReport.from` (`EvalReport.kt:60`) and `Evaluator.evaluate` (`Evaluator.kt:91`, default `true`
   so nothing else changes). Update `EvalTest` to assert the banner **is present** on synthetic runs
   and **absent** on a `synthetic=false` report. **Check:** `:core:eval:test` green.
5. **Real-run entry point, gated.** New `TorgoEvalTest` (or a `main` runner) that reads
   `-Dtorgo.dir=<path>`, and when **unset** calls JUnit `Assume.assumeTrue(...)` to **skip** (keeps
   `:core:eval:test` green with no corpus). When set: build per-speaker corpora, run `Evaluator`
   (head-mic, static + Δ+ΔΔ front-ends), aggregate, and **write the report** to
   `docs/testing/2026-07-06_frr-far-torgo.md` with `synthetic=false`. **Check:** with `-Dtorgo.dir`
   pointing at the extracted corpus, the test runs and the file is produced.
6. **One-speaker VAD sanity pass (before trusting the aggregate).** Run D1 on a single dysarthric
   speaker; inspect `enrollmentFailures` + trimmed lengths. If the VAD is eating real speech, tune
   endpointing and re-run. **Check:** enrollment-failure rate is plausible (not ~everything) and
   trims retain speech; recorded in the report.
7. **Produce the headline number + go/no-go.** Run over the acquired dysarthric speakers (+ controls
   as a sanity contrast). **Check:** `docs/testing/2026-07-06_frr-far-torgo.md` contains a real
   per-command + per-speaker + dysarthric-vs-control **FRR + false-accept count** table, the exact
   methodology (speaker-dependent, vocabulary rule, head-mic, front-end), and a one-line go/no-go
   verdict on the core hypothesis. `SYNTHETIC` banner absent. The report **states explicitly** that
   this measures FRR (+ OOV-utterance rejection), and does **not** measure the Phase-0 exit's always-on
   ambient FAR/hour budget (≤0.5 false accepts/hr on continuous audio) — TORGO has no continuous
   ambient stream, so that clause stays unmeasured here.

### D2 — one emulated end-to-end run

8. **Boot + install + launch.** `make emulator`; `make build`; `adb install -r`; `am start` the
   `MainActivity` (CLAUDE.md §3). **Check:** app launches; logcat clean of fatal exceptions.
9. **Drive the loop.** Enroll a command via the Teach UI, enable Always-on, and validate the service
   wiring is live (no fatal logcat). Then — **optional, debug-only** — add a debug DI binding that
   feeds a WAV through the existing `AudioRecorder` interface (`data/.../AudioRecorder.kt:18`; no
   change to `ListeningService` or any release code) so the full `ListeningService →
   WakeGatedRecognizer → CommandActionBus → SpeechAngelAccessibilityService` chain fires one
   deterministic action. **Check:** logcat shows the match → bus event → the AccessibilityService
   acting; capture the trace + a screenshot into `docs/testing/2026-07-06_on-device-e2e.md`,
   **explicitly noting** the audio source was a debug file feed, not the emulator mic, and that
   real-audio latency/false-fire/CPU (roadmap item 2) remain physical-device-only.

### D3 — minimal always-on survival soak

10. **Doze + reboot.** With Always-on enabled: `adb shell dumpsys deviceidle force-idle`, verify the
    foreground `microphone` service survives; `adb reboot`, verify `BootReceiver` posts the legal
    tap-to-resume notification (a `microphone` FGS legally cannot auto-start from `BOOT_COMPLETED` on
    SDK 35 — that is by design, `BootReceiver`). **Check:** results recorded in
    `docs/testing/2026-07-06_always-on-soak.md`; the **OEM-task-kill** case documented as
    **physical-device-only** (not emulable), not silently omitted.

### Close-out

11. **Reconcile ROADMAP + INDEX with the *real* numbers** (only the checkboxes the artifacts
    actually earn), run `make guardrails` green, commit in logical chunks (CLAUDE.md §8), and — if any
    step cost >~5 min to a wrong assumption (e.g. a VAD-endpointing surprise) — write the incident doc
    under `docs/errors/2026-07/`.

## Definition of Done

- **D1 (autonomous, the gate):** `docs/testing/2026-07-06_frr-far-torgo.md` exists with a **real,
  non-`SYNTHETIC`** speaker-dependent **FRR + false-accept count** table over ≥3 TORGO dysarthric
  speakers, per command and per speaker (+ a control contrast), stating the exact methodology
  (speaker-dependent split, vocabulary/OOV rule, head-mic, front-end config). `:core:eval:test` is
  green **with the corpus absent** (sys-prop gate) and produces the report **with it present**. The
  `EvalReport` `SYNTHETIC` banner is provably gone on the real run (`EvalReport.kt:35`). A one-line
  go/no-go verdict on the MFCC-DTW hypothesis is recorded. *No number is fabricated — whatever TORGO
  yields is reported, good or bad.* **Scope of the flip:** the Phase-0 exit has two clauses — (i) FRR
  measured on a real command set, (ii) beats the ≤0.5-false-accepts/hr always-on FAR budget. D1
  satisfies **(i) plus OOV-utterance rejection** and leaves **(ii) explicitly unmet** (TORGO has no
  continuous ambient audio). Only the FRR half of the roadmap checkbox flips.
- **D2 (emulator, honest ceiling):** primary deliverable —
  `docs/testing/2026-07-06_on-device-e2e.md` shows the app built, installed, and launched on
  `changemappers-test`, the Teach→enroll→Always-on UI driven, and the service wiring validated (no
  fatal logcat). *Real audio → action fire:* an **optional debug-only DI binding** (swapping
  `AndroidAudioRecorder` behind the existing `AudioRecorder` interface, `data/.../AudioRecorder.kt:18`
  — new **debug-only** code, off the release path) feeds a WAV so the full
  `ListeningService → WakeGatedRecognizer → CommandActionBus → SpeechAngelAccessibilityService` loop
  fires one deterministic action, with logcat + screenshot, **explicitly labeled** a debug file feed,
  not the emulator mic. **The Phase-1 exit line does NOT flip on this** — roadmap item 2's real-audio
  metrics (latency, false-fire rate, CPU) need a physical device; the emulator run validates wiring,
  which is recorded as such.
- **D3 (emulator, bounded):** `docs/testing/2026-07-06_always-on-soak.md` records Doze + reboot
  survival on the emulator and documents OEM-task-kill as physical-device-only.
- **Repo hygiene:** TORGO never committed; `.gitignore` covers it; `make guardrails` green; ROADMAP
  checkboxes flipped **only** for what the artifacts earn — D1 flips the **FRR half** of the Phase-0
  "Measure FRR/FAR" line (the always-on FAR budget stays open); D2/D3 are recorded as emulator
  wiring/soak notes against the Phase-1/2 exit lines **without** flipping them (real-audio metrics +
  OEM-kill remain physical-device-only).

## Risks & Mitigations

- **TORGO download slow/interrupted (multi-GB).** Mitigation: start with `F.tar.bz2` (1.14 GB, the
  smallest, and dysarthric — the point of the exercise); `curl -C -` resumable; controls are optional
  contrast, not required for the headline. Rollback: none needed — download is to a scratch dir
  outside the repo.
- **Real-layout mismatch vs a remembered one.** Mitigation: step 1 inspects the physical tree before
  step 3 writes the loader; the loader is written against `find` output, not recall.
- **VAD eats real dysarthric speech → FRR is a trimming artifact.** Mitigation: step 6 is a mandatory
  one-speaker sanity pass on `enrollmentFailures` + trim lengths before any aggregate is trusted;
  head-mic first to minimize confounds.
- **FAR/hour looks impressive/terrible off a tiny negative set.** Mitigation: headline is the
  false-accept **count** with negative-audio duration; FAR/hour carries the renderer's existing caveat
  (`EvalReport.kt:46`); the report states the negative-set size.
- **`[measure-only]` corpus accidentally committed.** Mitigation: `.gitignore` (`**/torgo/**`,
  `*.tar.bz2`) added in step 1; corpus lives outside the working tree; a pre-commit `git status` check.
- **Emulator can't do mic-real audio / OEM-kill.** Mitigation: D2 uses a debug file-audio source and
  says so; D3 documents the OEM-kill boundary — neither is claimed as done beyond what the emulator
  can show.
- **Rollback (overall):** all new code is additive and confined to `core:eval` (a JVM library off the
  runtime path) + docs; reverting the worktree restores today's state. The corpus touches no shipped
  code (measurement-only).

## Test & Verification

- **Autonomous on this host:** `:core:eval:test` green **without** the corpus (sys-prop skip) — the
  new `WavFileTest`, `TorgoCorpusTest`, and updated `EvalTest` (synthetic-banner assertions) all run on
  synthetic/fixture data. With `-Dtorgo.dir=<extracted>` set, the same task produces the real report.
  `make static` + `make guardrails` (`scripts/audits/run-all.mjs`) green. `:app:assembleDebug` green
  for the D2 install.
- **Emulator (D2/D3):** `make emulator` + `adb` drive the run and the soak; artifacts are the logcat
  traces, screenshots, and the three `docs/testing/2026-07-06_*.md` reports.
- **Honestly host-limited:** mic-real audio injection and per-OEM task-kill need a physical device;
  both are documented as such in the D2/D3 reports rather than claimed. The **real FRR/FAR (D1) is
  fully obtainable on this host** and is the deliverable the whole critical path gates on.
