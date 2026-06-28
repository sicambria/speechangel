# Technological findings — Android on-device recognition, always-on hands-free, OSS apps

**Date:** 2026-06-28
**Scope:** The technology layer. Engines, the Android always-on platform reality, the OSS Android app landscape, wake-word options, and accuracy/robustness evidence — all Android-and-on-device focused (the prior reports cover the desktop/server engine landscape and are reused, not repeated).

Citations are inline. Confidence and unconfirmed items are flagged throughout. **This is a fast-moving area — re-verify licenses, releases, and platform/policy details at build time.**

---

## T0. The single most important technical distinction

**On-device *inference* ≠ on-device *training*.** The brief wants the user to *record a few samples and re-train on the phone*. That requires **enrollment-based template/embedding matching**. Every neural-classifier engine below trains in the cloud/PC and only *runs* on-device — for them, "re-training" is a developer redeploy, **not** an end-user action. **Only DTW template matching and few-shot query-by-example (QbE) let the end user enroll/re-enroll on the phone.** This distinction decides the architecture.

---

## T1. Engines for the recognizer

### T1.1 DTW acoustic template matching — the language-independent core (BEST FIT for Path C)

- **Why it fits:** genuinely **language-independent** (matches raw acoustic feature trajectories, not phonemes), **speaker-dependent**, **one/few-shot** (as little as 1 template per command), and **trains + re-trains fully on-device** by recording samples. No learned "normal-speech" prior to misfit dysarthric/stroke speech. ([PLOS One — language-independent + speaker-dependent DTW](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0085458); [arXiv 2404.14903](https://arxiv.org/html/2404.14903)) — *high confidence on the mechanism.*
- **Accuracy:** classic isolated-word speaker-dependent DTW historically reaches **~90s%**; literature calls DTW "state-of-the-art for small-footprint speaker-dependent" small-vocab control. (The 71% F-score in the multi-sample-DTW paper is *embeddings*-DTW on a hard 15-word **open-vocabulary** setting — not representative of simple speaker-dependent isolated-command DTW.) — *medium-high.*
- **OSS Android starting points** (verify each license individually):
  - [cawfree/Dynamic-Time-Warping](https://github.com/cawfree/Dynamic-Time-Warping) — DTW for Android (Java).
  - [Linzecong/MFCC-DTW](https://github.com/Linzecong/MFCC-DTW), [ibillxia/MFCCandDTW](https://github.com/ibillxia/MFCCandDTW), [mradovic38/dtw-speech-recognition](https://github.com/mradovic38/dtw-speech-recognition) — MFCC+DTW references.
- **Always-on:** not built-in — add a VAD/energy gate + sliding-window scan + distance threshold (standard, self-implemented).
- **Trade-off:** you build the pipeline (MFCC + VAD + DTW + threshold tuning); **no turnkey Android SDK exists** — this is the gap to fill.
- **Voice-drift weakness:** templates can't self-adapt → solved by multi-template + easy re-enrollment + confirmation-gated adaptation (see T4 and `01_conceptual_findings.md` §C3), **not** by switching to a learned model.

### T1.2 Few-shot / QbE prototypical-network KWS — research-grade enhancement (Path C, fallback)

- Enrolls on-device from a few user samples (compute a prototype/embedding), language-independent. ([ArchitParnami/Few-Shot-KWS](https://github.com/ArchitParnami/Few-Shot-KWS), paper [arXiv 2007.14463](https://arxiv.org/pdf/2007.14463); multi-sample DTW [arXiv 2404.14903](https://arxiv.org/html/2404.14903)) — **license unconfirmed; no Android/on-device deployment shown** (flag).
- On-device personalization is **measured and cheap**: learning user-specific embeddings cut Speech-Commands-35 error **30.1%→24.3%** with **as few as 4 labeled inputs per class**, at **23.7k params, ~1 MFLOP/epoch, <4 kB** memory — microcontroller-feasible. ([arXiv 2403.07802](https://arxiv.org/html/2403.07802)) — *high confidence (primary).*
- **Caveat:** the embedding encoder is trained on **normal** speech → may embed severely distorted sounds poorly. Use as a configurable layer for milder impairment; keep raw-feature DTW as the severe-case default.

### T1.3 Vosk (Kaldi-based) — best off-the-shelf for Path A (language-dependent grammar mode)

- **License Apache-2.0**; mature, **purpose-built for offline Android** (official library + demo app; ~50 MB small models, 20+ languages, fully offline, streaming/zero-latency). ([github.com/alphacep/vosk-api](https://github.com/alphacep/vosk-api), [COPYING](https://github.com/alphacep/vosk-api/blob/master/COPYING), [alphacephei.com/vosk/android](https://alphacephei.com/vosk/android), [vosk-android-demo](https://github.com/alphacep/vosk-android-demo)) — *high.*
- **Grammar mode = real first-class feature.** Pass a **JSON array of allowed words**; the WFST graph is replaced by a subgraph restricted to that list. Append the special **`[unk]`** token to absorb out-of-grammar audio (without it the decoder can hang). Restricting from tens of thousands of words to a few dozen is the accuracy lever. ([alphacephei.com/vosk](https://alphacephei.com/vosk/); Android example [zenn.dev](https://zenn.dev/diced/articles/vosk-silero-vad-wakeword-android?locale=en)) — *high.*
  - **Constraint:** runtime vocab reconfiguration works only on **grammar-capable (mostly small) models** that ship the `tree`/phoneme-context files; **big models are static.** Pick a grammar-capable small model. — *medium-high.*
- **Acoustic adaptation** (personalizing to a voice) is possible but **not easy**: ~1 hour of audio + a Kaldi fine-tuning script, and the docs admit they're incomplete. ([alphacephei.com/vosk/adaptation](https://alphacephei.com/vosk/adaptation)) — *not* an end-user on-device feature. — *high.*
- **Language posture:** the acoustic model is language-specific → **degrades on damaged speech** (this is why Vosk is Path A, not the language-independent core). Maintenance: active (vosk-api 0.3.50, 2024-04). — *high.*

### T1.4 sherpa-onnx / k2-fsa (Next-gen Kaldi) — best maintained for Path A keyword spotting

- **License Apache-2.0**; first-class Android (pre-built APKs for streaming ASR, **keyword spotting**, VAD), offline via onnxruntime; broad device support. **Very actively maintained** (release 2026-06-18). ([github.com/k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx), [KWS docs](https://k2-fsa.github.io/sherpa/onnx/kws/index.html)) — *high.*
- **Open-vocabulary KWS:** supply a **keywords text file** (each line tokenized via `sherpa-onnx-cli text2token`); **"specify any keywords without re-training the model"**, with per-keyword **boosting score** and **trigger threshold** to trade detection vs false alarms. Cleanest "user supplies phrases, no training" story — but it's **keyword/phrase spotting**, language-dependent tokenization, not arbitrary-sound matching. ([KWS docs](https://k2-fsa.github.io/sherpa/onnx/kws/index.html)) — *high.* Also runs NeMo/Citrinet ONNX models, so it doubles as a **deployment runtime**.

### T1.5 whisper.cpp / Whisper on Android — accurate but wrong tool here

- **MIT** (whisper.cpp). Runs offline on Android (ggml, Q4/Q5; or TFLite ports). ([github.com/ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE), [vilassn/whisper_android](https://github.com/vilassn/whisper_android)) — *high.*
- **Live/streaming is ~5–7× slower than real-time** on phones (batch is usable); larger models need 2–4 GB RAM. ([discussion 3567](https://github.com/ggml-org/whisper.cpp/discussions/3567)) — *high.*
- **No true grammar restriction** — only soft biasing (`initial_prompt`, `suppress_tokens`); the model can still emit anything. ([faster-whisper advanced options](https://deepwiki.com/SYSTRAN/faster-whisper/6.2-advanced-options)) — *high.*
- **Verdict:** good optional **batch transcriber / dictation** fallback, not the always-on command core.

### T1.6 Silero — VAD yes, STT no (for commercial use)

- **Silero VAD: MIT**, 1.8 MB, ~1 ms / 30 ms chunk, ONNX, runs on Android — **ideal endpointing gate in front of any recognizer.** ([github.com/snakers4/silero-vad](https://github.com/snakers4/silero-vad)) — *high.*
- **Silero STT models: CC-BY-NC (non-commercial)** except some MIT base TTS models — **likely a dealbreaker for a product.** ([github.com/snakers4/silero-models](https://github.com/snakers4/silero-models)) — *high.* **Use Silero VAD, not Silero STT.**

### T1.7 Engines to avoid / deprioritize

- **Coqui STT (ex-DeepSpeech):** company **shut down (Dec 2023)**, STT repo unmaintained; only LM-scorer biasing, no FST grammar. Avoid for new work. ([shutdown discussion](https://github.com/coqui-ai/TTS/discussions/3489)) — *high.*
- **Kaldi proper:** has GrammarFst, but maintainers advise against on-device except very small vocab; **Vosk *is* the productized Kaldi-on-Android path** — use Vosk/sherpa-onnx instead. ([kaldi grammar](https://kaldi-asr.org/doc/grammar.html), [sourceforge thread](https://sourceforge.net/p/kaldi/discussion/1355349/thread/42a37b06/)) — *high.*
- **NVIDIA NeMo / Citrinet:** Apache-2.0 framework, **CC-BY-4.0** weights; **no first-party Android runtime** — consume via sherpa-onnx ONNX export. A **desktop training-side** component, not an on-device runtime. ([github.com/NVIDIA-NeMo/NeMo](https://github.com/NVIDIA-NeMo/NeMo)) — *high/synthesis.*
- **Picovoice Porcupine/Rhino:** **not truly OSS** — Apache-2.0 covers only SDK bindings; engine `libpv_porcupine`, acoustic `.pv` and keyword `.ppn` models are **proprietary binaries needing an AccessKey**; free tier capped at **3 active users/month**. And **language-dependent** (custom words from typed text/phonemes → can't match stroke-distorted pronunciation). Disqualified on both OSS and language-independence grounds. ([github.com/Picovoice/porcupine](https://github.com/Picovoice/porcupine), [free tier](https://picovoice.ai/blog/introducing-picovoices-free-tier/), [custom wake word](https://picovoice.ai/blog/console-tutorial-custom-wake-word/)) — *high.*
- **openWakeWord:** code Apache-2.0 but **pre-trained models CC-BY-NC-SA (non-commercial)**, **English-only**, **not few-shot** (needs thousands of synthetic positives + ~30k h negatives, trained off-device), **no official Android**. Its "custom verifier" is a speaker-dependent LR filter on an English base, not arbitrary-sound matching. Last release Feb 2024. ([github.com/dscripka/openWakeWord](https://github.com/dscripka/openWakeWord)) — *high.*
- **Edge Impulse / TFLite Model Maker:** language-independent in principle (you supply WAVs), but **trained off-device** (cloud Studio / Colab) → not end-user on-device training; Edge Impulse is commercial SaaS. ([Edge Impulse KWS](https://docs.edgeimpulse.com/tutorials/end-to-end/keyword-spotting), [TFLite Model Maker speech](https://ai.google.dev/edge/litert/libraries/modify/speech_recognition)) — *high.*

---

## T2. Always-on, fully hands-free on modern Android (the platform reality)

**Headline:** a third-party app **cannot** run a hidden background mic listener. The only architecture that is (a) able to keep the mic alive long-term, (b) survivable across reboots without a human touching the phone, and (c) shippable on Play, is **default-assistant role (`VoiceInteractionService` / `ROLE_ASSISTANT`) + a `microphone` foreground service + a deterministic `AccessibilityService`.** All platform mechanics below are **high confidence** (official Android docs/AOSP).

### T2.1 Microphone foreground service + the catch-22
- Since Android 14 (API 34), a mic-capturing service needs `android:foregroundServiceType="microphone"`, `FOREGROUND_SERVICE_MICROPHONE`, and runtime `RECORD_AUDIO`. ([FGS types](https://developer.android.com/develop/background-work/services/fgs/service-types))
- `RECORD_AUDIO` is **while-in-use** → you **cannot *start* a mic FGS from the background**, and **cannot start one from `BOOT_COMPLETED`** (blocked since Android 14, reaffirmed in 15 — throws `ForegroundServiceStartNotAllowedException`). A mic FGS *started while visible* **keeps running** in the background; what's blocked is *starting* it. ([bg-start restrictions](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start), [Android 15 FGS types](https://developer.android.com/about/versions/15/changes/foreground-service-types))
- **Android 15:** mic FGS is **not** subject to the new 6-hour `dataSync`/`mediaProcessing` timeout — it can run indefinitely. ([behavior changes 15](https://developer.android.com/about/versions/15/behavior-changes-15))
- **Android 17 (preview, 2026):** "background audio hardening" tightens this further (apps need a visible activity or a WIU-capable FGS) — trajectory is *more* restriction. ([bg-audio 17](https://developer.android.com/about/versions/17/changes/bg-audio)) — *medium-high (preview).*

### T2.2 The assistant role is the persistence lever
- The user-selected `VoiceInteractionService` is **bound by the system on boot and kept always running**, explicitly "to listen for hotwords in the background" — solving the reboot catch-22 hands-free. It is also on the **official exemption list** allowed to start a WIU mic FGS from the background. ([AOSP voice interaction](https://source.android.com/docs/automotive/voice/voice_interaction_guide), [VoiceInteractionService ref](https://developer.android.com/reference/android/service/voice/VoiceInteractionService))
- Claim it via an `android.intent.action.ASSIST` intent filter + `VoiceInteractionService` metadata + `RoleManager.ROLE_ASSISTANT` request; the **user must select your app as default assistant** (only one can be). ([RoleManager](https://developer.android.com/reference/android/app/role/RoleManager))
- **Two caveats:** (1) the **low-power DSP hotword path** (`AlwaysOnHotwordDetector` / `SoundTriggerManager`) is **system-only since Android 12** → a normal app must do **software** wake-word on a live mic stream. ([Android 12 release](https://source.android.com/docs/whatsnew/android-12-release)) (2) Reinstall may clear the assistant Secure Setting, needing re-selection — *low-medium confidence (community report).*

### T2.3 OEM task-killers are the dominant real-world failure
- Samsung, OnePlus, Huawei, Xiaomi layer aggressive battery managers that kill even foreground services; no public API — requires per-OEM user setup (disable battery optimization, lock in recents, enable autostart). ([dontkillmyapp.com](https://dontkillmyapp.com/xiaomi)) — *medium (crowd-sourced).*
- **Mitigations:** `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` exemption (one-tap whitelist), caregiver-guided per-OEM autostart setup, and **tight wake-lock usage** (Google's Android vitals penalizes "excessive wake locks" from 2025). ([Doze](https://developer.android.com/training/monitoring-device-state/doze-standby), [wake-lock guide](https://android-developers.googleblog.com/2025/09/guide-to-excessive-wake-lock-usage.html))

### T2.4 Two-stage recognition (battery architecture) — mandatory
- **Stage 1 (24/7):** lightweight **software wake-word** on the continuous mic stream. **Stage 2 (on trigger):** spin up the heavier recognizer (the template matcher / on-device STT) for a bounded utterance, then idle it.
- **Never** run continuous ASR as the always-on layer: `SpeechRecognizer` is **not built for continuous transcription** (fires `onEndOfSpeech()` on silence, beeps each restart, no custom models). Use it / an embedded engine only as Stage 2. ([SpeechRecognizer ref](https://developer.android.com/reference/android/speech/SpeechRecognizer))
- **Power (treat absolutes as low confidence; ratio is solid):** software wake-word ~1–2%/hr vs continuous ASR ~8–15%/hr → gating is essential. (Vendor sources; [Porcupine ~3.8% CPU on one Pi-3 core](https://picovoice.ai/docs/faq/porcupine/).)

### T2.5 Wake-word engine options (Stage 1)
- **microWakeWord** — powers Home Assistant Voice; the **HA Android app runs it on-device in the background even when locked** — the best real-world proof a third-party Android app can do always-on software wake-word. HA openly notes the battery impact. ([HA Android voice](https://www.home-assistant.io/voice_control/android/)) — *high.* (Apache-2.0 lineage — verify.)
- **Porcupine** — most optimized, full Android SDK, but **commercial/closed engine** (see T1.7).
- **openWakeWord** — OSS code but NC models / English / no official Android (see T1.7).
- **Vosk VAD + a wake phrase** — the [Dicio](https://github.com/Stypox/dicio-android) approach ("Hey Dicio").
- **For Path C consistency:** a wake word can itself be a **user-enrolled DTW template** — keeping the whole stack language-independent and trainable. (Novel but straightforward; this is part of the gap to build.)

### T2.6 Driving the whole device by voice — AccessibilityService
- A custom app **can** control the entire device hands-free: `performGlobalAction()` (home/back/recents/notifications/etc.), `dispatchGesture()` (taps/swipes), node-tree inspection/clicking — this is exactly how **Google Voice Access** works. ([AccessibilityService ref](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService), [Voice Access](https://support.google.com/accessibility/android/answer/6151848)) — *high.*
- **Cannot be enabled programmatically** — user must turn it on in Settings (deliberate security gate) → caregiver-assisted one-time setup. — *high.*

### T2.7 Google Play policy — the shippability discriminator
- **AccessibilityService policy:** only genuine disability-helping apps may set `isAccessibilityTool="true"`; such tools get autonomous-functionality + prominent-disclosure exemptions, but must complete the **Permission Declaration Form** (feature, disabilities served, demo video). ([policy](https://support.google.com/googleplay/android-developer/answer/10964491)) — *high.*
- **2026 tightening:** the policy **prohibits using the Accessibility API for apps that "autonomously initiate, plan, and execute actions"** (aimed at LLM agents / "do it for me" / RPA) **but explicitly still permits (a) accessibility tools for disability and (b) deterministic, rule-based automation following a static human-defined script.** Reported enforcement **Jan 28, 2026** — *medium confidence on the exact date (secondary blog [myappmonitor](https://myappmonitor.com/blog/google-play-accessibility-services-policy-update)); verify against the [official policy](https://support.google.com/googleplay/android-developer/answer/10964491).*
- **Make-or-break design line:** build as a **deterministic command→action tool** (`isAccessibilityTool=true`, fixed human-defined command map). If you use an LLM to *interpret free-form speech and autonomously decide device actions*, you risk the banned category **even though you serve disabled users** — **autonomy, not the user population, triggers the ban.** Keep any LLM strictly as a *speech→one-of-N-fixed-intents classifier* with a deterministic action layer. — *principle high confidence; reviewer margin uncertain → legal/policy review recommended.*
- Always-listening mic also triggers Play **prominent-disclosure/sensitive-permission** requirements — disclose in-app and in the listing. ([data policy](https://support.google.com/googleplay/android-developer/answer/16558241))

---

## T3. OSS Android app landscape & the GUI gap

(Full detail in `03_candidate_gap_analysis.md`; summary here.) Searched F-Droid, GitHub, GitLab, Codeberg.

- **Dicio** ([repo](https://github.com/Stypox/dicio-android), [F-Droid](https://f-droid.org/en/packages/org.stypox.dicio/), GPL-3, active Oct 2025) — the **only genuine voice-*command* app on F-Droid**; on-device Vosk STT + intent skills + wake word. **Not** template-trainable, **not** language-independent. Good architecture baseline.
- **openclaw-assistant** ([repo](https://github.com/yuga-hashimoto/openclaw-assistant), MIT, Compose/Material-3, 286★, active Apr 2026) — **best modern UX**, but command understanding is **cloud/self-hosted LLM**. Best GUI skeleton to fork.
- **takeout_assistant** (AGPL-3, offline Vosk) / **Vicky** (MIT, offline) — offline but **hard-coded** commands.
- **rhasspy_mobile** (MIT) — needs a **Rhasspy server** (not standalone).
- **Sayboard** ([repo](https://github.com/ElishaAz/Sayboard), GPL-3, F-Droid) — on-device Vosk **dictation IME**, literally based on `vosk-android-demo` — cleanest Vosk-GUI reference. FUTO Voice Input (source-available, not OSI), Whisper+/WhisperInput/Kõnele — other dictation IMEs.
- **Accessibility/AAC:** **no FOSS Voice Access equivalent**; **no OSS Android app lets a dysarthric user train their own command vocabulary on-device** — the exact target niche.
- **GitLab/Codeberg:** only minor Vosk clients; nothing matching the target (explicit negative).

---

## T4. Accuracy & robustness evidence (Android-relevant)

- **Benchmark ceiling:** generic speaker-independent KWS on Google Speech Commands clusters ~**97–98%** (Keyword-MLP 97.63% V2-12). ([arXiv 2104.00769](https://arxiv.org/pdf/2104.00769), [MLPerf Tiny](https://arxiv.org/pdf/2106.07597)) — *high.* This is the floor personalization should beat — not your regime.
- **Personalization is the dominant lever:** ~**19% error reduction from 4 samples/class** on-device ([arXiv 2403.07802](https://arxiv.org/html/2403.07802)); speaker-dependent isolated-word lab studies reach 98.5% (MFCC). — *high / medium.*
- **Dysarthric/atypical (reframe!):** the scary numbers are **open-vocabulary transcription**, not closed-set commands. **Project Euphonia** personalization cut median WER **>80%**; in the **home-command domain ~89%→~13% WER** (≥300 utterances, fine-tune bottom 5/8 encoder layers; personalized models even beat human transcribers). **Project Relate** enrolls via **500 phrases**. **Speech Accessibility Project**: 36.3%→23.7% WER fine-tuned, best challenge 5.3–8.11%. ([Euphonia blog](https://research.google/blog/project-euphonias-personalized-speech-recognition-for-non-standard-speech/), [personalized ASR](https://research.google/blog/personalized-asr-models-from-a-large-and-diverse-disordered-speech-dataset/), [Relate](https://www.deeplearning.ai/the-batch/project-relate), [SAP](https://arxiv.org/html/2507.22047v1)) — *high.* **All reach accuracy via personalization on the user's own recordings** — the on-device-enrollment analogue of Path C. (Note: these are **cloud/research**, not OSS on-device SDKs.)
- **DTW can't self-adapt → re-enroll:** "for feature-based DTW … speaker adaptation cannot be employed due to the lack of a statistical model." ([DTW review](https://www.jstage.jst.go.jp/article/jsp/18/2/18_89/_pdf)) Neural KWS can adapt online but **silent auto-retraining is risky** (drift/forgetting — AnalyticKWS, DE-KWS, Rainbow Keywords exist to fight it). — *medium-high.*
- **Mitigations (ranked):** multiple templates/command (QbE merges several enrollments) → frictionless re-enrollment → per-command adaptive thresholds → confirmation-gated adaptation. ([QbE on-device KWS](https://www.researchgate.net/publication/339405729_Query-by-Example_On-Device_Keyword_Spotting))
- **Vocabulary design:** choose **acoustically-distinct** commands (avoid minimal pairs / shared onsets: "blue/glue", "forward/four"); add an **OOV/garbage reject** path + confidence floor. ([KWS review](https://arxiv.org/html/2312.05640v1), [LLM-Synth4KWS hard negatives](https://arxiv.org/html/2505.22995v1)) — *high.*
- **Noise / always-on:** evaluate at SNR −5…+15 dB; the real metric is **recall at a fixed false-accepts/hour** (target ≤0.5/hr). Front-end enhancement + speech-presence gating + multi-condition enrollment + far-field handling. ([data-aug](https://ar5iv.labs.arxiv.org/html/1808.00563), [NTC-KWS](https://arxiv.org/html/2412.12614v1)) — *high.*

---

## T5. Re-ranked engine table (NEW axes: Android + always-on + on-device enrollment + language-independence)

The prior Turán report scored engines for **desktop fine-tuning** (NeMo 88 / SpeechBrain 86 / wav2vec2 84 …). Under **this** brief's constraints the ranking **inverts** — on-device-enrollment + language-independence dominate, and the big neural frameworks become *training-side components*, not the on-device runtime. Scores 0–100, analyst-assigned for *this* task.

| Engine / approach | Truly OSS + commercial-ok | Offline Android infer | Language-independent | On-device end-user (re)training | Always-on fit | Maintenance | **Fit for THIS brief** |
|---|---|---|---|---|---|---|---|
| **DTW template matching** (build) | ✅ (perm. libs) | ✅ | ✅ **yes** | ✅ **yes (1–5 shot)** | DIY (VAD) | timeless / libs vary | **95 — the core** |
| **Few-shot QbE embeddings** | ⚠️ unconfirmed | ⚠️ no demo | ✅ (encoder caveat) | ✅ (enroll) | DIY | research | **70 — enhancement** |
| **Vosk grammar mode** | ✅ Apache-2.0 | ✅ mature | ❌ language-specific | ❌ (config only) | via VAD | active | **72 — Path A mode** |
| **sherpa-onnx KWS** | ✅ Apache-2.0 | ✅ mature | ❌ (tokenized text) | ❌ (no retrain) | ✅ KWS | **very active** | **70 — Path A mode** |
| **Silero VAD** | ✅ MIT | ✅ | n/a | n/a | ✅ gate | active | **essential helper** |
| **microWakeWord** | ✅ (verify) | ✅ (HA proven) | ❌ | ❌ | ✅ wake | active | **wake-word option** |
| whisper.cpp | ✅ MIT | ⚠️ slow live | ✅ multiling. | ❌ | ❌ | active | **45 — batch fallback** |
| Picovoice Porcupine/Rhino | ❌ proprietary engine | ✅ | ❌ phoneme/text | ❌ (cloud Console) | ✅ | active | **disqualified** |
| openWakeWord | ⚠️ NC models | ⚠️ 3rd-party | ❌ English | filter only | ✅ | 2024 | **30** |
| Edge Impulse / TFLite MM | ❌ / tooling-only | ✅ | ✅ | ❌ (cloud/PC) | DIY | active | **off-device training** |
| NeMo / SpeechBrain / Coqui | ✅ (NeMo) / dead (Coqui) | via export only | ✅ | ❌ | ✅ via runtime | active / dead | **desktop training-side only** |

**Reading it:** the on-device runtime/core is **DTW template matching** (+ optional QbE), with **Vosk/sherpa-onnx** as the convenient language-dependent mode for intact speech, **Silero VAD** + a wake-word engine for always-on, and the big neural frameworks relegated to optional **desktop-side** model production (consumed via sherpa-onnx ONNX if used at all).

---

## T6. Flagged / unconfirmed (verify at build time)
- Per-repo licenses of DTW libs (cawfree, Linzecong, etc.) and **Few-Shot-KWS** — confirm individually.
- Exact SPDX of the **Coqui STT** repo (MPL-2.0 lineage assumed).
- **Vosk** "big models static" and which specific small models permit runtime grammar — check per-model files.
- **microWakeWord** license — confirm before commercial use.
- **Play 2026** accessibility enforcement date + banned-app itemization — verify against the live official policy.
- Absolute **battery %** for always-on listening — vendor-sourced; the wake-vs-ASR *ratio* is the reliable part.
- **Android 17** background-audio hardening — preview; may change before stable.
