# Scientific Scope Taxonomy

A scope-first discipline for framing every experiment and SOTA claim in this repo. Adapted from the kaizen
scientific-profile idea; it complements the standards in `docs/standards/engineering-principles.md` and the
journey discipline recorded under `docs/testing/`. The premise: a result is only meaningful relative to a
**fixed scope**. An unstated scope is how "we beat SOTA" quietly means "on our convenient split, at a threshold
we picked after seeing the test set." Pin the four levels below before running experiments; revisit only on a
deliberate scope change and record it.

Answer top-down — each level constrains the next. A benchmark chosen at Level 4 that does not test the
constraints named at Level 3 is measuring the wrong thing.

| Level | Question | Determines |
| --- | --- | --- |
| 1. Domain | What scientific field does this repository belong to? | Primary literature, venues, expert communities, high-level benchmark families |
| 2. Task | What specific problem is being solved? | Canonical datasets, standard metrics, SOTA baselines, common architectures, evaluation protocols |
| 3. Scenario / Constraints | Under what assumptions and operating conditions must the solution work? | Comparable papers, specialized datasets, robustness tests, deployment constraints, domain metrics |
| 4. Evaluation Profile | How is success demonstrated, scientifically and practically? | Datasets, metrics, statistical tests, ablations, reproducibility requirements, deployment acceptance criteria |

## This repository's scope (worked instance)

- **1. Domain** — Speech Processing: on-device keyword spotting / wake-word detection and speaker
  enrollment-and-matching, with a robustness focus on impaired and dysarthric speech. Communities: Interspeech,
  ICASSP; SSL speech representation and small-footprint keyword-spotting literature.
- **2. Task** — wake-gate detection plus speaker verification against an enrolled template (the CP-2 line of
  work). Standard metrics: detection rate at a fixed false-accept budget; the small-footprint model families
  (keyword-spotting CNNs, SSL front-ends such as DistilHuBERT distilled for edge use).
- **3. Scenario / Constraints** — streaming, always-on, embedded Android; low compute and power budget; noisy
  far-field ambient audio; impaired/dysarthric speakers and cross-speaker generalization; license-restricted
  corpora that never enter the repo (TORGO audio, the Picovoice benchmark set) and are referenced only by
  external directory, per `docs/standards/documentation-governance.md`.
- **4. Evaluation Profile** — datasets: TORGO and the Picovoice benchmark corpus, held out by speaker. Primary
  metric: **false-fires per hour of ambient audio** at a matched detection rate — never a bare accuracy number.
  Adjudication: at least two speakers or folds agreeing in direction, and a curve-area summary preferred over a
  single knife-edge threshold. Ablations close the front-end-versus-matcher 2x2 before a causal claim (the
  DistilHuBERT front-end swap is only a win once the matcher is held fixed). Reproducibility: pinned seeds and
  the one-command Gradle path recorded with each journey under `docs/testing/`.

### Binding axis and pre-registration (read before you measure)

- **Binding axis** — name the one metric that actually decides the product, not the convenient one. An
  always-on wake word is killed by false-fires per hour of ambient audio, not by per-utterance accuracy.
  Measuring the convenient axis produces confident, useless wins. For detection, always report error or
  miss-rate at a matched false-accept budget; a number without its operating point is not a result.
- **Pre-register one hypothesis.** Everything else tried is an exploratory family: report it in full, losing
  cells included, marked not banked, and never adopt a lever mined from it without a fresh, pre-registered,
  operating-point-matched confirmation. Reporting the best of many variants is selection-on-test.
- **Extreme operating points are high-variance.** A metric read at a single threshold at a curve extreme is
  pinned by the one or two hardest items; replicate across at least two speakers or folds before headlining.

## Evidence classification

Label every technical statement as exactly one of: **Fact, Measurement, Derived Result, Inference, Assumption,
Hypothesis, Speculation, Open Question.** Facts require supporting evidence; Measurements require a reproducible
experiment; Derived Results require a reproducible computation; everything else is labelled as what it is. Never
present an assumption as a fact. In practice, tag each number as measured (banked), directional (a bound, for
example cross-speaker or out-of-regime), or inferred — the same discipline already applied in the CP-2 journey
notes under `docs/testing/`.

## Scope-change log

Record every deliberate change to the four levels above. A moved goalpost that is not logged is
indistinguishable from cherry-picking.

| Date | Level changed | From then to | Why |
| --- | --- | --- | --- |
| 2026-07-08 | initial | none then baseline | First codification of the scope taxonomy for this repo. |
