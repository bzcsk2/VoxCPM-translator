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

Used by `scripts/05_generate_audio_chunks.py` as the integration point for per-segment dubbed audio generation.

Config key:

```yaml
models:
  voxcpm_model_path: "/path/to/VoxCPM2"
```

The repository does not currently ship a full TTS implementation. Generate one WAV file per segment as `raw_<id>.wav` in `paths.dub_chunk_dir`, or add a backend adapter that produces that format.

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
