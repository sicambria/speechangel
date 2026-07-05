# Release engineering

Scaffolding for an F-Droid + Play release. Everything here up to the account/keystore wall is in
place; the remaining steps are the human's (Bucket C).

## What is wired (autonomous)

- **Signing** — `app/build.gradle.kts` reads a git-ignored `keystore.properties` at the repo root. When
  it is absent (CI, this host) the release build assembles **unsigned** rather than failing; when
  present, the `release` build type is signed. The keystore, its passwords, and `keystore.properties`
  are never committed (`.gitignore` covers `*.jks`, `*.keystore`, `keystore.properties`).
- **Shrink** — the `release` build type sets `isMinifyEnabled` + `isShrinkResources`; keep rules live in
  `app/proguard-rules.pro`. `:app:assembleRelease` is verified green on this host (R8 exercised against
  the Room/Hilt/serialization reflection surface); `:app:assembleDebug` stays green.
- **Store metadata** — Play listing under the `fastlane` metadata tree
  (`fastlane/metadata/android/en-US/`); F-Droid recipe at `metadata/com.speechangel.app.yml`.

## What the human does (external, Bucket C)

1. **Generate a keystore** (once), then write `keystore.properties` (never commit it):

   ```sh
   keytool -genkeypair -v -keystore speechangel-release.jks \
     -keyalg RSA -keysize 4096 -validity 10000 -alias speechangel
   ```

   ```properties
   storeFile=/absolute/path/speechangel-release.jks
   storePassword=…
   keyAlias=speechangel
   keyPassword=…
   ```

2. **Play Console** — create the app, complete the mic Permission Declaration + Data safety form (the
   answers are in `docs/plans/2026-06/policy-and-path-a.md`), upload the signed AAB/APK.
3. **F-Droid** — fill the `SourceCode` / `IssueTracker` / `Repo` fields in the recipe once a public
   mirror exists, then submit the RFP to `fdroiddata`. Reproducibility holds: no proprietary deps,
   pinned versions (`gradle/libs.versions.toml`), deterministic build.

## Licensing

The app is AGPL-3.0 (`LICENSE`). Bundled third-party components are Apache-2.0 / MIT only; the in-app
list is `app/src/main/kotlin/com/speechangel/app/ui/policy/LicensesScreen.kt`.
