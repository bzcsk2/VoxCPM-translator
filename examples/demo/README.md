# No-model demo fixtures

This directory contains the smallest committed data set that explains the pipeline artifact flow without requiring local models, API keys, GPUs, FFmpeg, VibeVoice, VoxCPM, or source media.

Files:

| File | Purpose |
| --- | --- |
| `asr_demo.json` | Minimal stage 02-style ASR output. |
| `refined_demo.json` | Minimal stage 03-style refined translation output. |

The demo contains three segments:

1. spoken line by `SPEAKER_00`
2. non-spoken `[Music]` marker
3. spoken line by `SPEAKER_01`

Only spoken rows need audio chunks. The demo smoke runner generates silent WAV chunks for the spoken rows so chunk coverage can be validated without a real TTS model.

## Run the demo smoke

From the repository root:

```bash
python scripts/run_demo_smoke.py
```

The command creates:

```text
outputs/demo_smoke/
  asr_demo.json
  refined_demo.json
  chunks/raw_0.wav
  chunks/raw_2.wav
  instrumental.wav
  input_video_placeholder.mp4
  config.yaml
  diagnostic_report.md
```

It then runs:

```bash
python scripts/04_verify_translation.py --config outputs/demo_smoke/config.yaml
python scripts/validate_artifacts.py --config outputs/demo_smoke/config.yaml
python scripts/05_generate_audio_chunks.py --config outputs/demo_smoke/config.yaml
python scripts/diagnose.py --config outputs/demo_smoke/config.yaml --include-artifacts --output outputs/demo_smoke/diagnostic_report.md
```

The placeholder MP4 is intentionally not a real video. The demo smoke does not run stage 06 assembly. It only proves the JSON, chunk, TTS-manual, and diagnostic data path.

## Custom work directory

```bash
python scripts/run_demo_smoke.py --work-dir /tmp/voxcpm-translator-demo
```

## What this does not test

The demo smoke does not test:

- VibeVoice-ASR inference
- LLM translation
- real TTS inference
- FFmpeg muxing
- subtitle burn-in
- LatentSync

Use real local pipeline runs for those checks.
