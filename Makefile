# SpeechAngel — scripted, reproducible task runner.
# Pins JDK 21 (AGP-supported) and the local Android SDK; override on the command line if needed.

JAVA_HOME ?= /usr/lib/jvm/java-21-openjdk-amd64
ANDROID_HOME ?= $(HOME)/Android/Sdk
GRADLE := JAVA_HOME=$(JAVA_HOME) ANDROID_HOME=$(ANDROID_HOME) ./gradlew
NODE ?= node
AVD ?= changemappers-test

# Picovoice wake-word benchmark. PV_DIR holds the (uncommitted, [measure-only]) corpus.
PV_DIR ?= $(HOME)/picovoice-benchmark
PV_REPORT ?= build/picovoice-report.md
# Optional experiment-sweep overrides. Each UNSET ⇒ the PicovoiceBenchmark ctor default that produced
# the committed report, so `make bench-picovoice` with no overrides is byte-reproducible. EVAL-003: a
# swept variant is an exploratory, NOT-banked family — never a headline FRR/FAR win on its own.
PV_OVERRIDES := \
  $(if $(FRONTEND),-Dpicovoice.frontend=$(FRONTEND)) \
  $(if $(DELTA),-Dpicovoice.deltaOrder=$(DELTA)) \
  $(if $(SNR),-Dpicovoice.snrDb=$(SNR)) \
  $(if $(WINDOW),-Dpicovoice.windowMs=$(WINDOW)) \
  $(if $(HOP),-Dpicovoice.hopMs=$(HOP)) \
  $(if $(TARGETFA),-Dpicovoice.targetFaPerHour=$(TARGETFA))

# Automated SOTA scorecard — measured performance mapped to the 15-domain 0–1000 band ladder
# (DomainBands). TORGO is present at $(HOME)/torgo on the dev host. SOTA_SSL holds the optional
# torch-backed D8/D9 metrics; SOTA_PY is a python with torch+transformers (default python3 has neither —
# point it at a venv, e.g. SOTA_PY=$(HOME)/torch-venv/bin/python; SSL weights are cached, CPU is fine).
TORGO_DIR ?= $(HOME)/torgo
SOTA_REPORT ?= build/sota-scorecard.md
SOTA_JSON ?= build/sota-score.json
# Absolute: written by sota-score-ssl (make's cwd = repo root) but read by the :core:eval test whose
# working dir is the module dir — a relative path would not resolve in both.
SOTA_SSL ?= $(CURDIR)/core/eval/build/sota-metrics-ssl.txt
SOTA_PY ?= python3

.DEFAULT_GOAL := help

.PHONY: help install-deps setup build assemble test static format verify guardrails emulator roadmap clean ci \
	bench-picovoice-fetch bench-picovoice bench-picovoice-smoke bench-picovoice-anchor \
	sota-score sota-score-ssl sota-score-full

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install-deps: ## Install SDK components + emulator system image + dev AVD (idempotent)
	@ANDROID_HOME=$(ANDROID_HOME) ./scripts/setup/install-deps.sh

setup: ## Verify the build + run environment (JDK 21, SDK, Node, emulator) and write local.properties
	@ANDROID_HOME=$(ANDROID_HOME) ./scripts/setup/check-env.sh

build: assemble ## Alias for assemble

assemble: ## Build the debug APK
	$(GRADLE) :app:assembleDebug

test: ## Run all JVM unit tests
	$(GRADLE) test

static: ## Run detekt + spotless + Android lint
	$(GRADLE) detekt spotlessCheck :app:lintDebug

format: ## Auto-format all Kotlin (spotless)
	$(GRADLE) spotlessApply

verify: ## Full local gate: static analysis + lint + tests + debug build (mirrors CI)
	$(GRADLE) detekt spotlessCheck :app:lintDebug test :app:assembleDebug

guardrails: ## Run the AI-workflow guardrail verifiers
	$(NODE) scripts/audits/run-all.mjs

emulator: ## Boot the development AVD (override: make emulator AVD=<name>)
	$(ANDROID_HOME)/emulator/emulator -avd $(AVD)

bench-picovoice-fetch: ## Provision the Picovoice benchmark corpus into PV_DIR (open downloads, no key)
	@./scripts/eval/fetch-picovoice-benchmark.sh $(PV_DIR)

bench-picovoice: ## Run the Picovoice wake-word benchmark (no overrides ⇒ reproduces the committed report; sweep via FRONTEND=/DELTA=/SNR=/WINDOW=/HOP=/TARGETFA=)
	$(GRADLE) :core:eval:test --tests "*PicovoiceBenchmarkTest*" \
	  -Dpicovoice.dir=$(PV_DIR) \
	  -Dpicovoice.bgSeconds=$(or $(BG),900) \
	  -Dpicovoice.enroll=$(or $(ENROLL),10) \
	  -Dpicovoice.held=$(or $(HELD),40) \
	  -Dpicovoice.dump=$(PV_DIR)/mixed -Dpicovoice.report=$(PV_REPORT) $(PV_OVERRIDES)

bench-picovoice-smoke: ## Fast Picovoice run (bgSeconds=120) — does NOT match the committed report
	$(GRADLE) :core:eval:test --tests "*PicovoiceBenchmarkTest*" \
	  -Dpicovoice.dir=$(PV_DIR) -Dpicovoice.bgSeconds=120 \
	  -Dpicovoice.report=build/picovoice-report-smoke.md $(PV_OVERRIDES)

bench-picovoice-anchor: ## Same-host PocketSphinx anchor on the dumped streams (run bench-picovoice first)
	@./scripts/eval/run-pocketsphinx.sh $(PV_DIR)

sota-score: ## Automated SOTA scorecard — JVM domains vs TORGO → 0–1000 band map (no torch; folds in SOTA_SSL if present)
	$(GRADLE) :core:eval:test --tests "*SotaScorecardTest*" --rerun-tasks \
	  -Dtorgo.dir=$(TORGO_DIR) -Dsota.report=$(SOTA_REPORT) -Dsota.json=$(SOTA_JSON) \
	  $(if $(wildcard $(SOTA_SSL)),-Dsota.ssl=$(SOTA_SSL))

sota-score-ssl: ## Measure SSL domains D8 (dual-cascade) + D9 (ceiling) into SOTA_SSL (needs torch: SOTA_PY=<venv python>)
	@rm -f $(SOTA_SSL)
	@mkdir -p $(dir $(SOTA_SSL))
	PYTHONPATH=scripts/eval/ssl_frontend_spike $(SOTA_PY) scripts/eval/ssl_frontend_spike/sweep_ssl.py wavlm F01,F03,F04 --emit=$(SOTA_SSL)
	PYTHONPATH=scripts/eval/ssl_frontend_spike $(SOTA_PY) scripts/eval/ssl_frontend_spike/dual_cascade_verify.py F01,F03,F04 60 --emit=$(SOTA_SSL)

sota-score-full: sota-score-ssl sota-score ## Full SOTA scorecard incl. torch-backed D8/D9 (needs torch: SOTA_PY=<venv python>)

roadmap: ## Show the project roadmap
	@cat docs/ROADMAP.md

clean: ## Remove build outputs
	$(GRADLE) clean

ci: verify guardrails ## Everything CI runs, locally
