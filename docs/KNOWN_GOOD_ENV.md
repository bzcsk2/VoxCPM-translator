# Known-good environment

This document records environment combinations that are known to work. Keep it current when a full local run is completed.

## Lightweight CI environment

This environment does **not** validate GPU models, ASR, TTS, FFmpeg media processing, or LatentSync. It validates syntax, helper logic, and dry-run orchestration.

| Component | Value |
| --- | --- |
| Runner | GitHub Actions `ubuntu-latest` |
| Python | 3.10 |
| Checks | `python -m compileall scripts`, `pytest -q`, pipeline dry-run |
| Models required | None |
| API keys required | None |
| Media files required | None |

## Full local pipeline environment

Fill this section after a complete local run from `00_extract_audio.py` through `06_assemble_final.py`.

| Component | Value |
| --- | --- |
| OS | TODO |
| Python | TODO |
| CUDA | TODO |
| GPU | TODO |
| NVIDIA driver | TODO |
| PyTorch | TODO |
| FFmpeg / FFprobe | TODO |
| audio-separator | TODO |
| VibeVoice repo commit | TODO |
| VibeVoice-ASR model | TODO |
| Qwen ASR model | TODO |
| VoxCPM model / adapter | TODO |
| LatentSync repo commit | Optional / TODO |
| LLM provider / model | TODO |

## What to record after a successful full run

Record the following before cutting a release or recommending the setup to other users:

```bash
python --version
ffmpeg -version | head -n 1
ffprobe -version | head -n 1
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
python scripts/check_env.py --config configs/local.yaml
```

Also record:

- exact model names and download sources;
- local repository commit SHAs for VibeVoice, VoxCPM adapters, and LatentSync;
- whether stages 00 through 06 completed without manual edits;
- whether LatentSync was run;
- any local patches or environment variables required.

Do not paste API keys, private file paths, private media names, or non-redistributable model files into this document.
