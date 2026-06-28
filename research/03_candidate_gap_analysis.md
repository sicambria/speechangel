# Candidate gap analysis — top solutions vs the four hard requirements

**Date:** 2026-06-28
**The four hard requirements** (from the brief):
1. **On-device** (offline, private, reliable for always-on).
2. **User-trainable, language-independent matching** (record a few of *your own* samples; works for stroke/illness-damaged speech; re-trainable as the voice drifts).
3. **Always-on, fully hands-free** (24/7, survives reboot/OEM-kill, drives the device without touch).
4. **State-of-the-art, 10-year-old-easy UX.**

---

## A. The headline gap

**No single OSS Android app meets all four. Every existing app drops at least one — and the one nobody satisfies is requirement 2 (user-trainable, language-independent matching), which exists only as *engines/research*, never as a shipping Android GUI app.**

| Candidate | 1. On-device | 2. Trainable + language-independent | 3. Always-on hands-free | 4. Easy UX | Verdict |
|---|---|---|---|---|---|
| **Dicio** (F-Droid, GPL-3) | ~ hybrid (some skills online) | ❌ Vosk STT + fixed skills; language-specific | ✅ wake word | good | Best FOSS *command* baseline; wrong matching paradigm |
| **openclaw-assistant** (MIT) | ❌ cloud/self-hosted LLM | ❌ | ✅ | **best UX** | Best GUI skeleton; not standalone, not trainable |
| **takeout_assistant** / **Vicky** | ✅ offline Vosk | ❌ hard-coded commands | ✅ | basic | Offline but fixed vocab |
| **rhasspy_mobile** (MIT) | ❌ needs Rhasspy server | ❌ | ✅ | moderate | Satellite, not standalone |
| **Sayboard / FUTO / Whisper+** | ✅ offline | ❌ dictation only | ❌ no commands | good | Dictation IMEs; clean Vosk-GUI reference (Sayboard) |
| **Google Voice Access** | partial | ❌ not trainable; language-specific | ✅ | good | Proprietary; the *interaction* reference, not reusable |
| **Picovoice Porcupine/Rhino** | ✅ | ❌ proprietary + language-dependent | ✅ | SDK only | Disqualified (not OSS, not language-independent) |
| **openWakeWord / Mycroft Precise / Snowboy** | engine | ⚠️ trainable but **off-device / English / defunct** | wake only | no GUI | Engines, no Android app; train off-device |
| **DTW / few-shot QbE libraries** | ✅ | ✅ **yes** | DIY | **no GUI** | The right core — but only a library, no app |

---

## B. Gap analysis of the top candidates (what's missing from each)

### B1. Dicio — the closest FOSS *command* app
- **Has:** on-device Vosk STT, intent skills, wake word, mature Kotlin architecture, F-Droid presence, active maintenance (Oct 2025).
- **Missing for this brief:** (a) it recognizes *language* (Vosk STT), so it **degrades on damaged speech** and isn't language-independent; (b) commands are **developer-defined skills**, not **user-recorded templates** — no on-device enrollment; (c) no robustness-to-voice-drift mechanism.
- **Gap to close if forked:** replace/augment the STT-intent layer with the **on-device template/few-shot matcher** and an enrollment UI. You keep its service/wake/architecture; you add the language-independent core.

### B2. openclaw-assistant — the best UX skeleton
- **Has:** polished Compose/Material-3 chat UI, local Vosk wake word with custom phrase, active development.
- **Missing:** command understanding is a **cloud/self-hosted LLM** → not on-device, not standalone, and (critically) **an autonomous LLM agent is the exact pattern the 2026 Play accessibility policy bans** (see `02_technological_findings.md` §T2.7).
- **Gap to close if forked:** rip out the LLM/WebSocket backend; keep the UI shell; add the deterministic on-device template matcher + AccessibilityService action layer.

### B3. Vosk grammar mode — the best off-the-shelf Path-A engine
- **Has:** Apache-2.0, mature offline Android, true word-list FST restriction (+`[unk]` reject), no training needed for the grammar feature.
- **Missing:** **language-dependent** acoustic model (fails requirement 2 for damaged speech); runtime grammar only on small grammar-capable models; acoustic adaptation is a ~1-hour Kaldi script, not end-user on-device.
- **Role:** ship it as the **optional "intact-speech" mode**, not the core.

### B4. sherpa-onnx KWS — the best-maintained Path-A engine
- **Has:** Apache-2.0, very active (2026), first-class Android KWS, "any keywords without re-training", per-keyword thresholds, doubles as ONNX runtime.
- **Missing:** keywords are **tokenized from text** (language-dependent); no arbitrary-sound matching; no on-device acoustic enrollment.
- **Role:** alternative Path-A mode and/or the **deployment runtime** if you ever export a neural model.

### B5. DTW / few-shot QbE — the right core, but only a library
- **Has:** language-independent, speaker-dependent, 1–5 shot, **on-device trainable**, permissive OSS libs (cawfree, MFCC-DTW refs).
- **Missing:** **everything around it** — no Android GUI, no enrollment UX, no VAD/wake gating, no multi-template/threshold/re-enrollment logic, no AccessibilityService action layer, no always-on persistence. **This is the build.**
- **Few-shot QbE caveat:** embedding encoder trained on normal speech may handle severe distortion worse than raw-feature DTW → DTW is the safer default; QbE an enhancement.

### B6. Engines that look relevant but aren't usable here
- **Picovoice:** proprietary engine + AccessKey + 3-user free cap + language-dependent → fails OSS *and* requirement 2.
- **openWakeWord:** NC models, English-only, off-device training, no official Android.
- **Mycroft Precise / Snowboy:** trainable from samples (closest in spirit to template matching) but **PC/server-side training and both effectively defunct.**
- **Edge Impulse / TFLite Model Maker:** cloud/PC training → not end-user on-device.

---

## C. The precise missing piece (the unfilled core)

> **A user records a few examples of an arbitrary spoken command on-device, and the app matches future utterances by acoustic template / few-shot prototype — independent of any language model — with multi-template enrollment, per-command thresholds, an OOV reject path, and frictionless re-enrollment for voice drift; wrapped in a child-simple GUI and an always-on, hands-free assistant/AccessibilityService runtime.**

Every component *around* this exists in OSS (Vosk-GUI apps, Silero VAD, AccessibilityService patterns, DTW libs). **The integration into a language-independent, on-device-trainable, always-on Android accessibility app does not exist** — that is both the gap and the opportunity.

---

## D. Best library + GUI combination to build from

1. **GUI / app skeleton:** **openclaw-assistant** (best modern Compose UX — strip the cloud LLM) **or** **Dicio** (mature FOSS, F-Droid-ready, GPL) — and **Sayboard** as the reference for a clean Vosk-based recording GUI.
2. **Always-on layer:** **Silero VAD (MIT)** for endpointing + a wake word (microWakeWord, or a user-enrolled DTW wake template to stay fully language-independent), inside a `microphone` foreground service under the **default-assistant role**.
3. **The differentiator you must build (no OSS app has it):** the **on-device record-your-own-command + template/few-shot matching engine** (MFCC + VAD + DTW + multi-template + thresholds; optional QbE embedding layer), plus the **deterministic AccessibilityService** command→action layer.
4. **Optional modes:** **Vosk grammar / sherpa-onnx KWS** for intact-speech users; **whisper.cpp** for batch dictation.

See `04_build_and_reuse_plan.md` for the concrete architecture and phased plan.

---

## E. Flagged / unconfirmed
- `[snippet-only]` apps not page-verified: FUTO Voice Input, Whisper+, WhisperInput, NotelyVoice, Kõnele, AACVOX, VASIR, blurr (repo 404'd — do not rely on).
- FUTO is **source-available, not OSI-open**.
- Per-repo DTW/QbE library licenses — verify individually before reuse.
- **Coverage:** the major OSS Android channels were swept (F-Droid, GitHub, GitLab, Codeberg) — not an exhaustive claim. IzzyOnDroid was not separately searched (it is largely a superset index of the same upstream repos, so it is unlikely to change the conclusion, but a quick check before building is cheap).
