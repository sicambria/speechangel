# SpeechAngel Roadmap

Derived from `research/04_build_and_reuse_plan.md` §5 (phased plan) and §7 (non-negotiables). The
trackable artifact: each item has a checkbox and a status. Update status as work lands; keep
acceptance criteria honest (FRR + FAR/hour, never a bare "99 %").

**Legend:** `[ ]` not started · `[~]` in progress · `[x]` done · status tags: `planned` /
`active` / `blocked` / `done`.

---

## Phase 0 — Matcher spike (2–3 wks) · status: `active`

Prove the core no OSS app has: record N commands on-device → MFCC + VAD + DTW match → multi-template
+ per-command threshold + reject, on one phone, ugly UI. De-risk before any UX investment.

- [~] `core:model` — domain types (commands, templates, match results). _status: active (scaffolded)_
- [~] `core:dsp` — MFCC extractor (concatenate static+Δ+ΔΔ, never sum — LIVE BUG #1), mel filterbank,
      FFT, Silero-style VAD endpointing. _status: active (scaffolded + tests)_
- [~] `core:matching` — DTW distance, `argmin` over templates, per-command distance threshold,
      OOV/reject. _status: active (scaffolded + tests)_
- [~] `core:enrollment` — multi-template enroll, recognizer, repositories. _status: active (scaffolded)_
- [ ] Measure FRR / FAR on real (incl. dysarthric) voices, quiet + home noise. _status: planned_
- [ ] Feature front-end bake-off (plain MFCC vs PLP vs robust embedding). _status: planned_

**Phase 0 exit:** measured FRR/FAR on a real ~few-dozen-command set; the matcher beats a documented
FAR budget (≤0.5 false accepts/hr) for at least the in-quiet, distinct-command case.

---

## Phase 1 — Hands-free MVP (6–8 wks) · status: `planned`

Fork the GUI skeleton; ship the core promise for non-rooted phones with cooperative OEMs.

- [ ] `:app` module scaffolded + re-enabled in `settings.gradle.kts`. _status: planned_
- [ ] `:data` module (Room persistence for enrolled templates). _status: planned_
- [ ] Microphone foreground service (`foregroundServiceType="microphone"` +
      `FOREGROUND_SERVICE_MICROPHONE`) — gate: `verify-foreground-service-types.mjs`. _status: planned_
- [ ] Stage-1 (24/7) Silero VAD gate → software wake word (enrolled DTW wake OR microWakeWord). _planned_
- [ ] Stage-2 command matcher wired to the `core:*` engine. _status: planned_
- [ ] AccessibilityService — deterministic command→action table (`isAccessibilityTool="true"`). _planned_
- [ ] 4-screen enrollment UX (Teach / Name-Map / Try / Always-on) + caregiver setup wizard. _planned_
- [ ] Battery-optimization exemption flow. _status: planned_

**Phase 1 exit:** a non-rooted phone runs the full Teach→Try→hands-free loop end to end.

---

## Phase 2 — Persistence & policy hardening (6–8 wks) · status: `planned`

- [ ] Assistant role (`RoleManager.ROLE_ASSISTANT`) for reboot survival. _status: planned_
- [ ] Per-OEM autostart handling (DontKillMyApp guidance). _status: planned_
- [ ] Play Permission Declaration Form + prominent mic disclosure. _status: planned_
- [ ] FAR-budget threshold tuning per command. _status: planned_
- [ ] Multi-template re-enrollment polish + confirmation-gated adaptation. _status: planned_
- [ ] Optional Path-A intact-speech mode (Vosk grammar / sherpa-onnx KWS). _status: planned_

---

## Phase 3 — Delight & reach (ongoing) · status: `planned`

- [ ] QbE embedding enhancement (few-shot, milder impairment). _status: planned_
- [ ] Vocabulary-distinctness helper (warn on acoustically-close commands). _status: planned_
- [ ] Far-field / noise front-end. _status: planned_
- [ ] whisper.cpp batch dictation (optional). _status: planned_
- [ ] Shareable command packs. _status: planned_
- [ ] F-Droid + Play release. _status: planned_

---

## Cross-cutting non-negotiables (carry into every phase)

- [ ] Deterministic action layer — **never** an autonomous LLM agent. _status: planned (guardrail subject)_
- [ ] Accuracy always reported as FRR + FAR/hour. _status: planned_
- [ ] On-device enrollment stays the core — no regression to a language-dependent STT core. _planned_
- [ ] Licensing: keep Silero VAD/whisper.cpp (MIT), Vosk/sherpa-onnx (Apache-2.0); avoid NC-licensed
      models; ship a third-party-licenses screen. _status: planned_

---

## Workflow / framework track (this port)

- [x] AI workflow + guardrail system transplanted (Wave 0/2/3 + Android guardrails). _status: done_
- [ ] Install git hooks (`git config core.hooksPath .husky`) to make gates Enforced. _status: planned_
- [ ] Port worktree/plan tooling (Wave 1). _status: planned_
- [ ] CI workflow running the guardrail + core-test subset. _status: planned_

See `docs/meta/port-status.md` for the honest wave-by-wave status.
