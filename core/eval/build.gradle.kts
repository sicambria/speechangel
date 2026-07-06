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
// Add `-Dtorgo.grid=true` to also run the (expensive) front-end bake-off grid.
// Absent the props the test skips (JUnit Assume) and `:core:eval:test` stays green with no corpus.
// `-Dtorgo.reject=true` runs the realistic-condition simulation + common-mode rejection adjudication
// (`-Dtorgo.conditions=true` adds the noise/reverb grid; `-Dambient.wav=<file>` swaps a real ambient
// recording for the synthetic proxy; `-Dtorgo.sim.report=<file>` sets the output path).
tasks.withType<Test>().configureEach {
    // The real-corpus evals (TORGO, Picovoice) hold multi-minute 16 kHz audio streams in memory.
    maxHeapSize = "2g"
    listOf(
        "torgo.dir",
        "torgo.report",
        "torgo.grid",
        "torgo.frontend",
        "torgo.reject",
        "torgo.conditions",
        "torgo.sim.report",
        "ambient.wav",
        // Picovoice wake-word-benchmark placement (`PicovoiceBenchmarkTest`):
        // `-Dpicovoice.dir=<root>` runs it; `-Dpicovoice.report=<file>` sets the output; optional
        // `-Dpicovoice.bgSeconds` / `-Dpicovoice.enroll` / `-Dpicovoice.held` / `-Dpicovoice.dump=<dir>`.
        "picovoice.dir",
        "picovoice.report",
        "picovoice.bgSeconds",
        "picovoice.enroll",
        "picovoice.held",
        "picovoice.dump",
    ).forEach { key ->
        providers.systemProperty(key).orNull?.let { systemProperty(key, it) }
    }
}
