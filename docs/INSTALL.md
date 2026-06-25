# Installation

This project is a research workflow rather than a packaged CLI. Install the runtime first, then point the config file to your local model directories.

## 1. Clone

```bash
git clone https://github.com/bzcsk2/VoxCPM-translater.git
cd VoxCPM-translater
```

## 2. Create environment

```bash
conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements.txt
```

PyTorch should be installed according to your CUDA version.

## 3. Install system dependencies

You need FFmpeg and FFprobe:

```bash
ffmpeg -version
ffprobe -version
```

You also need `audio-separator` if you use `scripts/01_process_vocals.sh`.

## 4. Configure

```bash
cp .env.example .env
cp configs/default.yaml configs/local.yaml
```

Edit `configs/local.yaml`:

```yaml
paths:
  input_video: "/path/to/input.mp4"
  input_wav: "outputs/input.wav"

models:
  audio_separator_model_dir: "/path/to/audio-separator-models"
  vibevoice_repo: "/path/to/VibeVoice"
  vibevoice_asr_path: "/path/to/VibeVoice-ASR"
  qwen_asr_path: "/path/to/Qwen3-ASR-1.7B"
  voxcpm_model_path: "/path/to/VoxCPM2"
```

Set your API key in `.env` or export it in your shell:

```bash
NVIDIA_API_KEY="your_key_here"
```

Simple `KEY=VALUE` pairs in `.env` are loaded automatically by the Python scripts. Already-exported environment variables take precedence over `.env` values.

## 5. Check environment

Run the preflight check before the full pipeline:

```bash
python scripts/check_env.py --config configs/local.yaml
```

This checks FFmpeg, FFprobe, optional `audio-separator`, API-key presence, input paths, model directories, output directory creation, and TTS backend configuration.

## 6. Run pipeline

```bash
python scripts/00_extract_audio.py --config configs/local.yaml
bash scripts/01_process_vocals.sh configs/local.yaml
python scripts/02_transcribe_vibe.py --config configs/local.yaml
python scripts/03_refine_and_translate.py --config configs/local.yaml
python scripts/04_verify_translation.py --config configs/local.yaml
python scripts/05_generate_audio_chunks.py --config configs/local.yaml
python scripts/06_assemble_final.py --config configs/local.yaml
```

Or use the lightweight orchestrator:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6
```

Optional:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
python scripts/burn_subtitles.py --config configs/local.yaml
```
