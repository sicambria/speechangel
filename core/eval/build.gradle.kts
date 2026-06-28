plugins {
    alias(libs.plugins.speechangel.kotlin.library)
}

dependencies {
    // api: FeatureFrontEnd exposes MfccConfig; corpus exposes model types.
    api(projects.core.model)
    api(projects.core.dsp)
    implementation(projects.core.matching)
    implementation(projects.core.enrollment)
}
