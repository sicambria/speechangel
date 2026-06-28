// Root build. Declares plugin versions (apply false) and wires repo-wide quality tooling.
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.ksp) apply false
    alias(libs.plugins.hilt) apply false
    alias(libs.plugins.detekt)
    alias(libs.plugins.spotless)
    alias(libs.plugins.kover)
}

// Spotless (formatting) — applied to every subproject with Kotlin sources.
val ktlintVersion = libs.versions.ktlint.get()
val spotlessPluginId = libs.plugins.spotless.get().pluginId
subprojects {
    apply(plugin = spotlessPluginId)
    extensions.configure<com.diffplug.gradle.spotless.SpotlessExtension> {
        kotlin {
            target("src/**/*.kt")
            targetExclude("**/build/**")
            ktlint(ktlintVersion)
                .editorConfigOverride(
                    mapOf(
                        "ktlint_standard_no-wildcard-imports" to "disabled",
                        // Jetpack Compose uses PascalCase @Composable functions and theme vals.
                        "ktlint_standard_function-naming" to "disabled",
                        "ktlint_standard_property-naming" to "disabled",
                    ),
                )
            trimTrailingWhitespace()
            endWithNewline()
        }
        kotlinGradle {
            target("*.gradle.kts")
            ktlint(ktlintVersion)
        }
    }
}

// Detekt (static analysis) — repo-wide config + baseline.
detekt {
    buildUponDefaultConfig = true
    parallel = true
    config.setFrom(files("$rootDir/config/detekt/detekt.yml"))
    baseline = file("$rootDir/config/detekt/baseline.xml")
    source.setFrom(
        files(
            subprojects.map { "${it.projectDir}/src/main/kotlin" },
            subprojects.map { "${it.projectDir}/src/main/java" },
        ),
    )
}

// Coverage aggregation across modules.
dependencies {
    kover(project(":core:model"))
    kover(project(":core:dsp"))
    kover(project(":core:matching"))
    kover(project(":core:enrollment"))
}

kover {
    reports {
        total {
            verify {
                rule("Line coverage of core logic") {
                    minBound(70)
                }
            }
        }
    }
}
