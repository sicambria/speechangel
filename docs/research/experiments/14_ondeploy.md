# Domain 14: On-Device Optimization & Mobile Deployment

**Goal:** Make neural encoder inference viable on Android at <50ms/utt latency, <5MB model size, <50MB RAM, with reliable always-on operation.

**Enabling OSS:** ONNX Runtime Mobile (MIT), TFLite (Apache-2.0), Qualcomm AI Engine Direct SDK, NCNN (BSD-3), MNN (Apache-2.0).

---

## E14-01: ONNX Runtime vs TFLite vs NCNN benchmark on Android
**Hypothesis:** Different inference engines have different performance profiles on Android. ONNX Runtime (with XNNPACK/NNAPI delegates) is fastest for Transformer models; TFLite is fastest for CNNs; NCNN is fastest on Qualcomm GPUs. A bake-off determines the best engine per model architecture.
**Score:** Impact=180 Feasibility=240 Constraints=200 Evidence=80 → **700 (A)**
**Description:** Export the best student encoder to ONNX, TFLite, and NCNN formats. Benchmark on Android emulator (x86_64) and physical device (arm64): (a) cold start latency, (b) warm inference latency, (c) memory usage, (d) APK size impact, (e) battery drain (via Android profiler).
**Expected outcome:** ONNX Runtime with XNNPACK: best for Transformers/Conformers (10-30ms). TFLite with XNNPACK: best for CNNs (8-20ms). NCNN: best on Snapdragon with GPU (5-15ms). Results inform architecture selection for shippable model.
**How to run:** Multi-engine Android benchmark harness.

## E14-02: Streaming audio capture latency measurement (end-to-end)
**Hypothesis:** The end-to-end latency (mic input → feature extraction → model inference → command determination) must be <500ms for acceptable UX. The dominant latency contributions need measurement to identify optimization targets.
**Score:** Impact=200 Feasibility=260 Constraints=200 Evidence=70 → **730 (A)**
**Description:** Instrument the full pipeline with `System.nanoTime()` markers: (a) audio buffer acquisition, (b) VAD, (c) MFCC/embedding extraction, (d) matching, (e) total. Measure on emulator and physical device at various CPU loads. Report breakdown.
**Expected outcome:** Audio capture dominates at ~50-100ms (Android AudioRecord buffer). MFCC: ~2-5ms. VAD: ~1-3ms. Embedding: ~10-30ms. Matching: ~5-50ms (depends on template count). Total: ~70-190ms. Below 500ms threshold.
**How to run:** Latency instrumentation in ListeningService + benchmark script.

## E14-03: Battery drain measurement under always-on operation
**Hypothesis:** The always-on loop (Stage-1 energy gate + wake word + occasional Stage-2) consumes 1-3%/hr on a modern phone. Measuring this with Android Battery Historian on a physical device validates the always-on claim.
**Score:** Impact=250 Feasibility=180 Constraints=200 Evidence=60 → **690 (B)**
**Description:** Run the full always-on stack on a physical device for 8+ hours. Use `dumpsys batterystats` / Battery Historian to measure: (a) % battery consumed per hour, (b) wake locks held, (c) CPU time per component, (d) partial wakelocks. Compare Stage-1-only vs Stage-1+Stage-2 vs idle.
**Expected outcome:** Stage-1 energy gate only: 0.5-1.5%/hr. Full stack: 1.5-3.5%/hr. Acceptable for a device that charges nightly. Wake locks account for <5% of drain (foreground service keeps CPU awake by design).
**How to run:** Device battery test + Battery Historian analysis.

## E14-04: Wake-lock minimization (audio buffer coalescing)
**Hypothesis:** The AudioRecord callback fires every 10-20ms (frame-shift granularity), causing frequent CPU wake-ups. Coalescing audio into larger chunks (e.g., process 150ms every 150ms instead of 10ms every 10ms) reduces wake-lock overhead by 80% while adding only 150ms latency.
**Score:** Impact=220 Feasibility=260 Constraints=200 Evidence=70 → **750 (A)**
**Description:** Modify AudioRecorder.stream() to batch frames into 150ms chunks before emission. Compare: (a) wake-lock count per hour, (b) CPU time, (c) battery drain, (d) command latency. Trade off wake efficiency vs responsiveness.
**Expected outcome:** Coalesced 150ms chunks reduce CPU wake-ups from ~3600/hr to ~240/hr (15× reduction), with battery saving of 0.5-1.5%/hr. Latency increases by <150ms (still acceptable).
**How to run:** Coalescing buffer in AndroidAudioRecorder + battery benchmark.

## E14-05: CPU affinity and thread priority tuning
**Hypothesis:** Pinning the audio capture thread to a little core (power-efficient) and the recognition thread to a big core (performance) with appropriate priorities reduces jitter and improves power efficiency vs letting the OS scheduler decide.
**Score:** Impact=140 Feasibility=200 Constraints=200 Evidence=60 → **600 (B)**
**Description:** Set audio thread affinity to `CPU0-3` (LITTLE cores) with `THREAD_PRIORITY_URGENT_AUDIO`. Set recognition thread to `CPU4-7` (big cores) with `THREAD_PRIORITY_DEFAULT`. Measure tail latency (p99) and battery vs default scheduling.
**Expected outcome:** p99 latency reduces by 20-40% (fewer scheduler migrations). Battery saving marginal (<0.3%/hr). Worth doing for latency consistency more than battery.
**How to run:** Thread affinity via `Process.setThreadPriority()` + benchmark.

## E14-06: Model warm-up and pre-allocation
**Hypothesis:** The first inference after model load is 3-5× slower than subsequent inferences due to JIT compilation, memory allocation, and cache warming. Pre-warming the encoder with a dummy input at service startup eliminates cold-start latency spikes.
**Score:** Impact=120 Feasibility=280 Constraints=200 Evidence=80 → **680 (B)**
**Description:** After encoder model is loaded (at ListeningService.onCreate), run 3 dummy inferences with zero-filled audio. Measure inference latency for first real utterance vs 100th utterance. Compare with and without warm-up.
**Expected outcome:** Warm-up eliminates 2-5× latency spike on first real utterance. Cold start: 50-150ms → 10-30ms after warm-up. Standard practice for production ML services.
**How to run:** Warm-up logic in encoder initialization + latency benchmark.

## E14-07: Feature computation sharing (VAD + MFCC + Embedding)
**Hypothesis:** VAD, MFCC extraction, and encoder inference share overlapping computation (FFT for VAD, mel-filterbank for MFCC). Computing once and sharing intermediate results reduces total Stage-2 CPU time by 30-40%.
**Score:** Impact=200 Feasibility=220 Constraints=200 Evidence=70 → **690 (B)**
**Description:** Refactor pipeline to compute FFT once, share with VAD (energy in frequency bands) and MFCC (mel filterbank). Share mel energies between MFCC and embedding encoder (if encoder operates on mel features). Measure end-to-end speedup.
**Expected outcome:** 30-40% Stage-2 CPU reduction. FFT is ~40% of MFCC compute, mel filterbank ~20% — eliminating duplicate computation is a pure engineering win.
**How to run:** Shared FFT/mel computation in pipeline, benchmark.

## E14-08: Background degradation monitoring (Android Doze/App Standby)
**Hypothesis:** Android Doze and App Standby aggressively restrict background apps. SpeechAngel's assistant role + foreground service should be exempt — but on some OEMs (Xiaomi, Oppo), additional restrictions apply. Monitoring which restrictions activate in the field is critical for debugging always-on failures.
**Score:** Impact=180 Feasibility=220 Constraints=200 Evidence=60 → **660 (B)**
**Description:** Add telemetry: log when AudioRecord fails to read (silence gap), when service is killed, when CPU is throttled. Correlate with Android power management events (Doze entry, App Standby bucket change). Build a dashboard of "always-on survival" per OEM.
**Expected outcome:** Quantified survival rate per OEM. Xiaomi/Oppo: 60-80% survival without manual autostart setup. Stock Android/Pixel: >95% survival. Informs caregiver guidance per OEM.
**How to run:** Telemetry logging + per-OEM survival analysis.

## E14-09: Compressed feature storage (template size reduction)
**Hypothesis:** MFCC feature sequences stored as FloatArray blobs consume significant storage for multi-template enrollment (13 coeffs × 100 frames × 4 bytes × 3 templates × 50 commands ≈ 780 KB). LZ4 compression or 16-bit quantization reduces storage 2-4× with negligible DTW distance impact.
**Score:** Impact=140 Feasibility=260 Constraints=200 Evidence=70 → **670 (B)**
**Description:** Apply LZ4 compression or int16 quantization to stored feature sequences. Measure: (a) storage reduction ratio, (b) decompression latency, (c) DTW distance deviation from float32 reference. Choose scheme with <1% distance deviation.
**Expected outcome:** Int16 quantization: 2× reduction, <0.5% distance deviation. LZ4: 3-5× reduction, 0% deviation (lossless). Decompression latency <2ms.
**How to run:** Compression+quantization in FeatureCodec + distance fidelity benchmark.

## E14-10: Adaptive frame-rate based on CPU headroom
**Hypothesis:** When CPU is idle (phone on desk), process every 10ms frame for lowest latency. When CPU is busy (phone in use), skip every 2nd frame (20ms effective step) to reduce CPU contention. Adaptive frame rate maintains accuracy while being a good citizen.
**Score:** Impact=180 Feasibility=200 Constraints=200 Evidence=50 → **630 (B)**
**Description:** Monitor system CPU load via `/proc/stat`. When load >50%, increase frame step from 10ms to 20ms (fewer VAD/MFCC/DTW computations). Measure rank-1 degradation at 20ms step vs 10ms.
**Expected outcome:** 20ms step degrades rank-1 by 1-3pp but reduces CPU usage by 40%. Adaptive scheme achieves near-full accuracy during idle periods and gracefully degrades under load.
**How to run:** Adaptive frame-rate controller + CPU-load-conditioned eval.
