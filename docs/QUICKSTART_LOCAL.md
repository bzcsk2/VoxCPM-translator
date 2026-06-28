# Local quickstart

This quickstart answers the first setup question: **which local models do I need to download, where should I put them, and which config keys should point to them?**

The project does not ship model weights. Keep all models outside this repository and reference them from `configs/local.yaml`.

## 0. Recommended local layout

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

## 1. Clone this repository

```bash
git clone https://github.com/bzcsk2/VoxCPM-translator.git
cd VoxCPM-translator
```

## 2. Create the Python environment

```bash
conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements.txt
pip install -U "huggingface_hub[cli]" modelscope
```

Install PyTorch according to your CUDA version. Install FFmpeg / FFprobe through your OS package manager.

## 3. Download or clone the external components

### Required for vocal separation

Place an `audio-separator` compatible vocal model in a local model directory. The default local template expects:

```text
~/models/audio-separator/Kim_Vocal_2.onnx
```

Install the CLI if you will run the vocal separation stage:

```bash
pip install audio-separator
```

### Required for VibeVoice-ASR

```bash
mkdir -p ~/repos ~/models

git clone https://github.com/microsoft/VibeVoice.git ~/repos/VibeVoice
huggingface-cli download microsoft/VibeVoice-ASR --local-dir ~/models/VibeVoice-ASR
huggingface-cli download Qwen/Qwen3-ASR-1.7B --local-dir ~/models/Qwen3-ASR-1.7B
```

For Mainland China network conditions, Qwen3-ASR can also be downloaded through ModelScope:

```bash
modelscope download --model Qwen/Qwen3-ASR-1.7B --local_dir ~/models/Qwen3-ASR-1.7B
```

### Required only if you use VoxCPM2 for TTS

```bash
huggingface-cli download openbmb/VoxCPM2 --local-dir ~/models/VoxCPM2
pip install voxcpm
```

Then copy `examples/voxcpm_adapter_template.py` to your own adapter module and replace the placeholder loader / inference call with the VoxCPM API that works in your environment.

### Optional lip sync

```bash
git clone https://github.com/bytedance/LatentSync.git ~/repos/LatentSync
```

LatentSync may need a separate environment because its PyTorch / CUDA / diffusers stack can conflict with ASR or TTS dependencies.

## 4. Create local config files

Use the user-facing local template:

```bash
cp .env.example .env
cp configs/local.example.yaml configs/local.yaml
```

Do not copy `configs/default.yaml` for private local work. It is the canonical schema-like default used when no `--config` is provided. See [CONFIGURATION.md](CONFIGURATION.md) for the full config policy.

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
  latentsync_dir: "/home/you/repos/LatentSync"

tts:
  backend: "manual"  # manual | custom_command | voxcpm
```

For translation, put your API key in `.env`:

```bash
NVIDIA_API_KEY="your_key_here"
```

## 5. Choose the first TTS mode

Use `manual` first if you want to validate ASR, translation, and assembly inputs before wiring a TTS engine:

```yaml
tts:
  backend: "manual"
```

In manual mode, `scripts/05_generate_audio_chunks.py` only checks that WAV chunks already exist in `paths.dub_chunk_dir`. Each spoken segment must have one file named either:

```text
raw_<id>.wav
```

or:

```text
dub_<id>.wav
```

Switch to `custom_command` when you have a local TTS CLI:

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
```

Switch to `voxcpm` only after your adapter module is importable:

```yaml
tts:
  backend: "voxcpm"
  voxcpm_adapter: "my_voxcpm_adapter"
  voxcpm_adapter_function: "generate_audio"
```

## 6. Run preflight

```bash
python scripts/check_env.py --config configs/local.yaml
```

Fix all `[FAIL]` entries before running the full pipeline. `[WARN]` entries may still block later stages if they refer to a stage you plan to run.

## 7. Run the pipeline

Use the orchestrator with a preflight gate:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

If a run fails midway, inspect status and resume:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume --preflight
```

Manual stage execution is still useful while debugging:

```bash
python scripts/00_extract_audio.py --config configs/local.yaml
bash scripts/01_process_vocals.sh configs/local.yaml
python scripts/02_transcribe_vibe.py --config configs/local.yaml
python scripts/03_refine_and_translate.py --config configs/local.yaml
python scripts/04_verify_translation.py --config configs/local.yaml
python scripts/05_generate_audio_chunks.py --config configs/local.yaml
python scripts/06_assemble_final.py --config configs/local.yaml
```

See [PIPELINE_OPERATIONS.md](PIPELINE_OPERATIONS.md) for dry-run, status, resume, skip, and manifest workflows.

## 8. Common first-run failure points

| Symptom | Likely fix |
| --- | --- |
| `No module named vibevoice` | `models.vibevoice_repo` must point to the local VibeVoice checkout that contains the `vibevoice` package. |
| audio-separator cannot find `Kim_Vocal_2.onnx` | Put the ONNX file under `models.audio_separator_model_dir` or change `models.audio_separator_model` to the filename you actually downloaded. |
| VibeVoice model loading fails | Check `models.vibevoice_asr_path`, `models.qwen_asr_path`, CUDA memory, and upstream VibeVoice dependency installation. |
| translation fails with API key error | Set the environment variable named by `llm.api_key_env`, default `NVIDIA_API_KEY`. |
| `tts.backend: voxcpm` fails during preflight | Ensure `models.voxcpm_model_path` exists and `tts.voxcpm_adapter` is importable from the current Python environment. |
| manual TTS reports missing chunks | Place `raw_<id>.wav` or `dub_<id>.wav` files under `paths.dub_chunk_dir` for every spoken segment. |

## 9. Do not commit local artifacts

Do not commit model weights, private videos, generated audio / video, `.env`, `configs/local.yaml`, or `outputs/failed_llm_batches/`.
