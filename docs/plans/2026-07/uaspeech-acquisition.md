# UASpeech acquisition — the banking precondition (#24), user-initiated

**Status:** blocked (needs a user-sent email + institutional eligibility + signed license — cannot be done
in-session).

## Goal

Acquire the UASpeech dysarthric corpus (graded, multi-speaker, per-word repeats) so the standing
**positive** dysarthric levers can be banked on a cohort that fixes TORGO's n=8 single-speaker-per-severity
fragility (EVAL-005/006), and so the Tier-A reframe's retry-correlation can be *measured* rather than
assumed. (UASpeech gates the positives only — the voice-only D2 **negative** is already bankable on the
TORGO data in hand.)

## Context & Constraints

- Every positive dysarthric lever across Rounds 2–5 — the **+5.4pp vocab co-design** (held-out,
  cross-speaker, sub-8pp) and the **Tier-A operating points** (SPRT-k2 / confirm+retry, currently
  optimistic upper bounds under an independent-retry assumption) — is **NOT-BANKED pending a graded cohort.**
- **What UASpeech is:** 19 speakers with cerebral palsy, 765 isolated words/speaker (300 distinct uncommon
  + 3 reps each of digits, computer commands, radio alphabet, common words), 8-mic array + video —
  isolated-word, per-speaker repeats, intelligibility-graded (the shape TORGO lacks at scale). Sources:
  <http://www.isle.illinois.edu/sst/data/UASpeech/index.html>,
  <https://speechtechnology.web.illinois.edu/uaspeech/>.
- **Eligibility (REAL constraint):** free for "researchers employed at universities and government labs with
  an interest in universal-access technology." If not currently so affiliated, apply via a collaborating
  academic, or fall back to the already-scripted **EasyCall (Italian, #25)** / **Nemours/SAP (#26)**. Do not
  overstate affiliation.
- **Admissibility unchanged:** on-device, speaker-dependent, language/vocab-agnostic, few-shot,
  deterministic, NNAPI/INT8 ≤~150 MB (wavlm-large runs behind the VAD gate on a 2026 phone,
  `constraint-validity-check`). Real corpus only; FAR-matched, held-out-speaker adjudication (EVAL-007).

## Approach

Send the license request (only the user can), then on arrival re-run the standing positives through the
existing TORGO pipeline on the graded cohort, pre-registered and FAR-matched, banking only what replicates.

## Steps

1. **User sends the request** (from an institutional address if possible):

   **To:** uaspeech-requests@lists.illinois.edu
   **Subject:** UASpeech database access request — universal-access voice-control research

   > Dear UASpeech maintainers,
   >
   > I am [NAME], [ROLE] at [INSTITUTION / lab], working on on-device, speaker-dependent,
   > language-independent voice control for users with motor-speech disorders (an assistive-technology /
   > universal-access project). I would like to request access to the UASpeech database for research use.
   >
   > We evaluate few-shot, template/embedding-based keyword verification on dysarthric speech and need a
   > graded, multi-speaker isolated-word corpus with per-speaker repeats to measure false-reject rate at a
   > matched false-accept budget across intelligibility levels — which UASpeech uniquely provides.
   >
   > For the data transfer I can receive the data via a [Google / iCloud / OneDrive] account:
   > **[your-account@…]**. I have read and will abide by the license in LICENSE.txt; please let me know if a
   > signed agreement or any further eligibility information is required.
   >
   > Thank you very much,
   > [NAME], [INSTITUTION], [contact]

2. **On arrival:** embed UASpeech isolated words with the same `wavlm-large` L14 pooled pipeline
   (`H.scan` + `_ceiling_cache/*.npz`) used for TORGO.
3. Re-run the pre-registered, FAR-matched, held-out-speaker confirmations of the standing positives.

## Definition of Done

Each standing positive is adjudicated on the graded UASpeech cohort as **FRR at a matched FAR≤5%**
(held-out speaker, realized held-out FAR printed — never a bare %), paired McNemar where applicable
(EVAL-002/003/007):
- **(a) Vocab co-design** — banked only if the cross-speaker held-out FRR@FAR≤5% improvement replicates.
- **(b) Tier-A operating points** — SPRT-k2 / confirm+retry task-success reported jointly with turns +
  decision-FAR, with the **real measured retry-correlation** replacing the independence assumption.
- **(c) K-curve per severity** — FRR@FAR≤5% vs K, per intelligibility band.
Positives that do not replicate at matched FAR are recorded as NOT-BANKED with numbers.

## Risks & Mitigations

- **Eligibility gap** → fall back to EasyCall (#25) / Nemours (#26); do not overstate affiliation.
- **FAR inflation (the R3 trap)** → every verdict prints realized held-out FAR (EVAL-007).
- **n-fragility carried over** → report per-severity cells with raw counts; require ≥2 speakers agreeing
  in direction before banking (EVAL-005/006).

## Test & Verification

Verdicts computed by the TORGO harness pattern (`H.scan` + pooled `*.npz` + `held_out_global` @FAR≤5%),
extended to UASpeech; each banked positive requires a fresh pre-registered FAR-matched confirmation on a
held-out speaker, reported as **FRR + realized FAR** (EVAL-002/003/007). Blocker note stays in this file
until the corpus lands.
