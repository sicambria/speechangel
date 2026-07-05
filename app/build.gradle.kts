import java.io.FileInputStream
import java.util.Properties

plugins {
    alias(libs.plugins.speechangel.android.application)
    alias(libs.plugins.speechangel.android.compose)
    alias(libs.plugins.speechangel.android.hilt)
    alias(libs.plugins.ksp)
}

// Release signing is sourced from a git-ignored keystore.properties (never committed). When it is
// absent — the default on CI and this host — the release build assembles UNSIGNED rather than failing
// configuration, so R8/shrink can still be verified without the human's keystore (Bucket C).
val keystorePropsFile = rootProject.file("keystore.properties")
val hasKeystore = keystorePropsFile.exists()
val keystoreProps =
    Properties().apply {
        if (hasKeystore) FileInputStream(keystorePropsFile).use { load(it) }
    }

android {
    namespace = "com.speechangel.app"

    defaultConfig {
        applicationId = "com.speechangel.app"
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (hasKeystore) {
            create("release") {
                storeFile = file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    lint {
        abortOnError = true
        warningsAsErrors = false
        // Dependency/AGP versions are deliberately pinned for reproducibility; don't nag.
        disable += setOf("GradleDependency", "AndroidGradlePluginVersion")
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Signed only when a keystore is supplied; otherwise an unsigned release APK is produced.
            signingConfig = if (hasKeystore) signingConfigs.getByName("release") else null
        }
    }
}

dependencies {
    implementation(projects.data)
    implementation(projects.core.model)
    implementation(projects.core.dsp)
    implementation(projects.core.matching)
    implementation(projects.core.enrollment)

    implementation(libs.androidx.core.ktx)
    implementation(libs.android.material)
    implementation(libs.bundles.lifecycle)
    implementation(libs.androidx.lifecycle.service)
    implementation(libs.hilt.navigation.compose)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(projects.core.dsp)
    testImplementation(projects.core.matching)
    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.turbine)
    testImplementation(libs.kotlinx.coroutines.test)

    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}
