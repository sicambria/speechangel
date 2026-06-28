#!/usr/bin/env bash
# install-deps.sh — idempotently install the Android SDK components, the emulator system image,
# and the development AVD that SpeechAngel's run tier needs. See docs/DEPENDENCIES.md.
#
# Safe to re-run: every step is guarded by a presence check and skipped if already satisfied.
# Does NOT install JDK/Node/apt packages (those are documented in docs/DEPENDENCIES.md and need
# sudo); does NOT touch /dev/kvm group membership (prints the one sudo line instead).
#
# Run: ./scripts/setup/install-deps.sh
set -euo pipefail

ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
PLATFORM="platforms;android-35"
BUILD_TOOLS="build-tools;35.0.0"
SYS_IMAGE="system-images;android-35;google_apis;x86_64"
AVD_NAME="changemappers-test"
AVD_DEVICE="pixel_6"

SDKM="${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager"
AVDM="${ANDROID_HOME}/cmdline-tools/latest/bin/avdmanager"

ok()   { printf '\033[32m✓ %s\033[0m\n' "$1"; }
warn() { printf '\033[33m! %s\033[0m\n' "$1"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$1"; exit 1; }
step() { printf '\033[36m• %s\033[0m\n' "$1"; }

echo "== SpeechAngel dependency install (ANDROID_HOME=${ANDROID_HOME}) =="

[ -x "$SDKM" ] || fail "sdkmanager not found at ${SDKM}. Install cmdline-tools;latest first (see docs/DEPENDENCIES.md)."

install_pkg() { # $1 = sdkmanager package, $2 = directory that proves it is present
  if [ -d "$2" ]; then
    ok "already present: $1"
  else
    step "installing: $1"
    yes | "$SDKM" "$1" >/dev/null
    ok "installed: $1"
  fi
}

install_pkg "platform-tools"  "${ANDROID_HOME}/platform-tools"
install_pkg "$PLATFORM"       "${ANDROID_HOME}/platforms/android-35"
install_pkg "$BUILD_TOOLS"    "${ANDROID_HOME}/build-tools/35.0.0"
install_pkg "emulator"        "${ANDROID_HOME}/emulator"
install_pkg "$SYS_IMAGE"      "${ANDROID_HOME}/system-images/android-35/google_apis/x86_64"

# --- AVD ---
if "${ANDROID_HOME}/emulator/emulator" -list-avds 2>/dev/null | grep -qx "$AVD_NAME"; then
  ok "already present: AVD ${AVD_NAME}"
elif [ -x "$AVDM" ]; then
  step "creating AVD: ${AVD_NAME}"
  echo "no" | "$AVDM" create avd --name "$AVD_NAME" --package "$SYS_IMAGE" --device "$AVD_DEVICE" >/dev/null
  ok "created AVD: ${AVD_NAME}"
else
  warn "avdmanager not found — create the AVD manually (see docs/DEPENDENCIES.md)."
fi

# --- KVM acceleration (informational; the only step that may need sudo) ---
if [ -e /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
  ok "KVM accessible (/dev/kvm rw)"
else
  warn "No rw access to /dev/kvm. For durable access run:  sudo usermod -aG kvm \"\$USER\"  (then re-login)."
fi

echo
ok "Done. Verify with: make setup   ·   Boot the emulator with: make emulator"
