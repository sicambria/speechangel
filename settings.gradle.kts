@file:Suppress("UnstableApiUsage")

pluginManagement {
    // Convention plugins live in a composite build for reuse across modules.
    includeBuild("build-logic")
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "speechangel"

enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")

include(":core:model")
include(":core:dsp")
include(":core:matching")
include(":core:enrollment")
include(":core:eval")
include(":data")
include(":app")
