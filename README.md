# VoxCPM Translator

Local-first AI dubbing pipeline for translating Chinese drama / video content into English dubbed video.

This project combines vocal extraction, ASR, LLM-based script correction, dubbing-oriented translation, VoxCPM2 zero-shot voice cloning, FFmpeg audio assembly, and optional LatentSync lip-sync.

> Status: research release. The pipeline has been run locally, but users must prepare model weights and local paths themselves.

## What it does

VoxCPM Translator turns a source video into an English dubbed video through a staged workflow:

1. Extract clean vocals and instrumental audio.
2. Transcribe Chinese speech with speaker IDs and timestamps.
3. Refine ASR text and translate it into dubbing-friendly English.
4. Verify that translated JSON still matches the ASR segment list.
5. Generate English voice clips with VoxCPM2 using the original voice segment as reference audio.
6. Assemble the final dubbed audio track and mux it with video.
7. Optionally run LatentSync for mouth-shape synchronization.
8. Optionally burn English subtitles.

The core design choice is **per-segment voice cloning**: each dialogue segment uses the original segment audio as the reference voice, instead of relying on traditional diarization and a fixed speaker library.

## Features

- Local-first pipeline; model weights are not bundled in this repository.
- Designed for Chinese drama / short-video dialogue.
- Context-aware ASR correction and dubbing translation.
- VoxCPM2 zero-shot voice cloning.
- Smart speed adjustment for generated clips before audio assembly.
- Optional ASS subtitle generation.
- Optional experimental LatentSync integration.

## Repository layout

```text
.
├── configs/
│   └── default.yaml
├── docs/
│   ├── INSTALL.md
│   ├── MODEL_SETUP.md
│   ├── TROUBLESHOOTING.md
│   └── LIPSYNC_DESIGN.md
├── examples/
│   └── sample_workflow_data.json
├── scripts/
│   ├── 01_process_vocals.sh
│   ├── 02_transcribe_vibe.py
│   ├── 03_refine_and_translate.py
│   ├── 03_kimi_refine_and_translate.py
│   ├── 04_verify_translation.py
│   ├── 05_voxcpm_tts.py
│   ├── 06_assemble_final.py
│   ├── 07_latentsync_lipsync.py
│   ├── burn_subtitles.py
│   └── common.py
├── .env.example
├── .gitignore
├── environment.yml
├── requirements.txt
└── LICENSE
```

## Requirements

Recommended environment:

- Linux
- Python 3.10+
- CUDA-capable GPU
- FFmpeg / FFprobe
- Conda or Mamba
- Local model weights
- NVIDIA API key or another OpenAI-compatible chat-completions endpoint

The pipeline expects you to prepare these models yourself:

- `Kim_Vocal_2.onnx` or another audio-separator-compatible vocal model
- `VibeVoice-ASR`
- `Qwen3-ASR-1.7B` or compatible tokenizer/model path required by your VibeVoice setup
- `VoxCPM2`
- Optional: `LatentSync`

This repository does **not** redistribute any model weights.

## Installation

```bash
git clone https://github.com/bzcsk2/VoxCPM-translater.git
cd VoxCPM-translater

conda env create -f environment.yml
conda activate voxcpm-translator

cp .env.example .env
cp configs/default.yaml configs/local.yaml
```

Then edit `configs/local.yaml` and set your local model paths and input files.

See [docs/INSTALL.md](docs/INSTALL.md) and [docs/MODEL_SETUP.md](docs/MODEL_SETUP.md) for details.

## Configuration

All local paths should live in `configs/local.yaml`. The default template intentionally uses placeholder paths:

```yaml
models:
  audio_separator_model_dir: "/path/to/audio-separator-models"
  vibevoice_asr_path: "/path/to/VibeVoice-ASR"
  qwen_asr_path: "/path/to/Qwen3-ASR-1.7B"
  voxcpm_model_path: "/path/to/VoxCPM2"
  latentsync_dir: "/path/to/LatentSync"
```

Do not commit `configs/local.yaml` if it contains private machine paths.

## Usage

Run the stages in order:

```bash
bash scripts/01_process_vocals.sh configs/local.yaml
python scripts/02_transcribe_vibe.py --config configs/local.yaml
python scripts/03_refine_and_translate.py --config configs/local.yaml
python scripts/04_verify_translation.py --config configs/local.yaml
python scripts/05_voxcpm_tts.py --config configs/local.yaml
python scripts/06_assemble_final.py --config configs/local.yaml
```

Optional:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
python scripts/burn_subtitles.py --config configs/local.yaml
```

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

MIT License. See [LICENSE](LICENSE).

## Disclaimer

This project is for research, learning, and lawful content processing. Users are responsible for respecting copyright, likeness rights, voice rights, platform terms, model licenses, and content redistribution rules.
