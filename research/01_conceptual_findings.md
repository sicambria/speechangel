# Conceptual findings — the *delta* over the Turán reports

**Date:** 2026-06-28
**Scope:** Only the conceptual ideas the existing Turán reports do **not** already cover. For the task reframing (closed-set command spotting vs open dictation), the OSS engine landscape, and the desktop training-GUI design, **see** `Turan_engine/reports/` — those are reused, not repeated here.

---

## C1. The load-bearing conceptual point: "language-independent" means *don't model language at all*

The user's most unusual requirement is **language-independence because the users' speech is damaged** (stroke, illness, dysarthria) and fits no language model. This is not the same as "multilingual." It changes the architecture decision more than any other requirement, and most "obvious" answers fail it.

Three candidate architectures, and how each treats language:

| Path | Mechanism | Language posture | On-device end-user training? | Fit for damaged speech |
|---|---|---|---|---|
| **A. Language-dependent STT + grammar/KWS restriction** | A neural acoustic model decodes phonemes/words; you restrict the decoder to a small word list / keyword set | Trained on a **specific language's phonemes** | No (config only) | **Weak** — atypical sounds don't map to the trained phoneme inventory |
| **B. Fine-tune a multilingual backbone** (XLS-R / NeMo / SpeechBrain) | Self-supervised model adapted to commands | Multilingual, but **still linguistic/phonetic** | No (off-device training) | Medium — but assumes phonetic structure; training is desktop-side |
| **C. Speaker-dependent acoustic template / few-shot matching** | Compare the user's **enrolled own sounds** to the query (DTW / query-by-example / few-shot prototype) | **No language model at all** | **Yes** — enroll/re-enroll on the phone | **Best** — matches *the user's own* acoustic pattern, normal or not |

**Conclusion (this updates the prior report):** the Turán report's Part-E recommendation was "fine-tune a multilingual backbone into a closed-set classifier" (Path B). That was correct **for a desktop fine-tuning framing**, before Android + on-device enrollment + language-independence-for-damaged-speech were in scope. Once they are, **Path C is the correct core**, because:

- It is **language-independent by construction** — it never asks "what word/phoneme is this?", only "which of the user's enrolled patterns does this most resemble?". A stroke-distorted "yes" that no language model recognizes is fine, because the system is matched against the *user's own* distorted "yes".
- It is the **only** path where the end user can **train and re-train on the device** with a few samples — which is itself a hard requirement (see C3).
- Pure feature-based template matching (e.g. MFCC + DTW) has **no learned "normal-speech" prior** to misfit atypical sounds — a genuine advantage for damaged speech that the neural paths lack.

**The complementary mode:** for users whose speech is close to typical, Path A (a language-dependent grammar/KWS recognizer) is easier and may be more convenient (no enrollment). So the right product offers **both**: template-matching as the universal, language-independent core; an optional grammar/STT mode for intact-speech users. But the *core that makes the product unique and inclusive* is Path C.

> Tension noted and resolved: a query-by-example **embedding** encoder (a learned alternative to raw-feature DTW) generalizes better across a user's day-to-day variation, **but its encoder is trained on normal speech**, so it may embed severely distorted sounds poorly. Therefore: **raw-feature DTW is the safer default for severe impairment**; an embedding/QbE layer is a configurable enhancement for milder cases. Don't treat "modernize DTW" as "replace DTW with an embedding model" unconditionally.

---

## C2. The accuracy honesty principle (carry it to the top, not a footnote)

The brief asks for ">99% accuracy". The conceptual stance that must govern the whole product:

- **>99% is realistic only in quiet, with acoustically-distinct, personally-enrolled commands.** It is an **aspiration/estimate, not a measured guarantee** for always-on, far-field, impaired-speech use.
- The literature's headline ">99%" numbers are **the wrong task or the wrong conditions**: e.g. 99.2% is *speaker identification*; "100%" is a tiny clean-condition isolated-word lab study. None measure always-on far-field impaired-speech command accuracy.
- A bare "99% accurate" is **meaningless** for a command/wake system. Any accuracy claim must report **both False Rejection Rate (FRR)** and **False Acceptance Rate (FAR per hour)** — this is the prior Turán report's "accuracy-claim hygiene" point, and it is even more important here because the users are disabled and **over-promising is the most harmful failure mode of this work.**
- The three accuracy regimes are **non-comparable** and must be kept apart: generic speaker-independent KWS (~97–98%), speaker-dependent tiny-vocab (high-90s in quiet), and dysarthric *open-vocabulary transcription* (8–36% WER — a categorically harder task that does **not** set the ceiling for closed-set command recognition).

**Design implication:** market and engineer to a **FAR budget** (e.g. ≤0.5 false accepts/hour for always-on) and an FRR the user finds acceptable, with a visible "how sure was it" signal — not a headline percentage.

**The tradeoff that this number really encodes (decide it consciously).** Three of the brief's goals — **language-independence, on-device user-training, and >99%** — collide. The property that makes the recommended core (Path C / DTW) language-independent and on-device-trainable (no learned linguistic model; pure per-user acoustic matching) is *also* what caps its accuracy in the **~90s%** historically, below the personalized **neural closed-set classifiers** that more reliably reach >99% — but those are either **language-dependent** or **trained off-device**. So the honest position is: **you can reliably get any two of the three, not all three today.** This work chooses language-independence + on-device-training because they are the *inclusion* requirements for damaged speech, and accepts that >99% is a per-user aspiration to be measured, not a guarantee. If >99% were a hard, non-negotiable constraint, the rational move would be to relax language-independence (use Path A / a personalized neural classifier) for users whose speech allows it — which is exactly why the product offers Path A as a complementary mode.

---

## C3. Voice drift is the central robustness problem — and templates can't self-adapt

The target population's speech is **intrinsically variable**: dysarthria affects 22–58% of acute-stroke patients and >80% of ALS patients, and presents as *fluctuating* intelligibility with fatigue, illness, and progression. So day-to-day and within-day change is **expected, not an edge case.**

Key architectural fact: **DTW / template systems have no statistical model, so they cannot "drift along" with the voice automatically — they must be RE-ENROLLED.** (This is exactly why the prior report scored classic Turán DTW **30/100** on voice-change resilience.) Neural KWS *can* adapt online, but **silent continuous auto-retraining is dangerous** for this population — it risks adapting to bad samples and catastrophic forgetting (the entire incremental-KWS subfield exists to fight this).

**The resolution — robustness comes from enrollment design, not from a self-adapting model:**

1. **Multiple templates per command**, deliberately capturing good / tired / ill renditions of the voice.
2. **Frictionless, routine re-enrollment** — treat re-enrollment as a *first-class, primary* feature, not an afterthought. A few samples per command already help measurably.
3. **Per-command adaptive thresholds** rather than one global threshold.
4. **Confirmation-gated adaptation** — only fold a new sample into the model after the user confirms the action was correct. Never silent online retraining.

This reframes the Turán engine's worst axis (30/100) from "fatal flaw" to "solved by UX": the model stays simple and language-independent; the **robustness is bought by making enrollment effortless and habitual.**

---

## C4. "Always-on, fully hands-free" is an accessibility *concept*, not just a feature

For a user who **cannot touch the phone**, "hands-free" has a strict meaning the brief makes central: the system must keep working **across reboots and OEM task-kills without anyone touching the device.** Conceptually this splits into:

- **The recognition loop** (wake → recognize → act) — the ML problem.
- **The persistence problem** — staying alive 24/7 hands-free. On modern Android this is *the* hard part and is **a platform/policy problem, not an ML one** (see `02_technological_findings.md` §T2). Conceptually, the app is not "an app that listens" but **"the device's assistant + an accessibility tool"** — that framing is what makes always-on hands-free both technically possible and legally shippable.
- **The one unavoidable hands-on moment:** first-time setup (granting mic, enabling the AccessibilityService, selecting the assistant role, battery/autostart exemptions) **cannot be automated** by design. So the concept must include a **caregiver-assisted one-time setup**, after which operation is fully hands-free. This is an inherent, honest constraint — not a bug to engineer away.

**Inclusion concept:** the genuine "I can't use my hands" + "my speech is damaged" user is *precisely* the population the Android accessibility framework exists to serve. Building explicitly as an **accessibility tool for disability** is both the ethical framing and the thing that keeps the product on the right side of platform policy.

---

## C5. The two efforts are complementary, not overlapping (Turán / TalkTeach vs SpeechAngel)

To avoid confusion between this work and the existing `speechrecog-teach` / "TalkTeach" effort:

- **TalkTeach (`speechrecog-teach`)** = a **desktop** child-proof GUI that *trains* ASR models (Whisper/NeMo via LoRA) — training-side tooling, off-device, for building/adapting linguistic models.
- **SpeechAngel (this work)** = an **Android** app that does **on-device enrollment + runtime recognition + hands-free device control**, with a **language-independent template/few-shot core** so the *end user* (or caregiver) enrolls a few samples **on the phone**.

The architectural difference is exactly the **on-device, end-user enrollment** of Path C: TalkTeach trains a model on a PC; SpeechAngel enrolls the user's own sounds on the phone in seconds. They can share UX philosophy ("Record → Check → Teach → Try", zero-jargon, guardrails) and even prompt sets, but they solve different halves of the problem.

---

## C6. Conceptual conclusion

The unusual brief resolves to a coherent concept:

> **An Android accessibility assistant whose core recognizer is a speaker-dependent, language-independent acoustic template/few-shot matcher that the user (or caregiver) trains and re-trains on-device in seconds; gated by a low-power software wake word for always-on hands-free operation; mapping a fixed, human-defined command set to device actions via the AccessibilityService; with robustness to voice drift bought through effortless multi-template re-enrollment and confidence/rejection thresholds rather than through a self-adapting model — and with accuracy honestly reported as FRR + FAR/hour rather than a headline "99%".**

This *updates and extends* the Turán reports rather than repeating them: it keeps their task reframing and their respect for the DTW/template idea, but corrects the "fine-tune a multilingual backbone" recommendation for the Android + on-device-enrollment + damaged-speech context, and adds the always-on hands-free accessibility architecture they never addressed.
