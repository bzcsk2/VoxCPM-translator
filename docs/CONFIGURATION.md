# Configuration guide

VoxCPM Translator is configured through YAML files. The repository intentionally separates committed templates from private local configuration because real runs depend on machine-specific paths, model weights, source media, and secrets.

## Config files

| File | Commit? | Purpose |
| --- | --- | --- |
| `configs/default.yaml` | Yes | Canonical schema-like default used by scripts when no `--config` is provided. It documents all supported sections and keys. |
| `configs/local.example.yaml` | Yes | User-facing template. Copy this to `configs/local.yaml` for real local runs. |
| `configs/local.yaml` | No | Private machine-specific config for your media, models, and output paths. Ignored by Git. |
| `configs/ci.yaml` | Yes | Placeholder config for tests and lightweight CI-style checks. It is not a runnable media-processing config. |

## Recommended setup

Start from the user-facing template, not from `configs/default.yaml`:

```bash
cp configs/local.example.yaml configs/local.yaml
```

Then edit `configs/local.yaml` and replace every `/home/you/...` value with a real path on your machine.

Use preflight before running stages:

```bash
python scripts/check_env.py --config configs/local.yaml
```

For orchestrated runs, gate execution with the same preflight checks:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

## Path policy

Keep these outside the repository:

- model weights and checkpoints
- upstream model repositories such as VibeVoice and LatentSync
- private input media
- generated audio and video
- `.env`
- `configs/local.yaml`

A clean local layout looks like this:

```text
~/repos/
  VibeVoice/
  LatentSync/                 # optional

~/models/
  audio-separator/
    Kim_Vocal_2.onnx
  VibeVoice-ASR/
  Qwen3-ASR-1.7B/
  VoxCPM2/

~/media/
  input.mp4
```

Your repository checkout should contain code, docs, templates, and small test fixtures only.

## Required sections

### `paths`

The `paths` section defines input media, intermediate artifacts, and final outputs. At minimum, a full run expects these keys to be configured:

```yaml
paths:
  input_video: "/home/you/media/input.mp4"
  input_wav: "outputs/input.wav"
  output_dir: "outputs"
  vocal_source_for_asr: "outputs/input_Vocals_Final_Gated.wav"
  instrumental_audio: "outputs/input_(Instrumental)_Kim_Vocal_2.wav"
  asr_json: "outputs/test_recognition_vibe.json"
  refined_json: "outputs/workflow_data_refined_vibe.json"
  dub_chunk_dir: "outputs/dub_chunks"
  temp_mixed_wav: "outputs/temp_full_audio.wav"
  final_video: "outputs/final_dubbing.mp4"
```

Relative paths are resolved from the current working directory. The recommended convention is to run scripts from the repository root.

### `models`

The `models` section should point to local external repositories and local model directories:

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

The repository does not redistribute these models or upstream repositories.

### `llm`

The translation stage uses an OpenAI-compatible chat-completions endpoint:

```yaml
llm:
  api_base: "https://integrate.api.nvidia.com/v1/chat/completions"
  model: "openai/gpt-oss-120b"
  api_key_env: "NVIDIA_API_KEY"
```

Put the actual key in `.env` or in your shell environment. Do not place real secrets inside YAML files that may be committed.

### `tts`

Start with manual mode unless your TTS backend is already ready:

```yaml
tts:
  backend: "manual"
```

Manual mode expects one WAV chunk per spoken segment under `paths.dub_chunk_dir`.

For a CLI backend:

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
```

For VoxCPM2:

```yaml
tts:
  backend: "voxcpm"
  voxcpm_adapter: "my_voxcpm_adapter"
  voxcpm_adapter_function: "generate_audio"
```

The adapter module must be importable from the current Python environment.

## Validation commands

Human-readable preflight:

```bash
python scripts/check_env.py --config configs/local.yaml
```

Machine-readable preflight:

```bash
python scripts/check_env.py --config configs/local.yaml --json
```

Pipeline dry run:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --dry-run
```

Pipeline status:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
```

See [PIPELINE_OPERATIONS.md](PIPELINE_OPERATIONS.md) for status, resume, skip, and manifest workflows.

## What not to do

Do not edit `configs/default.yaml` for private local paths. Use `configs/local.yaml` instead.

Do not commit `configs/local.yaml`, `.env`, model files, downloaded repositories, input media, generated audio, generated video, subtitles generated from private media, or stage output directories.
