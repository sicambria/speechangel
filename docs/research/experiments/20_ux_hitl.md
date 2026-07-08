# Domain 20: Human-in-the-Loop & UX-Driven Accuracy

**Goal:** Design UX flows that directly improve recognition accuracy through smart user interaction — confirmation-gating, active disambiguation, adaptive prompting, and caregiver-optimized setup.

---

## E20-01: N-best disambiguation ("Did you say X or Y?")
**Hypothesis:** When the top-2 commands have close confidences (margin < 0.2), instead of picking one and risking a wrong action, the system can present a quick disambiguation: "Did you say 'go home' or 'go back'?" with a simple yes/no/neither response. This converts a 50% error into a 0% error, at the cost of one interaction.
**Score:** Impact=240 Feasibility=250 Constraints=200 Evidence=70 → **760 (A)**
**Description:** When `margin < 0.2`, trigger disambiguation mode: (a) speak the top-2 command names via TTS output, (b) listen for "first" / "second" / "no", (c) if "first" or "second", execute that command, (d) if "no", reject. Measure: error recovery rate, user acceptance.
**Expected outcome:** Disambiguation recovers 70-85% of margin-uncertain errors. Especially useful for minimal pairs. Adds ~3-5s per disambiguation — acceptable for important commands, annoying for frequent ones.
**How to run:** Disambiguation UI + TTS output + speech-input acceptance + user study.

## E20-02: Adaptive re-enrollment prompting ("Say it again differently")
**Hypothesis:** When a command consistently fails (FRR >20% over 10 attempts), the system should suggest re-enrollment with specific guidance: "I'm having trouble understanding 'go home.' Can you say it a bit slower and clearer? I'll record 3 new versions."
**Score:** Impact=280 Feasibility=220 Constraints=200 Evidence=70 → **770 (A)**
**Description:** Track per-command failure rate over a sliding window of 20 attempts. When failure rate exceeds threshold, trigger re-enrollment prompt with guidance based on the failure pattern: (a) if DTW distances are consistently low → suggest "speak more clearly," (b) if consistently high → suggest "try saying it the same way each time," (c) if high variance → suggest "record in different voice conditions."
**Expected outcome:** Adaptive re-enrollment reduces persistent per-command FRR by 30-50%. The guidance is evidence-based — the system diagnoses its own failure mode and suggests the right fix.
**How to run:** Per-command failure tracking + guidance logic + re-enrollment UX + accuracy measurement.

## E20-03: Caregiver calibration wizard (guided threshold tuning)
**Hypothesis:** A caregiver-assisted calibration session — where the caregiver speaks commands and provides immediate feedback (correct/wrong) — enables rapid threshold tuning and problematic-command identification in a supervised 5-minute session.
**Score:** Impact=220 Feasibility=240 Constraints=200 Evidence=60 → **720 (A)**
**Description:** Build a "Calibration Wizard": caregiver sits with the user, user speaks 20-30 test commands. Caregiver taps ✓ or ✗ for each recognition. System: (a) adjusts per-command thresholds, (b) identifies problematic commands, (c) suggests re-enrollment for weak commands. Measure: calibration time, FRR reduction vs uncalibrated.
**Expected outcome:** 5-minute calibration session reduces FRR by 15-30% vs uncalibrated baseline. Caregiver involvement is the most reliable calibration signal — humans are better at verifying than self-reporting.
**How to run:** Calibration wizard UX + caregiver-supervised threshold tuning + before/after accuracy.

## E20-04: Usage-context profile switching (home / work / car)
**Hypothesis:** Different environments have different acoustic profiles, and different contexts use different command subsets. Allowing the user/caregiver to create context profiles (e.g., "Home" with 15 household commands, "Car" with 5 driving commands) reduces the effective vocabulary per context, improving accuracy.
**Score:** Impact=220 Feasibility=230 Constraints=200 Evidence=60 → **710 (A)**
**Description:** Add context profiles: user creates named profiles with subset of commands. Profile can be auto-switched via: (a) location (geofence), (b) Bluetooth connection (car), (c) time of day, (d) manual switch. Compare per-context accuracy vs all-commands-in-one-profile.
**Expected outcome:** Context-specific profiles reduce effective vocabulary from 50→15 commands, improving rank-1 by 5-10pp per context. Profile switching is deterministic and rule-based.
**How to run:** Context profile system + profile-switching logic + per-context accuracy.

## E20-05: Confidence visualization design ("How sure" display)
**Hypothesis:** Users respond differently to different confidence visualizations. A 3-level display (green check = high confidence, yellow ? = medium, red X = low) is more usable than a numeric percentage. Testing visualization designs improves the "Try" screen's diagnostic value.
**Score:** Impact=120 Feasibility=280 Constraints=200 Evidence=50 → **650 (B)**
**Description:** Prototype 3 confidence visualization designs: (a) traffic light (green/yellow/red), (b) percentage bar (0-100%), (c) "distance meter" (near=good, far=bad). Test with users: which design leads to fastest correct identification of problem commands? Measure: time-to-diagnose, user preference.
**Expected outcome:** Traffic light design is fastest and most intuitive. Percentage bar creates false precision anxiety. Distance meter is confusing for non-technical users.
**How to run:** Confidence visualization prototypes + user study.

## E20-06: Multi-language command labeling (show command in user's script)
**Hypothesis:** Users who don't read Latin script need command labels displayed in their script (Cyrillic, Arabic, Devanagari, Chinese). The app should support Unicode command names and display them correctly in the Teach/Try/Home UI.
**Score:** Impact=100 Feasibility=280 Constraints=200 Evidence=60 → **640 (B)**
**Description:** Verify Unicode rendering in Compose TextFields and labels. Test with: Arabic (RTL), Chinese, Hindi, Cyrillic. Ensure: (a) text input accepts Unicode, (b) labels render correctly, (c) text-to-speech can voice the labels (Piper TTS multilingual), (d) sorting and search work correctly.
**Expected outcome:** All scripts render correctly. RTL languages need layout verification. No functional blockers — Compose handles Unicode natively.
**How to run:** Unicode test matrix + Compose rendering verification.

## E20-07: One-tap "Teach me more" drilling (guided enrollment flow)
**Hypothesis:** After initial enrollment (1-2 templates), the user may not realize more templates would help. A "Teach me more" flow that guides: "Good! Now say it louder" / "Now say it while facing away" / "Now say it quickly" captures condition diversity with minimal user thought.
**Score:** Impact=200 Feasibility=250 Constraints=200 Evidence=60 → **710 (A)**
**Description:** After the user enrolls 2 templates, offer "Teach me more" with guided prompts. Each prompt asks for a specific variant: louder, quieter, faster, slower, farther from mic, facing away. Compare rank-1 of guided-3-template enrollment vs blind-3-template enrollment.
**Expected outcome:** Guided enrollment captures 2-3× more acoustic diversity vs blind enrollment, translating to 3-5pp rank-1 gain with the same number of recordings.
**How to run:** Guided enrollment flow + enrollment diversity metrics + accuracy comparison.

## E20-08: Error explanation mode ("Why did it mishear?")
**Hypothesis:** When the user taps "Why was this wrong?" on a misrecognition, the system can explain: "It sounded more like 'go back' because of the 'g' sound at the start" or "The recording was too quiet" — making the system's failures transparent and actionable.
**Score:** Impact=140 Feasibility=180 Constraints=200 Evidence=40 → **560 (B)**
**Description:** On a rejection or wrong match, compute: (a) which command was confused with, (b) what acoustic feature drove the confusion (shared onset, similar duration, spectral overlap), (c) whether noise/VAD contributed. Present simplified explanation. Measure: user understanding, re-enrollment rate.
**Expected outcome:** Users who understand why an error occurred re-enroll more effectively than users given no explanation. Builds trust: the system is transparent about its limitations.
**How to run:** Error diagnosis logic + explanation UI + user study.

## E20-09: Silent mode (vibration-only wake confirmation)
**Hypothesis:** In quiet environments (meetings, libraries, bedside), audio wake confirmation is disruptive. A "silent mode" that confirms wake with a single vibration pulse and Stage-2 recognition with two pulses provides private feedback without drawing attention.
**Score:** Impact=100 Feasibility=270 Constraints=200 Evidence=50 → **620 (B)**
**Description:** Add VIBRATE permission. Replace TTS wake confirmation with: (a) wake detected → 1 short vibration, (b) command recognized → 2 short vibrations, (c) command executed → 1 long vibration. User-configurable via Always-on settings. Compare user satisfaction in quiet environments.
**Expected outcome:** Vibration feedback is sufficient for most users once trained. Audio feedback remains default. Silent mode is a critical accessibility feature — many speech-impaired users are in quiet care settings.
**How to run:** Vibration pattern implementation + user preference testing.

## E20-10: Longitudinal accuracy dashboard (per-user analytics)
**Hypothesis:** A privacy-preserving, on-device accuracy dashboard that shows: (a) recognition rate per command over time, (b) voice drift trend, (c) re-enrollment recommendations, (d) problematic command pairs. This gives the user/caregiver evidence-based insights into when and why to re-enroll.
**Score:** Impact=200 Feasibility=200 Constraints=200 Evidence=50 → **650 (B)**
**Description:** Build on-device analytics: track per-command acceptance/rejection counts, DTW distance trends (rolling average), confusion pairs. Render a simple dashboard (bar chart of per-command accuracy, trend line of DTW distances). Trigger re-enrollment notification when DTW trend increases by 20% over 2 weeks.
**Expected outcome:** Dashboard makes the invisible visible — users can see their accuracy day-by-day and make informed decisions about re-enrollment. Builds evidence for the recommended 2-4 week re-enrollment cadence.
**How to run:** On-device analytics + dashboard UI + trend detection + notification system.
