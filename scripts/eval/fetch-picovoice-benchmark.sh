#!/usr/bin/env bash
#
# fetch-picovoice-benchmark.sh — provision the Picovoice wake-word-benchmark data for core:eval.
#
# Places everything under a data root (default ~/picovoice-benchmark) that the Kotlin harness reads via
#   ./gradlew :core:eval:test -Dpicovoice.dir=<root>
#
# All sources are OPEN downloads — no Picovoice access key, no Kaggle account:
#   * keyword recordings : github.com/Picovoice/wake-word-benchmark  (Apache-2.0, in-repo FLAC)
#   * background speech   : LibriSpeech test-clean                    (OpenSLR)
#   * environmental noise : DEMAND 16 kHz                            (Zenodo record 1227121)
#
# WavFile.kt cannot read FLAC, so every source is transcoded to 16 kHz mono signed-16 PCM WAV under
# <root>/prepared/. The script is idempotent: each stage skips when its output already exists.
#
# Layout produced:
#   <root>/prepared/audio/<keyword>/<n>.wav   keyword takes
#   <root>/prepared/librispeech/<id>.wav      flattened test-clean utterances (background + OOV)
#   <root>/prepared/noise/<ENV>.wav           DEMAND ch01 per environment
#
set -euo pipefail
export PATH=/usr/bin:/bin:$PATH

DATA="${1:-$HOME/picovoice-benchmark}"
JOBS="${JOBS:-8}"
PREP="$DATA/prepared"
mkdir -p "$DATA" "$PREP/audio" "$PREP/librispeech" "$PREP/noise"
cd "$DATA"

log() { printf '\n=== %s ===\n' "$*"; }

decode() { # decode <src> <dst-wav>  -> 16 kHz mono s16 (skip if present & non-empty)
  local src="$1" dst="$2"
  [ -s "$dst" ] && return 0
  ffmpeg -nostdin -loglevel error -y -i "$src" -ac 1 -ar 16000 -sample_fmt s16 "$dst"
}
# decode_dir <src-dir> <dst-dir>: transcode every .flac/.wav under src (recursively) to 16k mono s16.
# The Picovoice repo stores `alexa` takes as .flac but the other keywords as (arbitrary-rate) .wav,
# so we normalise on extension-agnostic basenames.
decode_dir() {
  local sdir="$1" ddir="$2"
  mkdir -p "$ddir"
  find "$sdir" -type f \( -iname '*.flac' -o -iname '*.wav' \) -print0 | \
    xargs -0 -P "$JOBS" -I{} bash -c 'f="{}"; b="$(basename "$f")"; decode "$f" "'"$ddir"'/${b%.*}.wav"'
}
export -f decode

# ---------------------------------------------------------------- 1. keyword recordings
log "Picovoice repo (keyword FLAC)"
if [ ! -d wake-word-benchmark ]; then
  git clone --depth 1 https://github.com/Picovoice/wake-word-benchmark.git
fi
for kwdir in wake-word-benchmark/audio/*/; do
  kw="$(basename "$kwdir")"
  decode_dir "$kwdir" "$PREP/audio/$kw"
  printf 'keyword %-14s %s takes\n' "$kw" "$(find "$PREP/audio/$kw" -name '*.wav' | wc -l)"
done

# ---------------------------------------------------------------- 2. LibriSpeech test-clean
log "LibriSpeech test-clean (background + OOV)"
if [ ! -f test-clean.tar.gz ]; then
  curl -fSL -o test-clean.tar.gz https://www.openslr.org/resources/12/test-clean.tar.gz
fi
if [ ! -d LibriSpeech/test-clean ]; then
  tar -xzf test-clean.tar.gz
fi
# Flatten every utterance to prepared/librispeech/<speaker>-<chapter>-<utt>.wav
find LibriSpeech/test-clean -name '*.flac' -print0 | \
  xargs -0 -P "$JOBS" -I{} bash -c 'f="{}"; decode "$f" "'"$PREP/librispeech"'/$(basename "${f%.flac}").wav"'
printf 'librispeech utterances: %s\n' "$(find "$PREP/librispeech" -name '*.wav' | wc -l)"

# ---------------------------------------------------------------- 3. DEMAND noise (16 kHz)
log "DEMAND noise (Zenodo, 16 kHz, ch01 per environment)"
ENVS="DKITCHEN DLIVING DWASHING NFIELD NPARK NRIVER OHALLWAY OMEETING OOFFICE \
PCAFETER PRESTO PSTATION SPSQUARE STRAFFIC TBUS TCAR TMETRO"
mkdir -p demand
for env in $ENVS; do
  out="$PREP/noise/$env.wav"
  [ -s "$out" ] && continue
  zip="demand/${env}_16k.zip"
  [ -f "$zip" ] || curl -fSL -o "$zip" "https://zenodo.org/api/records/1227121/files/${env}_16k.zip/content"
  # each zip contains <ENV>/ch01.wav .. ch16.wav — extract ch01 only
  unzip -o -j "$zip" "${env}/ch01.wav" -d "demand/$env" >/dev/null 2>&1 || unzip -o -j "$zip" "*ch01.wav" -d "demand/$env" >/dev/null
  ch01="$(find "demand/$env" -name 'ch01.wav' | head -1)"
  if [ -n "$ch01" ]; then decode "$ch01" "$out"; fi
done
printf 'noise environments: %s\n' "$(find "$PREP/noise" -name '*.wav' | wc -l)"

# ---------------------------------------------------------------- summary
log "DONE — data root: $DATA"
printf 'keywords:     %s\n' "$(find "$PREP/audio" -mindepth 1 -maxdepth 1 -type d | wc -l)"
printf 'keyword wavs: %s\n' "$(find "$PREP/audio" -name '*.wav' | wc -l)"
printf 'libri wavs:   %s\n' "$(find "$PREP/librispeech" -name '*.wav' | wc -l)"
printf 'noise wavs:   %s\n' "$(find "$PREP/noise" -name '*.wav' | wc -l)"
printf '\nRun the benchmark with:\n  ./gradlew :core:eval:test -Dpicovoice.dir=%s\n' "$DATA"
