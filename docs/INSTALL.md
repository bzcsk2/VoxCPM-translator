# Installation

This project is a research workflow rather than a packaged CLI. Install the runtime first, then point the config file to your local model directories.

For the shortest first-run path, start with [QUICKSTART_LOCAL.md](QUICKSTART_LOCAL.md). Configuration policy is in [CONFIGURATION.md](CONFIGURATION.md), and model weight details are in [MODEL_SETUP.md](MODEL_SETUP.md).

## 1. Clone

```bash
git clone https://github.com/bzcsk2/VoxCPM-translator.git
cd VoxCPM-translator
```

## 2. Create environment

```bash
conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements.txt
```

Install PyTorch according to your CUDA version. FFmpeg and FFprobe are required:

```bash
ffmpeg -version
ffprobe -version
```

Install `audio-separator` if you use `scripts/01_process_vocals.sh`:

```bash
pip install audio-separator
```

## 3. Prepare external models

Keep external repositories and model weights outside this repository. A recommended layout is:

```text
~/repos/
  VibeVoice/
  LatentSync/              # optional

~/models/
  audio-separator/
    Kim_Vocal_2.onnx
  VibeVoice-ASR/
  Qwen3-ASR-1.7B/
  VoxCPM2/
```

The full pipeline needs these local components:

| Component | Config key |
| --- | --- |
| Vocal separation ONNX model | `models.audio_separator_model`, `models.audio_separator_model_dir` |
| VibeVoice source checkout | `models.vibevoice_repo` |
| VibeVoice-ASR weights | `models.vibevoice_asr_path` |
| Qwen3-ASR weights | `models.qwen_asr_path` |
| VoxCPM2 weights or another local TTS backend | `models.voxcpm_model_path`, `tts.*` |
| LatentSync repo / weights, optional | `models.latentsync_dir` |

## 4. Configure

Copy the local template, not the canonical default file:

```bash
cp .env.example .env
cp configs/local.example.yaml configs/local.yaml
```

Edit `configs/local.yaml`:

```yaml
paths:
  input_video: "/home/you/media/input.mp4"
  input_wav: "outputs/input.wav"

models:
  audio_separator_model: "Kim_Vocal_2.onnx"
  audio_separator_model_dir: "/home/you/models/audio-separator"
  vibevoice_repo: "/home/you/repos/VibeVoice"
  vibevoice_asr_path: "/home/you/models/VibeVoice-ASR"
  qwen_asr_path: "/home/you/models/Qwen3-ASR-1.7B"
  voxcpm_model_path: "/home/you/models/VoxCPM2"
```

`configs/default.yaml` is the schema-like default used when no `--config` is provided. Keep private machine paths in `configs/local.yaml`, which is ignored by Git. See [CONFIGURATION.md](CONFIGURATION.md) for the full config-file policy.

Set the environment variable named by `llm.api_key_env` before running the translation stage. The default variable name is `NVIDIA_API_KEY`. Simple `KEY=VALUE` pairs in `.env` are loaded automatically by the Python scripts.

## 5. Choose a TTS backend

For an initial check, keep the manual backend and place pre-generated WAV chunks under `paths.dub_chunk_dir`:

```yaml
tts:
  backend: "manual"
```

For a local CLI-based TTS engine:

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
```

For VoxCPM2, install the upstream runtime and provide an adapter module:

```bash
pip install voxcpm
```

```yaml
tts:
  backend: "voxcpm"
  voxcpm_adapter: "my_voxcpm_adapter"
  voxcpm_adapter_function: "generate_audio"
```

The repository includes only a starting template at `examples/voxcpm_adapter_template.py`; copy it and replace the loader / inference call with the VoxCPM API that works in your local environment.

## 6. Check environment

```bash
python scripts/check_env.py --config configs/local.yaml
```

This checks FFmpeg, FFprobe, optional `audio-separator`, required config values, input paths, model directories, the configured audio-separator model file, output directory creation, API-key presence, and TTS backend configuration. For `tts.backend: voxcpm`, it also checks `models.voxcpm_model_path` and whether `tts.voxcpm_adapter` is importable.

## 7. Run pipeline

Prefer the orchestrator with a preflight gate:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

Inspect status and resume after a partial run:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume --preflight
```

Manual stage execution is still available for debugging:

```bash
python scripts/00_extract_audio.py --config configs/local.yaml
bash scripts/01_process_vocals.sh configs/local.yaml
python scripts/02_transcribe_vibe.py --config configs/local.yaml
python scripts/03_refine_and_translate.py --config configs/local.yaml
python scripts/04_verify_translation.py --config configs/local.yaml
python scripts/05_generate_audio_chunks.py --config configs/local.yaml
python scripts/06_assemble_final.py --config configs/local.yaml
```

Optional:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
python scripts/burn_subtitles.py --config configs/local.yaml
```

See [PIPELINE_OPERATIONS.md](PIPELINE_OPERATIONS.md) for dry-run, status, resume, skip, and stage manifest workflows.
