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

// Forward the real-corpus opt-in props to the test JVM so `TorgoEvalTest` can run the TORGO
// evaluation on demand: `./gradlew :core:eval:test -Dtorgo.dir=<root> -Dtorgo.report=<file>`.
// Absent the props the test skips (JUnit Assume) and `:core:eval:test` stays green with no corpus.
tasks.withType<Test>().configureEach {
    listOf("torgo.dir", "torgo.report").forEach { key ->
        providers.systemProperty(key).orNull?.let { systemProperty(key, it) }
    }
}
