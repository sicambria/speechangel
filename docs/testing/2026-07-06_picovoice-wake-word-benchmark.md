<!-- SpeechAngel on the Picovoice wake-word-benchmark. Standing test report; index in docs/DOC_TOC.md. -->
# SpeechAngel on the Picovoice wake-word-benchmark

Produced by `PicovoiceBenchmark` (`core:eval`) over the
[Picovoice wake-word-benchmark](https://github.com/Picovoice/wake-word-benchmark) data. This is the
project's **first head-to-head placement on a standard, public benchmark** — the gap the SOTA scorecard
named ("directional references… not head-to-head benchmarks on identical data").

> **Provenance:** generated 2026-07-06. Data provisioned by
> `scripts/eval/fetch-picovoice-benchmark.sh` (Picovoice repo keyword takes + LibriSpeech test-clean from
> OpenSLR + DEMAND 16 kHz from Zenodo — all **open downloads, no access key, no Kaggle**), transcoded to
> 16 kHz mono via `ffmpeg`. **Run it:** `make bench-picovoice-fetch` (once) then `make bench-picovoice` —
> the no-override target is pinned to the exact config below
> (`-Dpicovoice.bgSeconds=900 -Dpicovoice.enroll=10 -Dpicovoice.held=40` + ctor defaults), so it
> regenerates these numbers byte-for-byte. The dataset is `[measure-only]` (never committed); the harness
> (`PicovoiceCorpus`/`PicovoiceMixer`/`PicovoiceBenchmark`) is committed and `:core:eval:test` stays green
> with the corpus absent.

> **Sweep knobs (experimentation).** `make bench-picovoice` accepts env overrides mapped to `-D` props —
> `FRONTEND=` (`none`/`delta`), `DELTA=` (`NONE`/`DELTA`/`DELTA_DELTA`), `SNR=`, `WINDOW=`, `HOP=`,
> `TARGETFA=` (+ `BG=`/`ENROLL=`/`HELD=`). Every **unset** knob falls back to the ctor default that produced
> this report — the **pinned baseline**. Per **EVAL-003**, a swept variant is an exploratory, **NOT-banked**
> family: report it in full (losing cells included) but never adopt or headline a mined variant as an
> FRR/FAR win without its own fresh, pre-registered, FAR-matched confirmation.

## The one thing to understand first: decompose the benchmark by metric

The benchmark's two outputs have **opposite validity** for a speaker-dependent product, so we never
collapse them into a single "SpeechAngel X% vs engine Y%" headline:

- **False-alarm rate** (does random background speech false-fire an enrolled template?) is **in-regime and
  speaker-agnostic** — it does not depend on the background being the enroller's voice. This is the
  headline, and LibriSpeech+DEMAND is a larger, more diverse, *standard* background than the project's
  prior TORGO-OOV proxy.
- **Detection miss-rate** (cross-speaker) is **out-of-regime**: SpeechAngel is speaker-dependent /
  few-shot, the keyword takes are 50+ *other* speakers with no speaker labels, and the engines this
  benchmark was built for (Porcupine/PocketSphinx) are speaker-**in**dependent. So miss-rate is reported
  as an explicitly-labelled **lower bound**, never a vs-engine headline.

## Verdict — infrastructure works; discrimination is strong; always-on rejection is the wall

Config: shipped static front-end (`MFCC`, `deltaOrder=NONE`), 1500 ms window / 500 ms hop, DEMAND @
10 dB SNR; 6 keywords, **118.7 min** total stream (**1.98 h** background), 240 keyword occurrences;
10 enrolled takes/keyword, 40 held-out.

1. **Discrimination is genuinely strong.** Combined 6-keyword **clean closed-set rank-1 = 89.2%**
   (cross-speaker, chance = 16.7%). The MFCC-DTW matcher separates *which* keyword was said very well —
   consistent with, and above, the TORGO rank-1 figures (typical speech is easier than dysarthric).
2. **There is no viable always-on operating point.** On the continuous stream, to hold the benchmark's
   target **0.1 FA/hour you miss 87.5%** of keywords; the first threshold that detects a useful fraction
   (~62% detected) already false-fires at **~119 FA/hour**. At the *shipped* threshold (8.0) the
   cross-speaker distances (25–60) are so far above it that nothing fires at all — 0 FA/hour **and** 99.6%
   miss. This is the scorecard's always-on gap, now measured on a **standard, citable** stream.
3. **The in-regime FA machinery runs, and the shipped config is inert here.** At the shipped threshold
   both the swept curve and the deployed matcher (`AmbientFar.measure`) fire nothing — cross-speaker
   distances (25–60) sit far above it — so the shipped operating point detects nothing on this stream.
   (That is a consistency note at one inert threshold, **not** a full cross-check: the two paths use
   different accept rules — raw DTW vs the deployed margin-weighted match.) The honest finding stands:
   the shipped MFCC-DTW matcher has **no cross-speaker typical-speech operating point** that is
   simultaneously sensitive and quiet.

## Miss-rate vs FA/hour curve (single threshold axis)

| threshold | miss-rate | FA/hour | false accepts | detected/240 |
|---:|---:|---:|---:|---:|
| 8.00 (shipped) | 99.6% | 0.00 | 0 | 1 |
| 16.55 | 95.0% | 0.00 | 0 | 12 |
| 20.98 | 91.7% | 0.00 | 0 | 20 |
| 23.93 (0.1 FA/hr op-pt) | 87.5% | 0.00 | 0 | 30 |
| 25.41 | 80.8% | 2.02 | 4 | 46 |
| 29.84 | 37.9% | 119.25 | 236 | 149 |
| 34.27 | 5.4% | 1037.40 | 2053 | 227 |
| 43.13 | 0.0% | 1986.38 | 3931 | 240 |

_The curve is monotone (miss falls as the threshold loosens), which the harness asserts as a scoring-bug
sanity check. Full 40-point curve + per-keyword detail: `core/eval/build/picovoice-report.md`._

## Honesty bounds (all stated in the machine report)

- **Cross-speaker ⇒ lower bound.** Enrolling on 10 speakers and testing on others is a regime the
  speaker-dependent matcher is not built for; the real product enrolls *your* voice.
- **Typical-English keywords ⇒ typical-speech proxy.** The target population is atypical/dysarthric speech
  in any language — not measured here.
- **Clean read-speech ≠ deployment ambient.** LibriSpeech is clean dictation, not TV/babble; the real
  continuous-ambient measurement still routes through the `-Dambient.wav` seam.
- **Statistically marginal FA denominator.** 1.98 h ⇒ 0.1 FA/hr means ~0.2 expected false alarms; raise
  `-Dpicovoice.bgSeconds` for a tighter number (the finding — no quiet+sensitive point — is unaffected).

## Comparison anchor

- **Same-host, byte-identical:** `scripts/eval/run-pocketsphinx.sh` runs CMU PocketSphinx (open-source,
  no key) over the **identical** dumped `<keyword>_speech.wav` streams. Result:
  `~/picovoice-benchmark/pocketsphinx-anchor.md` — see below.
- **Published (directional):** Picovoice reports Porcupine ≈ near-0 miss @ 0.1 FA/hr on typical speech,
  with PocketSphinx dramatically higher; those are on their original mix (seed=778, peak-energy SNR), so
  they anchor the *bar*, not a head-to-head on our stream.

### Same-host PocketSphinx result (byte-identical streams, thr=1e-20 ≈ the 0.1 FA/hr convention)

| keyword | PocketSphinx miss | PocketSphinx FA/hr | note |
|---|---:|---:|---|
| alexa | 7.5% | 21.57 | |
| computer | 25.0% | 3.02 | |
| jarvis | 15.0% | 21.15 | |
| smart mirror | 37.5% | 0.00 | |
| snowboy | — | — | OOV: not in the English dictionary (errored, reported honestly) |
| view glass | 7.5% | 6.03 | |

**How to read this (crucial):** PocketSphinx is a **speaker-independent English ASR** — the *right tool*
for detecting English keywords from anyone. It detects far better (7–37% miss vs SpeechAngel's 87.5% miss
at the 0.1 FA/hr point) — but at **much higher FA/hr** (3–22, except one), i.e. it is *not* quiet enough
for always-on either, and it **cannot handle** the OOV coinage `snowboy`. This is exactly the
apples-to-oranges the regime note warns about: SpeechAngel is speaker-dependent and language-independent
(no dictionary), so this stream is out-of-tool for it; the contrast quantifies the *cost of the wrong
regime*, not a quality verdict. (PocketSphinx was run once per keyword at a single threshold — a point,
not a curve; SpeechAngel's report owns the curve.)


## What this changes

- **Scorecard factor 4 (robustness & always-on):** the first FA/hour measurement on a **standard** stream,
  not the bespoke TORGO-OOV proxy — a real maturity gain, though the gap it quantifies is large.
- **Direction confirmed:** discrimination (rank-1) is not the bottleneck; **rejection / always-on gating**
  is. This is exactly the scorecard's Part-A ordering (wake cascade + learned embeddings before threshold
  tweaks).
