# Build & reuse plan — SpeechAngel Android app

**Date:** 2026-06-28
**Goal:** the cheapest, most reliable path to an Android app that does **on-device, language-independent, user-trainable** command recognition, **always-on and hands-free**, with **10-year-old-easy UX**, robust to voice drift, for immobilized and speech-impaired users.

**Strategy in one line:** **fork a modern Vosk-based Android GUI, strip it to a deterministic shell, and add the missing on-device template/few-shot engine + the assistant-role / AccessibilityService / two-stage-wake architecture.** ~Most of the scaffolding is reusable OSS; the genuinely new work is the language-independent on-device matcher, the enrollment UX, and the always-on persistence/accessibility plumbing.

---

## 1. Target architecture (four layers)

```
┌──────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE / IDENTITY                                                 │
│  VoiceInteractionService + RoleManager.ROLE_ASSISTANT (ASSIST filter)  │
│  → system keeps it alive, auto-binds on boot (solves reboot catch-22), │
│    exempt to start a WIU mic FGS from background.                       │
├──────────────────────────────────────────────────────────────────────┤
│  CAPTURE  —  foreground service, type "microphone"                      │
│  FOREGROUND_SERVICE_MICROPHONE + RECORD_AUDIO; started while visible    │
│  at setup, kept running; battery-optimization exemption; per-OEM        │
│  autostart guidance (DontKillMyApp).                                    │
├──────────────────────────────────────────────────────────────────────┤
│  RECOGNITION  —  two stages (battery)                                   │
│   Stage 1 (24/7): Silero VAD gate → software WAKE word                  │
│       (user-enrolled DTW wake template  OR  microWakeWord)              │
│   Stage 2 (on trigger): COMMAND MATCHER                                 │
│       core: MFCC + DTW template match over user-enrolled templates      │
│             (multi-template, per-command thresholds, OOV/[reject])      │
│       optional: few-shot QbE embedding layer (milder impairment)        │
│       optional Path-A mode: Vosk grammar / sherpa-onnx KWS (intact)     │
│       optional dictation: whisper.cpp (batch)                           │
├──────────────────────────────────────────────────────────────────────┤
│  ACTION  —  AccessibilityService, isAccessibilityTool="true"            │
│  DETERMINISTIC, human-defined command→action table →                   │
│  performGlobalAction() / dispatchGesture() / node clicks.              │
│  (NEVER an autonomous LLM agent — Play-policy make-or-break.)           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. The on-device matcher (the part you build — no OSS app has it)

**Pipeline:** mic frames → pre-emphasis + Hamming + framing → **MFCC** (and Δ/ΔΔ — note the Turán report's LIVE BUG #1: *concatenate* static+Δ+ΔΔ into one vector, never sum them) → **Silero VAD** endpointing → **DTW** distance against each stored template → `argmin` with a **per-command distance threshold**; below-threshold-for-all → **reject** (OOV/garbage).

**Robustness (this is where accuracy is won — see `01_conceptual_findings.md` §C3):**
- **Multiple templates per command** (good / tired / ill renditions), distances combined (min or k-NN).
- **Frictionless re-enrollment** as a primary feature — "add a new way of saying this".
- **Per-command adaptive thresholds**, not one global threshold; tune to a **FAR budget (≤0.5 false accepts/hr)**.
- **Confirmation-gated adaptation** — only fold a new sample in after the user confirms the action was right. No silent online retraining.
- **Vocabulary design helper** — warn when two enrolled commands are acoustically close (minimal pairs / shared onset); nudge toward multi-syllable, distinct words.

**Engine choice within Path C:** **raw-feature MFCC-DTW is the default** (language-independent, no normal-speech prior — safest for severe impairment). A **few-shot QbE embedding** matcher (arXiv 2403.07802 style: ~4 samples/class, ~24k params, <4 kB) is a **configurable enhancement** for milder cases — but its encoder is trained on normal speech, so don't make it the only path.

**Reuse:** [cawfree/Dynamic-Time-Warping](https://github.com/cawfree/Dynamic-Time-Warping) (Android Java DTW) + an MFCC implementation (verify licenses); [Silero VAD](https://github.com/snakers4/silero-vad) (MIT). Don't reinvent DTW/MFCC/VAD.

---

## 3. Reuse map (don't build what exists)

| Need | Reuse | License | Role |
|---|---|---|---|
| App/GUI skeleton (best UX) | **openclaw-assistant** (strip cloud LLM) | MIT | Compose/Material-3 shell |
| Alt. skeleton (mature FOSS) | **Dicio** | GPL-3 | Service/wake/architecture baseline |
| Vosk-recording-GUI reference | **Sayboard** (= polished `vosk-android-demo`) | GPL-3 | Enrollment/record UI pattern |
| Endpointing / VAD | **Silero VAD** | MIT | Stage-1 gate, trim enrollment clips |
| Wake word (option) | **microWakeWord** (HA-proven on Android) | verify | Stage-1 wake |
| DTW core | **cawfree/Dynamic-Time-Warping** + MFCC lib | verify | The matcher |
| Path-A intact-speech mode | **Vosk** grammar / **sherpa-onnx** KWS | Apache-2.0 | Optional language-dependent mode |
| Batch dictation (option) | **whisper.cpp** | MIT | Optional text entry |
| Desktop training (if ever) | **NeMo / SpeechBrain / sherpa-onnx export** | Apache-2.0 | Off-device model production only |
| Shared training-UX philosophy | **`speechrecog-teach` / TalkTeach** | (sibling) | Reuse "Record→Check→Teach→Try", zero-jargon, guardrails |

**New work (the ~15% that is the real IP):** the language-independent on-device matcher + multi-template/threshold/re-enrollment logic; the child-simple enrollment + try-it UX; the assistant-role + mic-FGS + AccessibilityService persistence/action plumbing; the deterministic command→action mapping.

---

## 4. UX (reuse the TalkTeach philosophy, Android-native)

Four-screen, one-path, zero-jargon, guardrailed (mirroring the proven TalkTeach design, but for **on-device enrollment** not model training):
- **Teach** — big mic button; record a command 2–3 times ("say it again"); live VAD trims silence; quality thumbs-up/down (clipping/too-quiet/too-noisy).
- **Name/Map** — pick what this command *does* (from a fixed, human-defined action list).
- **Try** — speak → see which command matched + a confidence meter ("how sure" not "WER"); wrong? → one tap to add another example (re-enrollment loop).
- **Always-on toggle** + a clear "I'm listening" indicator; "Grown-up mode" hides thresholds/FAR settings.
- **Caregiver setup wizard** for the one-time, un-automatable grants (mic, AccessibilityService, assistant role, battery/autostart exemption) with per-OEM guidance.

---

## 5. Phased plan

- **Phase 0 — Matcher spike (2–3 wks).** Prove the core: record N commands on-device → MFCC+VAD+DTW match → multi-template + threshold + reject, on one phone, ugly UI. De-risks the one thing no OSS app has. Measure FRR/FAR on real (incl. atypical) voices.
- **Phase 1 — Hands-free MVP (6–8 wks).** Fork the GUI skeleton; wire mic FGS + Silero VAD + Stage-1 wake + Stage-2 matcher; AccessibilityService deterministic action table; the 4-screen enrollment UX + caregiver setup wizard. Battery-optimization exemption. **Ships the core promise** for non-rooted phones with cooperative OEMs.
- **Phase 2 — Persistence & policy hardening (6–8 wks).** Assistant role (`ROLE_ASSISTANT`) for reboot-survival; per-OEM autostart handling; **Play Permission Declaration Form** + prominent mic disclosure; FAR-budget threshold tuning; multi-template re-enrollment polish; optional Vosk/sherpa-onnx intact-speech mode.
- **Phase 3 — Delight & reach (ongoing).** QbE embedding enhancement; vocabulary-distinctness helper; far-field/noise front-end; whisper.cpp dictation; shareable command packs; F-Droid + Play release.

---

## 6. Licensing strategy
- Fork choice sets the floor: **Dicio (GPL-3)** → simplest to default the whole app **GPL-3** and reuse freely (consistent with Turán's GPL-3 lineage). **openclaw-assistant (MIT)** → more permissive but you re-add UX.
- Keep **Silero VAD (MIT)**, **whisper.cpp (MIT)**, **Vosk/sherpa-onnx (Apache-2.0)** — all compatible.
- **Avoid:** Silero STT (CC-BY-NC), openWakeWord models (CC-BY-NC-SA), Picovoice (proprietary) — all fail commercial/OSS goals.
- Verify per-repo DTW/MFCC and microWakeWord licenses before integration; ship a third-party-licenses/credits screen.

---

## 7. The non-negotiables (carry these as gates)
1. **Deterministic, NOT an autonomous LLM agent** — `isAccessibilityTool=true` + fixed command→action map. Autonomy triggers the 2026 Play ban regardless of serving disabled users. (Verify the live policy + complete the Permission Declaration Form.)
2. **Accuracy reported as FRR + FAR/hour**, never a bare "99%". >99% is the in-quiet, distinct-command aspiration — engineer to a FAR budget for always-on far-field impaired speech.
3. **On-device enrollment is the differentiator** — the language-independent matcher trained by the user on the phone is the whole point; don't regress to a language-dependent STT core.
4. **Robustness = effortless re-enrollment + multi-template + confirmation-gated adaptation**, not a self-adapting model.
5. **First-time setup needs a caregiver** (un-automatable grants) — design for it honestly; everything after is hands-free.

---

## 8. Open questions to resolve in Phase 0
- Measured FRR/FAR of MFCC-DTW on a real few-dozen-command set, in quiet and in home noise, for typical **and** dysarthric voices (no public benchmark pins this — you must measure).
- Best feature front-end for damaged speech (plain MFCC vs PLP vs a robust embedding) — CNN-PPG hit 93.5% vs CNN-MFCC 65.7% on dysarthric commands ([arXiv 2106.10259](https://arxiv.org/pdf/2106.10259)), worth a bake-off.
- Battery cost of the chosen Stage-1 wake on target phones (the absolute %s in the literature are vendor-sourced/low-confidence — measure on device).
- Whether a user-enrolled DTW **wake word** is reliable enough to keep the whole stack language-independent, or microWakeWord is needed.
