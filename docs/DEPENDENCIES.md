# Dependencies

The complete host/system dependency manifest for building **and running** SpeechAngel. Gradle/JVM
artifact versions are **not** duplicated here — they live in `gradle/libs.versions.toml` (the single
source of truth, no dynamic versions). This file covers everything *above* Gradle: the OS-level
toolchain, the Android SDK components, and the emulator/KVM stack needed for on-device QA.

There are two tiers:

- **Build tier** — what `make build` / `make verify` / the `core:*` tests need. JDK 21 + the Android
  SDK platform. A CI runner needs only this tier.
- **Run tier** — what running the app on a virtual device needs *on top of* the build tier: the
  emulator binary, a system image, KVM hardware acceleration, and an AVD. Only needed for the
  on-device QA work in `docs/ROADMAP.md` (Phase 0 measurement, Phase 1 hands-free loop).

> Host quirk (recorded in `docs/errors/2026-06/2026-06-28_host-toolchain-jdk-and-shell-quirks.md`):
> the agent shell only resolves **absolute** binary paths. All commands below use absolute paths for
> that reason. See `CLAUDE.md` §1.

---

## Build tier

| Dependency | Required version | Purpose | Verify |
|---|---|---|---|
| OS | Ubuntu 26.04 (any modern Linux) | Host. | `cat /etc/os-release` |
| JDK | **21** (`java-21-openjdk-amd64`) | Gradle + AGP toolchain (Java 17 bytecode target). | `$JAVA_HOME/bin/java -version` |
| Android SDK platform | `platforms;android-35` | compileSdk 35. | dir `~/Android/Sdk/platforms/android-35` |
| Android build-tools | `build-tools;35.0.0` | aapt2, d8, zipalign. | dir `~/Android/Sdk/build-tools/35.0.0` |
| Android platform-tools | latest (`adb` 1.0.41+) | adb, device bridge. | `~/Android/Sdk/platform-tools/adb version` |
| SDK command-line tools | `cmdline-tools;latest` | `sdkmanager`, `avdmanager`. | `~/Android/Sdk/cmdline-tools/latest/bin/sdkmanager --version` |
| Node.js | **>= 24** (pinned by `.nvmrc`) | Runs the dependency-free workflow/guardrail scripts under `scripts/`. | `node --version` |
| Git | any | VCS + `.husky` hooks. | `git --version` |
| Gradle | 8.14.3 (via `./gradlew` wrapper) | Build. Never install system Gradle — use the wrapper. | `./gradlew --version` |

The pinned application toolchain (AGP 8.7.3 · Kotlin 2.0.21 · compileSdk 35 · minSdk 26) and every
library version are declared in `gradle/libs.versions.toml`. A "no dynamic versions" guardrail
(`scripts/audits/verify-no-dynamic-versions.mjs`) enforces that they stay pinned.

### Installing the build tier on a fresh host

```sh
# JDK 21 (Debian/Ubuntu)
sudo apt-get update && sudo apt-get install -y openjdk-21-jdk

# Node 24 — via nvm (matches .nvmrc); or distro/nodesource
nvm install 24 && nvm use 24

# Android SDK components (sdkmanager already present under cmdline-tools/latest)
export ANDROID_HOME="$HOME/Android/Sdk"
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" \
  "platform-tools" \
  "platforms;android-35" \
  "build-tools;35.0.0"
```

`scripts/setup/check-env.sh` (run via `make setup`) verifies this tier and writes `local.properties`.

---

## Run tier (emulator / on-device QA)

| Dependency | Required value on this host | Purpose | Verify |
|---|---|---|---|
| Emulator | `emulator` SDK package | Boots a virtual device. | `~/Android/Sdk/emulator/emulator -version` |
| System image | `system-images;android-35;google_apis;x86_64` | The OS image the AVD runs. | dir `~/Android/Sdk/system-images/android-35/google_apis/x86_64` |
| AVD | `changemappers-test` (android-35, google_apis, x86_64) | The virtual device definition. | `~/Android/Sdk/emulator/emulator -list-avds` |
| KVM acceleration | `/dev/kvm` readable+writable | Hardware-accelerated emulation (usable speed). | `~/Android/Sdk/emulator/emulator -accel-check` |

### KVM access — the one sudo dependency

The emulator needs read/write on `/dev/kvm`. On this host it is `root:kvm` with an **ACL** already
granting the user direct access (`user:<you>:rw-`), applied by `logind` for the active local seat —
so `-accel-check` already reports *"KVM (version 12) is installed and usable"* with **no sudo
required today**.

That ACL is seat-scoped: a headless / plain-SSH / no-seat-session login may not get it. The durable
fix (belt-and-suspenders) is permanent `kvm`-group membership:

```sh
sudo usermod -aG kvm "$USER"   # then log out/in (or: newgrp kvm)
```

On a host where `/dev/kvm` does not exist at all (KVM module not loaded / virtualization disabled in
BIOS), install the KVM stack first:

```sh
sudo apt-get install -y qemu-kvm cpu-checker
kvm-ok            # should report "KVM acceleration can be used"
```

### Installing the run tier on a fresh host

```sh
export ANDROID_HOME="$HOME/Android/Sdk"
SDKM="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
AVDM="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"

"$SDKM" "emulator" "system-images;android-35;google_apis;x86_64"
echo "no" | "$AVDM" create avd \
  --name changemappers-test \
  --package "system-images;android-35;google_apis;x86_64" \
  --device pixel_6
```

`scripts/setup/install-deps.sh` does the above idempotently (skips anything already present) and is
the recommended path. Booting an AVD: `make emulator`.

---

## Gradle / JVM artifact dependencies

**Not listed here on purpose.** The authoritative, version-pinned list of every library and plugin
is `gradle/libs.versions.toml`. Notable groups: AndroidX core + lifecycle, Jetpack Compose
(BOM-managed), Hilt (DI), Room + DataStore (persistence), Coroutines, and the test stack (JUnit,
Truth, Turbine, MockK, Robolectric). Quality plugins: detekt, Spotless/ktlint, Kover.

---

## Fresh-host bootstrap (summary)

```sh
git clone <repo> && cd speechangel
./scripts/setup/install-deps.sh   # SDK components + system image + AVD (idempotent)
make setup                         # verify build tier, write local.properties
make verify                        # detekt + spotless + unit tests + debug APK
make emulator                      # boot the AVD for on-device QA
```

> Verification status on this host (2026-06-28): build tier and run tier are **all present and
> KVM-accelerated**. `install-deps.sh` was exercised here only as an idempotent no-op (everything was
> already installed); its fresh-install paths are documented but not end-to-end tested on a bare host.
