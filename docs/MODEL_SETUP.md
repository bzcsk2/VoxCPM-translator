# Model setup

This repository does not include model weights. Keep all external models outside this Git repository and point `configs/local.yaml` to local paths.

## Required local downloads

| Component | Required for | Local path example | Config keys |
| --- | --- | --- | --- |
| Vocal separation ONNX model, for example `Kim_Vocal_2.onnx` | Stage 01 | `~/models/audio-separator/Kim_Vocal_2.onnx` | `models.audio_separator_model`, `models.audio_separator_model_dir` |
| VibeVoice source checkout containing the `vibevoice` Python package | Stage 02 | `~/repos/VibeVoice` | `models.vibevoice_repo` |
| VibeVoice-ASR model directory | Stage 02 | `~/models/VibeVoice-ASR` | `models.vibevoice_asr_path` |
| Qwen3-ASR model directory | Stage 02 | `~/models/Qwen3-ASR-1.7B` | `models.qwen_asr_path` |
| VoxCPM2 model directory | Stage 05 when `tts.backend: voxcpm` | `~/models/VoxCPM2` | `models.voxcpm_model_path` |
| LatentSync checkout, optional | Stage 07 | `~/repos/LatentSync` | `models.latentsync_dir` |

Recommended layout:

```text
~/repos/
  VibeVoice/
  LatentSync/

~/models/
  audio-separator/
    Kim_Vocal_2.onnx
  VibeVoice-ASR/
  Qwen3-ASR-1.7B/
  VoxCPM2/
```

## Local config example

```yaml
models:
  audio_separator_model: "Kim_Vocal_2.onnx"
  audio_separator_model_dir: "/home/you/models/audio-separator"
  vibevoice_repo: "/home/you/repos/VibeVoice"
  vibevoice_asr_path: "/home/you/models/VibeVoice-ASR"
  qwen_asr_path: "/home/you/models/Qwen3-ASR-1.7B"
  voxcpm_model_path: "/home/you/models/VoxCPM2"
  latentsync_dir: "/home/you/repos/LatentSync"
```

## VoxCPM backend contract

The repository does not hard-code a concrete VoxCPM runtime. `tts.backend: voxcpm` imports the adapter configured by `tts.voxcpm_adapter` and calls:

```python
from pathlib import Path

def generate_audio(segment: dict, output_path: Path, config: dict) -> None:
    ...
```

The function must write one WAV file to `output_path`. Start from `examples/voxcpm_adapter_template.py`, replace the placeholder loader and inference call, and make the adapter module importable from the environment that runs `scripts/05_generate_audio_chunks.py`.

## Verify local setup

Run:

```bash
python scripts/check_env.py --config configs/local.yaml
```

For a full run, fix failures for FFmpeg / FFprobe, input media, the audio-separator model file, VibeVoice source path, VibeVoice-ASR model directory, Qwen3-ASR model directory, and the selected TTS backend.

## Git hygiene

Do not commit model weights, private media, generated audio/video, `.env`, `configs/local.yaml`, or local diagnostics under `outputs/`.
