# VoxCPM Translator

Local-first AI dubbing pipeline for translating Chinese drama / video content into English dubbed video.

This project combines audio extraction, vocal extraction, ASR, LLM-based script correction, dubbing-oriented translation, per-segment TTS adapter integration, FFmpeg audio assembly, and optional LatentSync lip-sync. The audio generation stage is implemented as a strict adapter boundary so users can connect their own local backend and comply with the licenses and permissions of their source material.

> Status: research release. Model weights are not bundled in this repository. Users must prepare local weights, external repositories, local paths, and runtime dependencies themselves.

## What it does

VoxCPM Translator turns a source video into an English dubbed video through a staged workflow:

1. Extract WAV audio from the input video.
2. Extract clean vocals and instrumental audio.
3. Transcribe Chinese speech with speaker IDs and timestamps.
4. Refine ASR text and translate it into dubbing-friendly English.
5. Verify that translated JSON still matches the ASR segment list.
6. Generate or validate per-segment audio chunks through a local backend adapter.
7. Assemble the final dubbed audio track and mux it with video.
8. Optionally run LatentSync for mouth-shape synchronization.
9. Optionally burn English subtitles.

The core design choice is **per-segment audio generation**: each dialogue segment maps to one output clip named `raw_<id>.wav`, so the assembly stage can align the generated audio to the original timestamps.

## Current capability matrix

| Area | Status |
| --- | --- |
| Video-to-WAV extraction | Implemented |
| Vocal / instrumental separation | Implemented through `audio-separator`; requires a local separator model such as `Kim_Vocal_2.onnx` |
| VibeVoice-ASR transcription | Implemented script; requires local VibeVoice source repo plus local ASR weights |
| LLM script correction and translation | Implemented for OpenAI-compatible chat-completions endpoints |
| Manual TTS chunk validation | Implemented |
| CLI-based TTS generation | Implemented through `tts.backend: custom_command` |
| VoxCPM / VoxCPM2 TTS | Adapter slot implemented; users must install VoxCPM and provide an importable adapter module |
| Audio assembly and video muxing | Implemented |
| LatentSync | Experimental optional integration |
| Fully reproducible public demo | Not included yet, because model weights and test media are external |

## Features

- Local-first pipeline; model weights are not bundled in this repository.
- Designed for Chinese drama / short-video dialogue.
- Context-aware ASR correction and dubbing translation.
- Per-segment audio chunk interface for local generation backends.
- Built-in backend modes: `manual`, `custom_command`, and `voxcpm` adapter.
- Smart speed adjustment for generated clips before audio assembly.
- Config and environment preflight checks.
- Resumable stage orchestration with output status inspection.
- Optional ASS subtitle generation.
- Optional experimental LatentSync integration.

## Local model requirements

The common local components are:

| Component | Required for | Config key |
| --- | --- | --- |
| Vocal separation model, for example `Kim_Vocal_2.onnx` | Stage 01 | `models.audio_separator_model`, `models.audio_separator_model_dir` |
| VibeVoice source repository | Stage 02 | `models.vibevoice_repo` |
| VibeVoice-ASR weights | Stage 02 | `models.vibevoice_asr_path` |
| Qwen3-ASR weights | Stage 02 | `models.qwen_asr_path` |
| VoxCPM2 weights or another local audio-generation backend | Stage 05 | `models.voxcpm_model_path`, `tts.*` |
| LatentSync repo / weights | Optional stage 07 | `models.latentsync_dir` |

Read [docs/QUICKSTART_LOCAL.md](docs/QUICKSTART_LOCAL.md) first for the concrete local directory layout and setup order. Configuration details are in [docs/CONFIGURATION.md](docs/CONFIGURATION.md), data contracts are in [docs/DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md), output stage details are in [docs/OUTPUT_STAGES.md](docs/OUTPUT_STAGES.md), development workflow is in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), installation details are in [docs/INSTALL.md](docs/INSTALL.md), model details are in [docs/MODEL_SETUP.md](docs/MODEL_SETUP.md), operational commands are in [docs/PIPELINE_OPERATIONS.md](docs/PIPELINE_OPERATIONS.md), and known-good environment notes are in [docs/KNOWN_GOOD_ENV.md](docs/KNOWN_GOOD_ENV.md).

This repository does **not** redistribute any model weights.

## Installation

```bash
git clone https://github.com/bzcsk2/VoxCPM-translator.git
cd VoxCPM-translator

conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements.txt

cp .env.example .env
cp configs/local.example.yaml configs/local.yaml
```

Then edit `configs/local.yaml` and set your local model paths and input files.

The scripts automatically load simple `KEY=VALUE` pairs from `.env` without overriding already exported environment variables.

Project maturity and planned improvements are tracked in [ROADMAP.md](ROADMAP.md).

## Configuration

Committed config files have separate roles:

| File | Purpose |
| --- | --- |
| `configs/default.yaml` | Canonical default / schema-like reference used when no `--config` is provided. |
| `configs/local.example.yaml` | User-facing template to copy into `configs/local.yaml`. |
| `configs/ci.yaml` | Placeholder config for tests and lightweight CI-style validation. |

All private local paths should live in `configs/local.yaml`, which is ignored by Git. Do not edit `configs/default.yaml` with machine-specific paths.

A typical local model section looks like this:

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

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the full configuration policy.

## Development checks

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the same lightweight check suite used by CI:

```bash
python scripts/dev_check.py
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for focused checks, CI policy, and full local validation.

## Usage

Run a preflight check first:

```bash
python scripts/check_env.py --config configs/local.yaml
```

Run stages through the orchestrator with a preflight gate:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

Inspect status before resuming:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume --preflight
```

Validate ASR / refined JSON alignment and TTS chunk coverage:

```bash
python scripts/validate_artifacts.py --config configs/local.yaml
```

You can still run stages manually when debugging:

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

See [docs/OUTPUT_STAGES.md](docs/OUTPUT_STAGES.md) for final assembly, LatentSync, and subtitle burn-in details.

## TTS backend contract

`paths.refined_json` contains one row per segment. The audio generation stage expects one WAV file per spoken segment in `paths.dub_chunk_dir`:

```text
raw_0.wav
raw_1.wav
raw_2.wav
```

Backend options:

```yaml
tts:
  backend: "manual"
```

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
```

```yaml
tts:
  backend: "voxcpm"
  voxcpm_adapter: "my_voxcpm_adapter"
  voxcpm_adapter_function: "generate_audio"
```

The `custom_command` backend supports `$id`, `$speaker`, `$text`, `$output`, `$start`, and `$end`. The `voxcpm` backend imports the configured adapter module and calls `generate_audio(segment, output_path, config)`.

The repository ships only an adapter template at `examples/voxcpm_adapter_template.py`. To use VoxCPM2 directly, install the upstream runtime and provide an adapter module that loads your local `models.voxcpm_model_path` and writes one WAV file per segment.

## Main outputs

Typical output files:

```text
outputs/test_recognition_vibe.json
outputs/workflow_data_refined_vibe.json
outputs/temp_full_audio.wav
outputs/final_dubbing.mp4
outputs/final_dubbing_lipsync.mp4
outputs/final_dubbing_subtitled.mp4
```

## Important notes

- Keep model weights outside the repository.
- Keep input videos, generated audio, and generated videos outside Git.
- Make sure you have the right to process, translate, dub, and redistribute your source material.
- The LatentSync step is experimental and GPU-memory-sensitive.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Contributions and security reporting are documented in [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Disclaimer

This project is for research, learning, and lawful content processing. Users are responsible for respecting copyright, likeness rights, voice rights, platform terms, model licenses, and content redistribution rules.
