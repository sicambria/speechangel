"""Benchmark microWakeWord models on Picovoice wake-word-benchmark mixed streams.

Measures: FRR (miss rate), FA/hr (false accepts per hour of audio).
Uses ESPHome microWakeWord .tflite models with pymicro-features frontend.

Usage:
    python bench_microWakeWord.py [--keyword alexa] [--model-dir /path/to/models]

Requires: pymicro-features, ai-edge-litert, numpy, scipy
Models from: https://github.com/esphome/micro-wake-word-models
Benchmark data: ~/picovoice-benchmark/mixed/
"""
import argparse, json, os, sys, time, wave
import numpy as np

SR = 16000
SAMPLES_PER_10MS = 160

# pymicro-features returns features as uint16 * FLOAT32_SCALE (1/25.6)
FLOAT32_SCALE = 0.0390625

# ESPHome exact quantization: int8 = round(feature_float * (256 / (FLOAT32_SCALE * 666))) - 128
# 256 / (FLOAT32_SCALE * 666) = 256 / (1/25.6 * 666) = 256 * 25.6 / 666 = 9.84024
ESP_QUANT_MULT = 256.0 / (FLOAT32_SCALE * 666)
ESP_QUANT_OFFSET = -128

# ESPHome dequantization: float_score = uint8_output / 255.0
# TFLite metadata: scale=0.00390625 (=1/256), zero_point=0
# Use ESPHome convention: uint8_out / 255.0
OUTPUT_DIVISOR = 255.0


def load_model(model_path):
    from ai_edge_litert.interpreter import Interpreter
    interp = Interpreter(model_path=model_path)
    interp.allocate_tensors()
    return interp


def read_wav(path):
    with wave.open(path, 'rb') as w:
        assert w.getframerate() == SR, f"Expected {SR} Hz, got {w.getframerate()}"
        assert w.getnchannels() == 1
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2')
    return audio, w.getnframes() / SR


def read_labels(path):
    labels = []
    with open(path) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                labels.append((float(parts[0]), float(parts[1])))
    return labels


def extract_features(audio, mf, progress=False):
    """Stream audio through MicroFrontend, yielding feature slices (40-dim float32)."""
    n_chunks = len(audio) // SAMPLES_PER_10MS
    for i in range(n_chunks):
        chunk = audio[i * SAMPLES_PER_10MS : (i + 1) * SAMPLES_PER_10MS]
        result = mf.process_samples(chunk.tobytes())
        if result.features:
            yield i * SAMPLES_PER_10MS / SR, np.array(result.features, dtype=np.float32)
        if progress and i % 16000 == 0:
            sys.stderr.write(f"\r  features: {i}/{n_chunks}")
    if progress:
        sys.stderr.write(f"\r  features: {n_chunks}/{n_chunks}\n")


def quantize_features(feats_slice):
    """Quantize float32 features to int8 using ESPHome exact formula.
    
    pymicro-features returns: feature_float = uint16 * FLOAT32_SCALE
    ESPHome quantizes: int8 = (uint16 * 256) / 666 - 128
                     = feature_float * (256 / (FLOAT32_SCALE * 666)) - 128
    """
    scaled = feats_slice * ESP_QUANT_MULT
    return np.clip(np.round(scaled) + ESP_QUANT_OFFSET, -128, 127).astype(np.int8)


def dequantize_output(raw_val):
    """Dequantize uint8 model output to float [0, 1] using ESPHome formula.
    ESPHome: float_score = uint8_output / 255.0
    """
    return int(raw_val) / OUTPUT_DIVISOR


def run_inference(interpreter, feats_window):
    """Run single inference on a window of feature slices. Returns float score [0,1]."""
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    input_slices = inp['shape'][1]  # 3

    if len(feats_window) < input_slices:
        return None

    latest = feats_window[-input_slices:]
    stacked = np.stack(latest)  # [3, 40]
    quantized = quantize_features(stacked)  # [3, 40]
    interpreter.set_tensor(inp['index'], quantized.reshape(inp['shape']))
    interpreter.invoke()
    raw = interpreter.get_tensor(out['index'])[0][0]
    return dequantize_output(raw)


def apply_sliding_window(scores, timestamps, window_size=5):
    """Apply sliding window voting: detection only if window_size consecutive scores > 0."""
    detections = []
    for i in range(window_size - 1, len(scores)):
        window = scores[i - window_size + 1: i + 1]
        if all(s > 0 for s in window):
            score = float(np.mean(window))
            t = timestamps[i]
            detections.append((t, score))
    return detections


def deduplicate_detections(detections, cooldown_sec=1.0):
    """Merge detections within cooldown_sec, keeping highest score."""
    if not detections:
        return []
    deduped = []
    current = detections[0]
    for det in detections[1:]:
        if det[0] - current[0] < cooldown_sec:
            if det[1] > current[1]:
                current = det
        else:
            deduped.append(current)
            current = det
    deduped.append(current)
    return deduped


def match_detections(detections, labels, tolerance_sec=1.5):
    """Match detections to ground truth labels.

    Each label can match at most one detection (the closest in time).
    Returns: (matched_hits, missed_labels, false_accepts)
    """
    used = set()
    hits = 0
    missed = 0

    for label_start, label_end in labels:
        best_dist = float('inf')
        best_idx = None
        for i, (det_t, det_score) in enumerate(detections):
            if i in used:
                continue
            # Detection must be within label bounds +/- tolerance
            if label_start - tolerance_sec <= det_t <= label_end + tolerance_sec:
                dist = abs(det_t - (label_start + label_end) / 2)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i
        if best_idx is not None:
            used.add(best_idx)
            hits += 1
        else:
            missed += 1

    false_accepts = len(detections) - hits
    return hits, missed, false_accepts


def benchmark_keyword(model_path, model_config, mixed_dir, keyword):
    """Run full benchmark for one keyword."""
    wav_path = os.path.join(mixed_dir, f"{keyword}_speech.wav")
    label_path = os.path.join(mixed_dir, f"{keyword}_label.txt")

    if not os.path.exists(wav_path) or not os.path.exists(label_path):
        print(f"  SKIP: no data for '{keyword}'")
        return None

    print(f"\n{'='*60}")
    print(f"Benchmarking: {keyword} ({model_config.get('wake_word', '?')})")
    print(f"{'='*60}")

    t0 = time.time()

    # Load
    audio, duration_sec = read_wav(wav_path)
    labels = read_labels(label_path)
    hours = duration_sec / 3600.0
    print(f"  audio: {duration_sec:.1f}s ({hours:.2f}h), labels: {len(labels)}")

    interpreter = load_model(model_path)
    cutoff = model_config['micro']['probability_cutoff']
    sw_size = model_config['micro']['sliding_window_size']

    # Extract features
    import pymicro_features as pmf
    mf = pmf.MicroFrontend()
    feats_list = list(extract_features(audio, mf, progress=True))
    print(f"  features: {len(feats_list)} slices ({time.time() - t0:.0f}s)")

    t_inf = time.time()

    # Run inference sliding window
    inp_shape = interpreter.get_input_details()[0]['shape']
    input_slices = inp_shape[1]  # 3
    scores = []
    timestamps = []
    feats_buffer = []

    for ts, feats in feats_list:
        feats_buffer.append(feats)
        if len(feats_buffer) >= input_slices:
            score = run_inference(interpreter, feats_buffer)
            if score is not None:
                scores.append(score)
                timestamps.append(ts)

    print(f"  inferences: {len(scores)} ({time.time() - t_inf:.0f}s)")

    # Apply threshold
    binary = [1 if s >= cutoff else 0 for s in scores]
    print(f"  above cutoff ({cutoff}): {sum(binary)} / {len(binary)} ({sum(binary)/max(len(binary),1)*100:.2f}%)")

    # Sliding window voting
    detections = apply_sliding_window(binary, timestamps, sw_size)
    print(f"  after sliding window ({sw_size}): {len(detections)} detections")

    # Deduplicate
    detections = deduplicate_detections(detections)
    print(f"  after dedup: {len(detections)} detections")

    # Match against labels
    hits, missed, fas = match_detections(detections, labels)
    total_labels = len(labels)
    frr = missed / total_labels * 100 if total_labels > 0 else 0
    detection_rate = hits / total_labels * 100 if total_labels > 0 else 0
    fa_hr = fas / hours if hours > 0 else 0

    result = {
        'keyword': keyword,
        'wake_word': model_config.get('wake_word', '?'),
        'duration_sec': duration_sec,
        'hours': hours,
        'total_labels': total_labels,
        'hits': hits,
        'missed': missed,
        'false_accepts': fas,
        'frr_pct': frr,
        'detection_rate_pct': detection_rate,
        'fa_per_hour': fa_hr,
        'cutoff': cutoff,
        'sliding_window': sw_size,
        'inferences': len(scores),
        'above_cutoff_pct': sum(binary) / max(len(binary), 1) * 100,
        'time_sec': time.time() - t0,
    }

    print(f"  RESULTS: det={detection_rate:.1f}%  FRR={frr:.1f}%  FA/hr={fa_hr:.1f}  "
          f"({hits}/{total_labels} hits, {fas} fas, {hours:.2f}h)")

    return result


def sweep_threshold(model_path, model_config, mixed_dir, keyword):
    """Sweep threshold to find best FA/hr vs FRR operating point."""
    wav_path = os.path.join(mixed_dir, f"{keyword}_speech.wav")
    label_path = os.path.join(mixed_dir, f"{keyword}_label.txt")

    if not os.path.exists(wav_path):
        return None

    print(f"\n--- Sweeping thresholds for {keyword} ---")
    t0 = time.time()

    audio, duration_sec = read_wav(wav_path)
    labels = read_labels(label_path)
    hours = duration_sec / 3600.0
    total_labels = len(labels)

    interpreter = load_model(model_path)
    sw_size = model_config['micro']['sliding_window_size']

    import pymicro_features as pmf
    mf = pmf.MicroFrontend()
    feats_list = list(extract_features(audio, mf, progress=True))

    inp_shape = interpreter.get_input_details()[0]['shape']
    input_slices = inp_shape[1]
    scores = []
    timestamps = []
    feats_buffer = []

    for ts, feats in feats_list:
        feats_buffer.append(feats)
        if len(feats_buffer) >= input_slices:
            score = run_inference(interpreter, feats_buffer)
            if score is not None:
                scores.append(score)
                timestamps.append(ts)

    print(f"  {len(scores)} inferences ({time.time() - t0:.0f}s)")

    results = []
    for cutoff in np.linspace(0.1, 0.99, 30):
        binary = [1 if s >= cutoff else 0 for s in scores]
        detections = apply_sliding_window(binary, timestamps, sw_size)
        detections = deduplicate_detections(detections)
        hits, missed, fas = match_detections(detections, labels)
        frr = missed / total_labels * 100 if total_labels > 0 else 0
        fa_hr = fas / hours if hours > 0 else 0
        results.append((cutoff, frr, fa_hr, hits, missed, fas))

    # Find best FA/hr at each FRR level, and vice versa
    print(f"\n  {'Cutoff':>8s}  {'FRR%':>6s}  {'FA/hr':>8s}  {'Hits':>5s}  {'Miss':>5s}  {'FAs':>5s}")
    print(f"  {'-'*8}  {'-'*6}  {'-'*8}  {'-'*5}  {'-'*5}  {'-'*5}")
    for c, frr, fa_hr, hits, missed, fas in results:
        marker = ""
        if fa_hr <= 0.5:
            marker = " ★ ≤0.5"
        elif fa_hr <= 1.0:
            marker = " ● ≤1.0"
        elif fa_hr <= 5.0:
            marker = " ○ ≤5.0"
        print(f"  {c:8.3f}  {frr:6.1f}  {fa_hr:8.1f}  {hits:5d}  {missed:5d}  {fas:5d}{marker}")

    # Best at ≤0.5 FA/hr
    best_half = [r for r in results if r[2] <= 0.5]
    if best_half:
        best = min(best_half, key=lambda r: r[1])
        print(f"\n  Best @ ≤0.5 FA/hr: cutoff={best[0]:.3f}  FRR={best[1]:.1f}%  FA/hr={best[2]:.2f}  "
              f"({best[3]}/{total_labels} hits)")
    else:
        best_low = min(results, key=lambda r: r[2])
        print(f"\n  Best (FAILS ≤0.5 FA/hr): cutoff={best_low[0]:.3f}  FRR={best_low[1]:.1f}%  "
              f"FA/hr={best_low[2]:.1f}  ({best_low[3]}/{total_labels} hits)")

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark microWakeWord on Picovoice streams")
    parser.add_argument('--keyword', default=None, help='Specific keyword (alexa, jarvis, etc.)')
    parser.add_argument('--model-dir', default='/tmp/opencode/mww-models',
                       help='Directory with .tflite and .json model files')
    parser.add_argument('--mixed-dir', default=os.path.expanduser('~/picovoice-benchmark/mixed'),
                       help='Directory with *_speech.wav and *_label.txt files')
    parser.add_argument('--sweep', action='store_true', help='Sweep thresholds')
    args = parser.parse_args()

    # Keyword-to-model mapping
    keyword_map = {
        'alexa': 'alexa',
        'jarvis': 'hey_jarvis',
    }

    if args.keyword and args.keyword.lower() not in keyword_map:
        print(f"Error: unknown keyword '{args.keyword}'. Available: {list(keyword_map.keys())}")
        sys.exit(1)

    # Suppress TFLite logging
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

    keywords = [args.keyword] if args.keyword else sorted(keyword_map.keys())

    all_results = []
    for kw in keywords:
        model_name = keyword_map[kw]
        model_path = os.path.join(args.model_dir, f'{model_name}.tflite')
        config_path = os.path.join(args.model_dir, f'{model_name}.json')

        if not os.path.exists(model_path):
            print(f"ERROR: model not found: {model_path}")
            continue
        if not os.path.exists(config_path):
            print(f"ERROR: config not found: {config_path}")
            continue

        with open(config_path) as f:
            config = json.load(f)

        if args.sweep:
            sweep_threshold(model_path, config, args.mixed_dir, kw)
        else:
            result = benchmark_keyword(model_path, config, args.mixed_dir, kw)
            if result:
                all_results.append(result)

    if all_results:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"  {'Keyword':>12s}  {'Hours':>6s}  {'Labels':>6s}  {'FRR%':>6s}  {'FA/hr':>8s}  {'Time':>6s}")
        for r in all_results:
            print(f"  {r['keyword']:>12s}  {r['hours']:6.2f}  {r['total_labels']:6d}  "
                  f"{r['frr_pct']:6.1f}  {r['fa_per_hour']:8.1f}  {r['time_sec']:6.0f}s")


if __name__ == '__main__':
    main()
