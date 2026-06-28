plugins {
    alias(libs.plugins.speechangel.android.library)
    alias(libs.plugins.speechangel.android.hilt)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.speechangel.data"
}

dependencies {
    api(projects.core.enrollment)
    implementation(projects.core.model)
    implementation(projects.core.dsp)
    implementation(projects.core.matching)

    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)

    implementation(libs.datastore.preferences)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(libs.junit)
    testImplementation(libs.truth)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.robolectric)
}
