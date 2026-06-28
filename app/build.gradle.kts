plugins {
    alias(libs.plugins.speechangel.android.application)
    alias(libs.plugins.speechangel.android.compose)
    alias(libs.plugins.speechangel.android.hilt)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.speechangel.app"

    defaultConfig {
        applicationId = "com.speechangel.app"
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
        }
        release {
            // R8 is intentionally deferred until device QA (see docs/ROADMAP.md).
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}

dependencies {
    implementation(projects.data)
    implementation(projects.core.model)
    implementation(projects.core.enrollment)

    implementation(libs.androidx.core.ktx)
    implementation(libs.android.material)
    implementation(libs.bundles.lifecycle)
    implementation(libs.androidx.lifecycle.service)
    implementation(libs.hilt.navigation.compose)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)

    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
}
