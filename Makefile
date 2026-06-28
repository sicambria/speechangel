# SpeechAngel — scripted, reproducible task runner.
# Pins JDK 21 (AGP-supported) and the local Android SDK; override on the command line if needed.

JAVA_HOME ?= /usr/lib/jvm/java-21-openjdk-amd64
ANDROID_HOME ?= $(HOME)/Android/Sdk
GRADLE := JAVA_HOME=$(JAVA_HOME) ANDROID_HOME=$(ANDROID_HOME) ./gradlew
NODE ?= node
AVD ?= changemappers-test

.DEFAULT_GOAL := help

.PHONY: help install-deps setup build assemble test static format verify guardrails emulator roadmap clean ci

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

roadmap: ## Show the project roadmap
	@cat docs/ROADMAP.md

clean: ## Remove build outputs
	$(GRADLE) clean

ci: verify guardrails ## Everything CI runs, locally
