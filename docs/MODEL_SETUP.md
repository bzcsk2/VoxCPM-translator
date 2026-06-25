# Model setup

This repository does not include model weights. You must download models from their official sources and follow their usage terms.

## Required models

### 1. Vocal separation model

Used by `audio-separator` in `scripts/01_process_vocals.sh`.

Config keys:

```yaml
models:
  audio_separator_model: "Kim_Vocal_2.onnx"
  audio_separator_model_dir: "/path/to/audio-separator-models"
```

### 2. VibeVoice-ASR

Used by `scripts/02_transcribe_vibe.py` for timestamped ASR and speaker IDs.

Config keys:

```yaml
models:
  vibevoice_repo: "/path/to/VibeVoice"
  vibevoice_asr_path: "/path/to/VibeVoice-ASR"
  qwen_asr_path: "/path/to/Qwen3-ASR-1.7B"
```

`vibevoice_repo` should be the local source repository path that exposes the `vibevoice` Python package imports used by the script.

### 3. Local audio generation backend

Used by `scripts/05_generate_audio_chunks.py` for per-segment dubbed audio generation or validation.

Config key:

```yaml
models:
  voxcpm_model_path: "/path/to/VoxCPM2"

tts:
  backend: "manual"
```

The repository does not redistribute a model-specific TTS implementation. Instead, it defines a stable file contract:

```text
paths.dub_chunk_dir/
  raw_0.wav
  raw_1.wav
  raw_2.wav
```

Each spoken segment in `paths.refined_json` must produce one WAV file named `raw_<id>.wav`. `dub_<id>.wav` is accepted for compatibility.

The default `manual` backend validates that required chunks exist. To connect a local model runner, use `custom_command`:

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
  overwrite: false
```

Available template variables:

```text
$id       segment id
$speaker  speaker label
$text     English dubbing line, falling back to zh_fixed/text_zh
$output   target raw_<id>.wav path
$start    segment start timestamp
$end      segment end timestamp
```

### 4. LatentSync, optional

Used by `scripts/07_latentsync_lipsync.py`.

Config key:

```yaml
models:
  latentsync_dir: "/path/to/LatentSync"
```

The LatentSync step is experimental. It may require separate dependency isolation because its torch / diffusers / CUDA requirements can conflict with the ASR or TTS environment.

## Recommended model storage

Do not store models inside this Git repository. Use a separate local directory, for example:

```text
~/models/
  audio-separator/
  VibeVoice-ASR/
  Qwen3-ASR-1.7B/
  VoxCPM2/
  LatentSync/
```

Then reference those paths from `configs/local.yaml`.
