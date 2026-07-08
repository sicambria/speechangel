<!-- Concrete requirements/acquisition spec backing Critical Path v2 (CP-0..CP-3). Index in docs/DOC_TOC.md. -->
# SpeechAngel — CP-0..CP-3 Requirements & Acquisition Spec

**Date:** 2026-07-06 · Backs `docs/ROADMAP.md` "Critical path v2". Companion to the scorecard and the
authoritative SOTA reference (`docs/product/2026-07-08_sota-wake-word-reference.md`).

This lists **exactly what is needed** to execute the four critical-path bets — with concrete quantities,
audio formats, model parameters, target ranges, and **error margins**. Where a precise value does not yet
exist, it is marked **`UNKNOWN — needs measurement`** with the reason, never guessed. Two label tags:
**[verified]** = confirmed this session (repo/paper/web); **[approx — verify]** = from memory/summary,
confirm before acting.

**Governing statistical facts** (drive every "how much" below):
- A proportion (FRR/FAR) at count *n* has 95% CI ≈ ±1.96·√(p(1−p)/n). At our real *n*: dysarthric FRR
  75.7% (n=267) → **±5.1 pp**; control FRR 61.9% (n=740) → **±3.5 pp**; a single small-vocab speaker
  (n≈32) → **±13.5 pp** (why per-speaker numbers are untrustworthy and ≥10 speakers are required).
- A per-hour false-accept rate follows Poisson. **Rule of three:** 0 false accepts in *T* hours ⇒ 95%
  upper bound ≈ 3/T FA/hr. So bounding **≤0.5 FA/hr needs ≥6 h** zero-event audio; **≤0.1 FA/hr needs
  ≥30 h**. *Characterizing* a non-zero rate to ±20% **(1 SE, ≈±40% at 95%)** needs ~25 events (~50 h at
  0.5/h); to ±10% (1 SE) ~100 events (~200 h).
- A paired FRR improvement (McNemar) needs enough **discordant** trials: to detect a ~10 pp shift at 80%
  power / α=0.05, budget **≥300 in-vocab positive trials per arm** (expect ≥40 discordant; our committed
  control test had 182 discordant at n=740, so ~300–800 positives is the working range).

---

## CP-0 — Real data (the prerequisite; everything else is unfalsifiable without it)

### Audio format contract (all corpora + recordings must meet or be resampled to this)

| Parameter | Requirement | Basis |
|---|---|---|
| Sample rate | **16 kHz** (resample down if source is 44.1/48 k; never up-sample) | pipeline `MfccConfig` 16 kHz [verified] |
| Channels | **mono**; if multi-mic array, take the close-talk or a single fixed channel | recognizer is single-stream |
| Bit depth / encoding | 16-bit signed PCM WAV (lossless); no MP3/Opus for measurement audio | avoids codec artifacts in FRR |
| Per-utterance length | isolated command words ≈ **0.8–2.0 s** (our enrollment window `RECORD_MS=1500`) | `TeachViewModel` [verified] |
| Labels required | speaker id · command/word label · **is-wake-command vs OOV/non-command** flag (for FAR) · severity/intelligibility if available | FRR needs positives, FAR needs labeled OOV |

### Corpora — what each is, what it unblocks, how to get it

| Corpus | Content (speakers / units / hours) | Format notes | License / access | Lead time | Unblocks |
|---|---|---|---|---|---|
| **TORGO** ✅ in hand | ~8 dysarthric + 7 control; F01/F03/F04 + FC01/FC02/FC03 used; ~21 h [verified] | head + array mic, 16 kHz | free download, [measure-only] | **done** | CP-1 pilot, sim harness |
| **SAP (Speech Accessibility Project)** — the gating asset | ~500–959 speakers, 5 etiologies, **400+ h, ~190k utterances**, has a **"digital-assistant commands"** category [approx — verify exact release counts] | curated, per-utterance labels | UIUC **DUA + application review**; check commercial clause | **weeks–months (DUA is the real cost) — start now** | CP-1 + CP-2 trust; the only command-fit dysarthric corpus |
| **UASpeech** | ~15 dysarthric (+13 control), **765 isolated words/speaker**, intelligibility **VL/L/M/H** [approx — verify] | 7-mic array, 16 kHz | register w/ UIUC (H. Kim), [measure-only] | weeks | per-severity FRR table |
| **EasyCall** | 55 speakers, **37 commands + 30 non-commands**, Italian [approx — verify] | — | contact authors, [measure-only] | weeks | built-in OOV/FAR split; cross-language check |
| **Common Voice** | multilingual, CC0 [verified: CC0] | 16 kHz after resample | CC0 download | days | **language-independence** eval (Howl used it) |

### Minimum viable dataset to *run* CP-1/CP-2 (not the full corpora)

- **CP-1 accuracy bet:** ≥**10 speakers** (mixed severity) × ≥**15 command words** × ≥**5 reps/word**,
  **plus ≥30 OOV/non-command utterances per speaker** for FAR. Rationale: 10 speakers pools to pooled-FRR
  ±~3 pp; <10 leaves per-speaker ±13 pp noise (above). ~**1,500 positive + ~300 OOV trials** ⇒ clears the
  ≥300-positives McNemar budget.
- **CP-2 ambient:** see CP-2 below — corpora do **not** supply this; it needs continuous recordings.

---

## CP-1 — Learned encoder (the accuracy bet)

**Gate (non-negotiable):** any candidate must preserve **language-independence + 1-shot arbitrary-word
enrollment**. An option that erodes those is disqualified regardless of FRR (ROADMAP CP-1).

### Candidate architectures to bake off

| Candidate | Params | Size on device | Front-end | Training data | Language-indep? | Source |
|---|---|---|---|---|---|---|
| (a) On-device-learnable KWS | ~**23.7k** | <4 kB [verified target] | MFCC (existing) | MSWC (50 lang, ~6000 h, CC-BY-4.0) + GSC v2 (~105k utt, CC-BY-4.0) | yes (MFCC) | arXiv 2403.07802 |
| (b) ZP-KWS / PhonMatchNet-class | ~**1.55M** (0.9M spk enc.) | ~1.5 MB int8 / ~6 MB fp32 [approx — verify quantized size] | phoneme-supervised encoder | LibriPhrase / GSC / Qualcomm | **partial** — phoneme-supervised is language-agnostic-ish; verify no hard language dependency | arXiv 2606.20106 |
| baseline | MFCC-DTW (current) | templates only, <100 kB | MFCC static | user's 1-shot enrollment | yes | shipped |

### Success criterion (what "the bet paid off" means, concretely)

- **A statistically-significant FRR reduction at matched, held-out FAR** on real dysarthric audio (CP-0
  corpus), at the **product operating point ≤5% FAR/utterance**, McNemar p<0.05 vs MFCC-DTW baseline,
  **and** rank-1 not worse — measured under the ≥300-positive / ≥40-discordant budget above. Report as
  **FRR + FAR delta** (EVAL-002), never a bare %.
- **Target magnitude:** close a meaningful fraction of the gap the constraint-matched SOTA implies —
  ZP-KWS cuts **FRR@1%FAR by ~60% relative** (its absolute ~29–33% is quoted **at 1% FAR**, a *stricter*
  point than our 76% @ ~5% FAR, so the two are directional, **not** matched — the true headroom at our
  operating point is if anything larger). **Not** a target of 10% — that anchor is a closed-vocab task
  (opportunity bound, not a goal).
- **On-device budget the encoder must fit:** model ≤ **~2 MB** (Porcupine <1 MB is the SOTA reference);
  added per-frame inference latency `UNKNOWN — needs on-device benchmark` (target < 10 ms/frame so Stage-2
  stays real-time; confirm on CP-3 hardware).

---

## CP-2 — Stage-1 wake cascade + ambient measurement (the deployability bet)

### The ambient recording SpeechAngel does **not** have and must acquire/record

| Parameter | Requirement | Basis / error margin |
|---|---|---|
| Content | **continuous** real household audio: TV/dialogue, conversation, kitchen/appliance noise, music, silence — **not** concatenated isolated words (the current proxy is optimistically biased) | proxy caveat in sim report [verified] |
| Duration | **≥6 h** to *bound* ≤0.5 FA/hr at zero events (rule of three); **≥30 h** to bound ≤0.1 FA/hr; **~50–200 h** to characterize the true rate to ±20%/±10% | Poisson (above) |
| Environments | ≥3 distinct rooms/scenarios; include a **TV-on** block (the classic false-fire source) | representativeness |
| Format | 16 kHz mono 16-bit WAV (the format contract); drop-in via built `-Dambient.wav` seam | pipeline [verified] |
| Labels | timestamps of any *genuine* wake utterances (to separate true accepts from false) | FA/hr needs a clean negative stream |

### Wake-stage requirements

| Parameter | Requirement | Basis |
|---|---|---|
| **FA/hr target (wake stage alone)** | **≤ 0.5 FA/hr** (MVP, openWakeWord) → **≤ 0.1 FA/hr** (stretch, Porcupine) | competitive bar [verified targets] |
| **FRR at that FAR** | **< 5%** wake-miss (openWakeWord design target); production-real **~10% @ 4 FA/hr** (Howl) acceptable interim | competitive bar |
| Adopted option | **enrolled-DTW / personalized wake template** (`WakeWordGate`, built) — constraint-preserving; openWakeWord is a **benchmark yardstick**, not necessarily the shipped gate (its language-indep = 30) | ROADMAP CP-2 |
| Latency (wake decision) | `UNKNOWN — needs on-device`; target **< 200 ms** from end-of-utterance | SOTA wake detectors are ~real-time |
| Window geometry (current) | `WINDOW_MS=1500`, `WAKE_WINDOW_MS=750`, sliding; debounced | `ListeningService` [verified] |

---

## CP-3 — Real-device metrics (the alpha gate) — all currently `UNKNOWN`

The emulator's silent mic makes every number below unmeasured. Each needs a **physical device** (or a
debug `AudioRecorder` WAV-injection binding). Targets are ranges to *aim at*, with the SOTA reference.

| Metric | Target range | SOTA reference | Current status |
|---|---|---|---|
| End-to-end latency (speech → action) | **< 500 ms** perceived; wake < 200 ms | commercial KWS ~real-time | `UNKNOWN — needs device` |
| DTW cost per command match | benchmark; O(n·m·band), band ratio 0.1 [verified code] | — | `UNKNOWN — never benchmarked` |
| Always-on CPU (Stage-0/1 idle listening) | **< ~3–5%** of one core sustained | tiny KWS models negligible | `UNKNOWN — needs device` |
| Battery drain (always-on listening) | **< ~3–5%/hour** additional | no published budget in repo | `UNKNOWN — needs device + real battery` |
| Peak RAM | **< ~150 MB** (low-end phone headroom) | — | `UNKNOWN` |
| APK size | debug **21.4 MB** [verified]; release `UNKNOWN` (R8 shrinks) | Porcupine runtime <1 MB | release-APK size unmeasured |
| Always-on survival | OEM task-kill (Xiaomi/Huawei/Oppo/Vivo/Samsung) + multi-hour soak | — | `UNKNOWN — physical-device only` |

---

## The honest "unknown" register (what precise data does **not** exist yet)

1. **Real-device latency / CPU / battery / RAM / real false-fire rate** — all CP-3, need hardware.
2. **DTW per-match wall-clock** — never benchmarked even off-device.
3. **Real continuous-ambient FA/hr** — only the ~82 FA/hr *proxy* exists (optimistically biased); needs a
   real ≥6 h recording.
4. **Encoder-vs-DTW FRR delta on dysarthric** — the entire CP-1 result; needs CP-0 data + a trained encoder.
5. **Quantized on-device size/latency of the ZP-KWS-class encoder** — estimated ~1.5 MB int8, unconfirmed.
6. **Exact current-release SAP/UASpeech/EasyCall counts** — cited [approx — verify] from summaries; confirm
   against the corpus release notes before quoting in any result.
7. **Per-severity FRR** (VL/L/M/H) — needs UASpeech; the current numbers pool severities.

**Acquisition-order to make the unknowns knowable:** SAP DUA (start now, long lead) ∥ record ≥6 h ambient
(cheap, unblocks CP-2 bound) ∥ train candidate (a) 24k encoder on MSWC+GSC (days) → first CP-1 bake-off on
TORGO while SAP lands → CP-3 device run with a WAV-injection binding.
