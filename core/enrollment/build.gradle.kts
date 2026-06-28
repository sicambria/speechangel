plugins {
    alias(libs.plugins.speechangel.kotlin.library)
}

dependencies {
    api(projects.core.model)
    implementation(projects.core.dsp)
    implementation(projects.core.matching)
    api(libs.kotlinx.coroutines.core)
}
