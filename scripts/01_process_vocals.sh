#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-configs/default.yaml}"

read_config() {
  local key="$1"
  python - "$CONFIG_PATH" "$key" <<'PY'
import sys, yaml
config_path, key = sys.argv[1], sys.argv[2]
with open(config_path, encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
cur = data
for part in key.split('.'):
    cur = cur[part]
print(cur)
PY
}

INPUT_WAV="$(read_config paths.input_wav)"
OUTPUT_DIR="$(read_config paths.output_dir)"
MODEL="$(read_config models.audio_separator_model)"
MODEL_DIR="$(read_config models.audio_separator_model_dir)"
RAW_VOCAL_NAME="$(read_config vocal_extraction.raw_vocal_name)"
FINAL_VOCAL_NAME="$(read_config vocal_extraction.final_vocal_name)"
MDX_OVERLAP="$(read_config vocal_extraction.mdx_overlap)"
THRESHOLD="$(read_config vocal_extraction.noise_gate_threshold)"
RANGE="$(read_config vocal_extraction.noise_gate_range)"
ATTACK="$(read_config vocal_extraction.noise_gate_attack_ms)"
RELEASE="$(read_config vocal_extraction.noise_gate_release_ms)"

mkdir -p "$OUTPUT_DIR"

echo "[1/2] Extracting vocals with audio-separator..."
audio-separator "$INPUT_WAV" \
  -m "$MODEL" \
  --model_file_dir "$MODEL_DIR" \
  --mdx_enable_denoise \
  --mdx_overlap "$MDX_OVERLAP" \
  --output_format WAV \
  --output_dir "$OUTPUT_DIR" \
  --custom_output_names "{\"Vocals\": \"$RAW_VOCAL_NAME\"}"

echo "[2/2] Applying FFmpeg noise gate..."
ffmpeg -y -i "$OUTPUT_DIR/${RAW_VOCAL_NAME}.wav" \
  -af "agate=threshold=${THRESHOLD}:range=${RANGE}:attack=${ATTACK}:release=${RELEASE}" \
  "$OUTPUT_DIR/$FINAL_VOCAL_NAME"

echo "Done: $OUTPUT_DIR/$FINAL_VOCAL_NAME"
