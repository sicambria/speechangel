# SpeechAngel research — Android trainable, language-independent voice control

**Compiled:** 2026-06-28
**Question researched:** Is there a modern Android app (or reusable OSS partial/full solution) for **trainable, language-independent** speech recognition that can hit **>99% on a fixed small vocabulary (< 100 words)**, run **always-on / fully hands-free** for immobilized users, stay robust to **voice changes** (illness, stroke), and ship with **state-of-the-art, 10-year-old-easy UX**?

This folder records the findings **in detail**, split as requested into **conceptual** and **technological** parts, plus a **candidate gap analysis** and a **build/reuse plan**.

---

## Relationship to the existing Turán reports (reuse, don't repeat)

Detailed prior work lives in `/home/arsvivendi/git/Turan_engine/reports/` and is **reused, not restated** here:

- `Turan_RMS_architecture_and_ASR_comparison_2026-06-27.md` — documents Turán RMS (speaker-dependent isolated-word **DTW template matcher**, Hungarian, GPL-3), **reframes the task** as closed-set command spotting (where ≥99% *is* achievable, unlike open dictation), and scores OSS engines for a **desktop fine-tuning** framing.
- `open_source_realtime_ASR_libraries_research_2026-06-27.md` — the deep OSS ASR library landscape, SI-unit benchmarks, algorithm history, and the ">99% WER is not achievable for general ASR" finding.
- `ASR_training_GUI_wizard_research_and_design_2026-06-27.md` — the **"TalkTeach" desktop training-GUI** design and training-tooling gap analysis (sibling repo `speechrecog-teach`, Phase 0 done).

**What THIS research adds (the genuine gaps the prior reports do not cover):**
1. **Android-specific** on-device deployment and runtime reality.
2. **Always-on, fully hands-free** Android architecture (Android 14–17 mic rules, foreground services, the assistant role, the AccessibilityService, battery, Play policy).
3. The **OSS Android *app* / F-Droid GUI gap** (the prior report covered a *desktop training* GUI, not an Android command app).
4. **Language-independence for damaged/atypical speech** — and why this **updates** the prior report's "fine-tune a multilingual backbone" recommendation once on-device enrollment + language-independence are in scope.
5. On-device **enrollment / re-enrollment** mechanics for robustness to voice drift.

---

## The thesis (read this first)

1. **The defining requirement — language-independence *for damaged speech* — forces a specific architecture.** Three paths exist; only one is truly language-independent:
   - **Path A — language-dependent STT + grammar/keyword restriction** (Vosk grammar mode, sherpa-onnx KWS). Easy, Android-native, off-the-shelf — but the acoustic models are trained on a *specific language's phonemes*, so they degrade on stroke/dysarthric speech that doesn't map to standard phonemes. **Not** truly language-independent.
   - **Path B — fine-tune a multilingual neural backbone** (the prior report's Part-E pick: SpeechBrain/NeMo/XLS-R). Still linguistic, still assumes phonetic structure, and trains **off-device**. Good for the *desktop training* effort; wrong for *on-device enrollment* by an end user.
   - **Path C — speaker-dependent acoustic template / few-shot matching on the user's *own* enrolled sounds** (modernized DTW = query-by-example KWS; or the on-device few-shot personalization of arXiv 2403.07802). **Language-independent by construction** — it compares the user's enrollment to the user's query, with no language model. This is the original Turán DTW idea, modernized, and it is exactly the gap with **no Android app** today.

   **Position: Path C is the correct *core* for the damaged-speech requirement, with Path A as a complementary mode for users with intact speech.** This **updates** the prior report's multilingual-backbone recommendation, which was made before the Android + on-device-enrollment + language-independence constraints were in scope.

2. **>99% is an aspiration, not a guarantee.** It is realistic **in quiet, with acoustically-distinct commands**; the literature's headline ">99%" figures are wrong-task (speaker ID) or clean-lab. For always-on, far-field, impaired speech it must be **engineered and reported as FRR + FAR/hour**, never as a bare "99%".

   **The central tradeoff — name it before you build.** Your three headline goals — **language-independence, on-device user-training, and >99%** — are in tension; today's evidence says you can reliably get **any two, not all three.** The language-independent, user-enrollable core we recommend (DTW / QbE) historically tops out in the **~90s%**, not a guaranteed >99%; the approaches that more reliably reach >99% on a fixed small vocabulary (personalized **neural closed-set classifiers**) are either **language-dependent** or **trained off-device**. This report deliberately chooses **language-independence + on-device-training** (the inclusion requirement for damaged speech) and treats >99% as an aspiration measured per-user. **If >99% is a hard contractual constraint rather than a goal, that is the lever to revisit** — and for users with intact/mild speech, the optional Path-A mode or a personalized neural classifier may be the better accuracy choice. Phase 0 must *measure* FRR/FAR per user to see where each user actually lands.

3. **There is no off-the-shelf app.** No single OSS Android app combines on-device + user-trainable language-independent matching + always-on hands-free + great UX. The trainable-template idea exists only as **engines/research**. The realistic plan is **fork a Vosk-based Android GUI + build the missing on-device template/few-shot engine + the assistant-role / AccessibilityService / two-stage-wake architecture.**

4. **Always-on hands-free is a hard Android-platform problem, not just an ML problem.** The only shippable architecture is **default-assistant role + microphone foreground service + deterministic AccessibilityService**, and the **make-or-break Play-policy line is "deterministic command→action tool, NOT autonomous LLM agent."**

---

## Files

| File | Contents |
|---|---|
| `01_conceptual_findings.md` | The *delta* conceptual findings: language-independence-for-damaged-speech reasoning, always-on accessibility concept, voice-drift / re-enrollment, accuracy honesty. References the Turán reports for the reframing & engine landscape. |
| `02_technological_findings.md` | Android on-device engines (Vosk grammar, sherpa-onnx KWS, whisper.cpp, Silero VAD…), always-on hands-free platform reality, OSS Android apps landscape, wake-word engines, accuracy/dysarthric tech, **re-ranked engine table** on the new axes. |
| `03_candidate_gap_analysis.md` | Gap analysis for the top candidates against the four hard requirements. |
| `04_build_and_reuse_plan.md` | Concrete Android build/reuse plan: architecture, fork targets, phased plan, licensing, and the deterministic-not-LLM-agent Play-policy line. |

---

## Method & confidence

Findings come from 6 parallel research agents (web search + primary-source fetch), reconciled against the three existing Turán reports and reviewed by a stronger advisor model. Per-claim confidence and unconfirmed/flagged items are carried through into each file. The Android platform mechanics are **high confidence** (official Android docs/AOSP); the Play 2026 accessibility enforcement date and absolute battery percentages are **lower confidence** and flagged. Fast-moving area — re-verify product/license/policy details at build time.
