# Release engineering

Scaffolding for an F-Droid + Play release. Everything here up to the account/keystore/tag-push wall
is in place; the remaining steps are the human's (Bucket C).

## What is wired (autonomous)

- **Signing** — `app/build.gradle.kts` reads a git-ignored `keystore.properties` at the repo root. When
  it is absent (CI, this host) the release build assembles **unsigned** rather than failing; when
  present, the `release` build type is signed. The keystore, its passwords, and `keystore.properties`
  are never committed (`.gitignore` covers `*.jks`, `*.keystore`, `keystore.properties`).
  **This signing config is for the Play upload only.** F-Droid builds and signs the APK itself on its
  own build server — no keystore is needed (or wanted) for the F-Droid path.
- **Shrink** — the `release` build type sets `isMinifyEnabled` + `isShrinkResources`; keep rules live in
  `app/proguard-rules.pro`. `:app:assembleRelease` is verified green on this host (R8 exercised against
  the Room/Hilt/serialization reflection surface); `:app:assembleDebug` stays green.
- **Store metadata** — Play listing under the `fastlane` metadata tree
  (`fastlane/metadata/android/en-US/`), now including 3 phone screenshots (reused from the
  2026-07-06 on-device run: `docs/testing/2026-07-06_on-device-{home,try,mic}.png`); F-Droid recipe at
  `metadata/com.speechangel.app.yml`.
- **Public mirror** — `origin` (`https://github.com/sicambria/speechangel`) is a **public** GitHub repo
  (verified via `gh repo view`), so the recipe's `SourceCode` / `IssueTracker` / `Repo` fields are now
  filled in (2026-07-06) rather than commented out.
- **No proprietary deps / no network anti-feature** — `AndroidManifest.xml` requests no `INTERNET`
  permission at all (RECORD_AUDIO, FOREGROUND_SERVICE[_MICROPHONE], POST_NOTIFICATIONS,
  RECEIVE_BOOT_COMPLETED only); `settings.gradle.kts` only resolves `google()` / `mavenCentral()` — no
  JitPack or other repos F-Droid's build server can't reach. No Firebase/GMS/Crashlytics/ads/analytics
  anywhere in `gradle/libs.versions.toml`. This is a fully offline app — no anti-features apply.

## F-Droid publish checklist (current gap, 2026-07-06)

| Step | Status |
|---|---|
| OSI license (AGPL-3.0-only) | ✅ done |
| No proprietary deps / no network anti-feature | ✅ done (verified above) |
| Public source repo | ✅ done — `github.com/sicambria/speechangel` is public |
| `metadata/com.speechangel.app.yml` recipe (Categories, License, Builds, repo fields) | ✅ done |
| Fastlane description + changelog | ✅ done |
| ≥1 phone screenshot | ✅ done (3 added) |
| `:app:assembleRelease` builds clean from the declared `subdir: app` | ✅ verified green |
| **`v0.1.0` git tag exists on the public remote** | ❌ **blocking** — no tag exists yet locally or on `origin`, and local `main` is currently 8 commits ahead of `origin/main` (unpushed). The recipe's `Builds[0].commit: v0.1.0` needs an actual tag F-Droid's build server can check out. |
| Push local `main` + the tag to `origin` | ❌ human call — pushing to the public remote/tag is a one-way, visible action; not done without explicit go-ahead |
| Submit the RFP (Request For Packaging) | ❌ human call — open an issue/MR against `fdroiddata` (via F-Droid's "Add new app" flow) pointing at the recipe; needs a GitLab account |
| Keystore + Play Console listing | ❌ human call (Play only — **not** required for F-Droid) |

## What the human does next (external, Bucket C)

1. **Push the release.** `git push origin main`, then `git tag v0.1.0 <commit>` and `git push origin
   v0.1.0` — pick the commit that actually matches `versionCode 1` / `versionName 0.1.0` in
   `app/build.gradle.kts`.
2. **Submit to F-Droid.** Use the recipe at `metadata/com.speechangel.app.yml` (now fully filled in)
   via F-Droid's "Add new app" wizard or a merge request to `fdroiddata`. No signing key needed —
   F-Droid signs it with its own key.
3. **Play Console (separate, optional path)** — generate a keystore (once), write
   `keystore.properties` (never commit it):

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

   Then create the app in Play Console, complete the mic Permission Declaration + Data safety form
   (answers are in `docs/plans/2026-06/policy-and-path-a.md`), and upload the signed AAB/APK.

## Licensing

The app is AGPL-3.0 (`LICENSE`). Bundled third-party components are Apache-2.0 / MIT only; the in-app
list is `app/src/main/kotlin/com/speechangel/app/ui/policy/LicensesScreen.kt`.
