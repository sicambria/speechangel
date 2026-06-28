#!/usr/bin/env bash
# Reproducible-environment precheck (meta Wave 0.5). Verifies the host can build SpeechAngel
# and records the working invocation. Run: ./scripts/setup/check-env.sh
set -euo pipefail

REQUIRED_JDK_MAJOR=21
DEFAULT_JDK="/usr/lib/jvm/java-${REQUIRED_JDK_MAJOR}-openjdk-amd64"
DEFAULT_SDK="${HOME}/Android/Sdk"

fail() { printf '\033[31m✗ %s\033[0m\n' "$1"; exit 1; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$1"; }
warn() { printf '\033[33m! %s\033[0m\n' "$1"; }

echo "== SpeechAngel environment check =="

# --- JDK 21 ---
JAVA_HOME="${JAVA_HOME:-$DEFAULT_JDK}"
if [ ! -x "${JAVA_HOME}/bin/java" ]; then
  fail "JDK ${REQUIRED_JDK_MAJOR} not found at JAVA_HOME=${JAVA_HOME}. Install temurin-${REQUIRED_JDK_MAJOR} or set JAVA_HOME."
fi
JAVA_VER="$("${JAVA_HOME}/bin/java" -version 2>&1 | head -1)"
case "$JAVA_VER" in
  *"\"${REQUIRED_JDK_MAJOR}"*) ok "JDK: ${JAVA_VER} (JAVA_HOME=${JAVA_HOME})" ;;
  *) warn "JDK is not ${REQUIRED_JDK_MAJOR}: ${JAVA_VER}. AGP supports 17-21; ${REQUIRED_JDK_MAJOR} is pinned." ;;
esac

# --- Android SDK ---
ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$DEFAULT_SDK}}"
if [ ! -d "${ANDROID_HOME}/platforms" ]; then
  fail "Android SDK not found at ANDROID_HOME=${ANDROID_HOME}. Install the SDK and platform android-35."
fi
ok "Android SDK: ${ANDROID_HOME}"
if [ ! -d "${ANDROID_HOME}/platforms/android-35" ]; then
  warn "Platform android-35 missing — install it via: sdkmanager 'platforms;android-35'"
fi

# --- Gradle wrapper ---
[ -f ./gradlew ] || fail "gradlew not found — run from the repo root."
ok "Gradle wrapper present"

# --- Node (workflow/guardrail scripts; >= 24 per .nvmrc) ---
if command -v node >/dev/null 2>&1; then
  NODE_VER="$(node --version 2>/dev/null || echo '?')"
  case "$NODE_VER" in
    v2[4-9]*|v[3-9][0-9]*) ok "Node: ${NODE_VER}" ;;
    *) warn "Node ${NODE_VER} < 24 (.nvmrc pins 24) — guardrail scripts may not run." ;;
  esac
else
  warn "node not found — the scripts/ guardrail + workflow gates need Node >= 24."
fi

# --- Build-tools + platform-tools (adb) ---
if [ -d "${ANDROID_HOME}/build-tools/35.0.0" ]; then
  ok "build-tools 35.0.0 present"
else
  warn "build-tools 35.0.0 missing — install: sdkmanager 'build-tools;35.0.0'"
fi
if [ -x "${ANDROID_HOME}/platform-tools/adb" ]; then
  ok "platform-tools (adb) present"
else
  warn "platform-tools (adb) missing — install: sdkmanager 'platform-tools'"
fi

# --- Run tier (emulator / on-device QA): advisory only; the build tier does not need these ---
EMU="${ANDROID_HOME}/emulator/emulator"
if [ -x "$EMU" ]; then
  ok "emulator binary present"
  if [ -d "${ANDROID_HOME}/system-images/android-35/google_apis/x86_64" ]; then
    ok "system image android-35;google_apis;x86_64 present"
  else
    warn "system image missing — install: sdkmanager 'system-images;android-35;google_apis;x86_64'"
  fi
  if "$EMU" -accel-check >/dev/null 2>&1; then
    ok "KVM acceleration usable"
  else
    warn "KVM acceleration unavailable — see docs/DEPENDENCIES.md 'KVM access'."
  fi
  if AVDS="$("$EMU" -list-avds 2>/dev/null)" && [ -n "$AVDS" ]; then
    ok "AVD(s) available: $(echo "$AVDS" | tr '\n' ' ')"
  else
    warn "no AVD — create one: ./scripts/setup/install-deps.sh (or see docs/DEPENDENCIES.md)."
  fi
else
  warn "emulator not installed — run tier (on-device QA) unavailable. See docs/DEPENDENCIES.md."
fi

# --- local.properties (AGP reads ANDROID_HOME if absent, but make it explicit & reproducible) ---
if [ ! -f local.properties ]; then
  echo "sdk.dir=${ANDROID_HOME}" > local.properties
  ok "Wrote local.properties (sdk.dir=${ANDROID_HOME})"
else
  ok "local.properties exists"
fi

echo
ok "Environment OK. Build with:  JAVA_HOME=${JAVA_HOME} ANDROID_HOME=${ANDROID_HOME} ./gradlew assembleDebug"
echo "   (or simply: make build)"
