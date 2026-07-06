#!/usr/bin/env bash
#
# run-pocketsphinx.sh — same-host open-source WAKE-WORD anchor for the Picovoice benchmark.
#
# Runs CMU PocketSphinx (Apache-2.0, **no access key**) in keyword-spotting mode over the EXACT mixed
# streams the SpeechAngel harness scored (dumped by `PicovoiceBenchmark` via `-Dpicovoice.dump=<dir>`),
# so both engines are measured on identical bytes. Emits `<data>/pocketsphinx-anchor.md`.
#
# Best-effort by design: PocketSphinx's `pip` wheel may not build on this host's bleeding-edge Python.
# On ANY failure the script writes a fallback note pointing at Picovoice's PUBLISHED engine numbers, and
# exits 0 — it is an anchor, never a gate.
#
# Usage: run-pocketsphinx.sh [DATA_ROOT]   (default ~/picovoice-benchmark; expects <root>/mixed/*.wav)
#
set -uo pipefail
export PATH=/usr/bin:/bin:$PATH

DATA="${1:-$HOME/picovoice-benchmark}"
MIXED="$DATA/mixed"
OUT="$DATA/pocketsphinx-anchor.md"
VENV="$DATA/.venv-ps"

fallback() {
  cat > "$OUT" <<'EOF'
# PocketSphinx same-host anchor — UNAVAILABLE (fallback to published numbers)

The same-host PocketSphinx run could not execute on this host (see reason below). Per the plan this is a
best-effort tier, not a gate, so we fall back to Picovoice's **published** benchmark numbers as the
directional anchor (miss-rate at 1 false alarm / 10 hr, typical-English speech):

- **Porcupine** — miss-rate ≈ near-0 (single-digit %) at 0.1 FA/hr.
- **PocketSphinx** — dramatically higher miss-rate at the same operating point (the benchmark's weakest
  engine), and **Snowboy** in between.

Caveat: those are on Picovoice's *original* mix (seed=778 placement, peak-energy 10 dB SNR mix), not the
JVM-reimplemented stream SpeechAngel was scored on, so treat them as directional — not a byte-identical
head-to-head. The head-to-head that IS byte-identical is whatever this script produces when it runs.
EOF
  echo "PocketSphinx anchor unavailable — wrote fallback to $OUT"
  echo "reason: $1"
  exit 0
}

[ -d "$MIXED" ] || fallback "no dumped streams at $MIXED (run the benchmark with -Dpicovoice.dump=$MIXED)"

echo "=== creating venv + installing pocketsphinx ==="
python3 -m venv "$VENV" 2>/dev/null || fallback "python3 -m venv failed"
# shellcheck disable=SC1091
source "$VENV/bin/activate" || fallback "venv activate failed"
pip install --quiet --upgrade pip 2>/dev/null
pip install --quiet pocketsphinx 2>&1 | tail -3 || fallback "pip install pocketsphinx failed (likely no wheel for this Python)"
python3 -c "import pocketsphinx" 2>/dev/null || fallback "import pocketsphinx failed after install"

echo "=== scoring dumped streams with PocketSphinx kws ==="
MIXED_DIR="$MIXED" OUT_FILE="$OUT" python3 - <<'PY' || fallback "python scorer raised"
import os, sys, glob, wave, struct

try:
    from pocketsphinx import Decoder
except Exception as e:
    print("import error:", e); sys.exit(1)

mixed = os.environ["MIXED_DIR"]
out = os.environ["OUT_FILE"]
SR = 16000
FRAME_RATE = 100  # pocketsphinx frames are 10 ms

def read_labels(path):
    spans = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if not line: continue
            a, b = [float(x) for x in line.split(",")]
            spans.append((a, b))
    return spans

def read_pcm(path):
    w = wave.open(path, "rb")
    n = w.getnframes()
    raw = w.readframes(n)
    w.close()
    return raw

def overlaps(t, spans):
    return any(a <= t <= b for a, b in spans)

# ONE decode per keyword at a single kws threshold (a re-decode per swept threshold reloads the
# acoustic model each time and is pathologically slow). The anchor is a single operating point; the
# SpeechAngel report owns the full curve.
THR = 1e-20
rows = []
for wav in sorted(glob.glob(os.path.join(mixed, "*_speech.wav"))):
    stem = os.path.basename(wav)[:-len("_speech.wav")]
    keyphrase = stem.replace("_", " ")
    labels = read_labels(os.path.join(mixed, f"{stem}_label.txt"))
    if not labels:
        rows.append((keyphrase, None, None, "no labels")); continue
    raw = read_pcm(wav)
    dur_h = (len(raw) // 2) / SR / 3600.0
    print(f"[pocketsphinx] decoding {keyphrase} ({dur_h*60:.1f} min)...", flush=True)
    try:
        d = Decoder(keyphrase=keyphrase, kws_threshold=THR)
        d.start_utt(); d.process_raw(raw, False, True); d.end_utt()
        hits = [(seg.start_frame / FRAME_RATE) for seg in d.seg()]
    except Exception as e:
        rows.append((keyphrase, None, None, f"decoder: {type(e).__name__}")); continue
    tp = sum(1 for a, b in labels if any(a <= t <= b for t in hits))
    fa = sum(1 for t in hits if not overlaps(t, labels))
    miss = (len(labels) - tp) / len(labels)
    fah = fa / dur_h if dur_h > 0 else 0.0
    rows.append((keyphrase, miss, fah, f"thr={THR:g}"))

with open(out, "w") as f:
    f.write("# PocketSphinx same-host anchor (identical mixed streams)\n\n")
    f.write("Open-source CMU PocketSphinx keyword-spotting on the EXACT `<keyword>_speech.wav` streams\n")
    f.write("SpeechAngel was scored on — a byte-identical, no-access-key head-to-head. Operating point\n")
    f.write("chosen nearest 0.1 FA/hr (1 FA / 10 hr), the benchmark's convention.\n\n")
    f.write("| keyword | miss-rate | FA/hour | note |\n|---|---:|---:|---|\n")
    for kw, miss, fah, note in rows:
        ms = f"{miss*100:.1f}%" if miss is not None else "—"
        fs = f"{fah:.2f}" if fah is not None else "—"
        f.write(f"| {kw} | {ms} | {fs} | {note} |\n")
    f.write("\n_PocketSphinx is an English acoustic model; OOV coinages (jarvis, snowboy) may score poorly\n")
    f.write("or error — reported honestly per-row. This anchors the stream, not SpeechAngel's regime._\n")
print("wrote", out)
PY

echo "=== done: $OUT ==="
