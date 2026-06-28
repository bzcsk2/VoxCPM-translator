# Output stages

This guide covers the final media-producing stages of the pipeline:

- stage 06: assemble dubbed audio and mux it with the source video
- stage 07: optional LatentSync lip sync
- stage 08: optional ASS subtitle burn-in

Use this after ASR, translation, and TTS chunk validation have passed.

## Stage 06: assemble final dubbed video

Command:

```bash
python scripts/06_assemble_final.py --config configs/local.yaml
```

Inputs:

| Config key | Meaning |
| --- | --- |
| `paths.refined_json` | Refined translation JSON. Must satisfy the refined JSON contract. |
| `paths.instrumental_audio` | Instrumental / background track used as the base audio bed. |
| `paths.dub_chunk_dir` | Directory containing `raw_<id>.wav` or `dub_<id>.wav` chunks. |
| `paths.input_video` | Source video used for the final video stream. |

Outputs:

| Config key | Meaning |
| --- | --- |
| `paths.temp_mixed_wav` | Intermediate full mixed WAV. |
| `paths.final_video` | Final dubbed video without optional subtitle burn-in. |

The assembly stage validates all configured inputs before running FFmpeg. It also validates refined JSON through the shared data contract layer.

### Missing chunk policy

`assembly.missing_chunk_policy` controls what happens when spoken segments do not have matching chunks:

| Value | Behavior |
| --- | --- |
| `error` | Fail before exporting output. Recommended for final runs. |
| `warn` | Print missing chunk IDs and continue. Useful for partial previews. |
| `skip` | Skip missing chunks silently. Useful only for debugging. |

Default:

```yaml
assembly:
  missing_chunk_policy: "error"
```

### Speed adjustment

Generated chunks are adjusted to fit the target segment window when needed. `assembly.min_speed_ratio` sets the slowest allowed ratio for chunks that are shorter than the target duration:

```yaml
assembly:
  min_speed_ratio: 0.70
```

The value must be positive.

## Stage 07: optional LatentSync

Command:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
```

Inputs:

| Config key | Meaning |
| --- | --- |
| `models.latentsync_dir` | Local LatentSync checkout. |
| `paths.input_video` | Source video. |
| `paths.temp_mixed_wav` | Mixed dubbed audio from stage 06. |

Output:

| Config key | Meaning |
| --- | --- |
| `paths.lipsync_video` | Lip-synced video output. |

The script validates the configured LatentSync directory, input video, mixed WAV, and output parent directory before invoking LatentSync.

LatentSync is optional and may require a separate Python / CUDA environment.

## Stage 08: optional subtitle burn-in

Command:

```bash
python scripts/burn_subtitles.py --config configs/local.yaml
```

Inputs:

| Config key | Meaning |
| --- | --- |
| `paths.refined_json` | Refined translation JSON. |
| `paths.final_video` | Dubbed video from stage 06. |

Outputs:

| Config key | Meaning |
| --- | --- |
| `paths.subtitle_ass` | Generated ASS subtitle file. |
| `paths.subtitled_video` | Final video with burned-in subtitles. |

The subtitle stage validates the refined JSON and required video input before writing ASS events or invoking FFmpeg.

Subtitle settings live under `subtitles`:

```yaml
subtitles:
  font_name: "Arial"
  font_size: 60
  pos_x: 960
  pos_y: 930
  color_text: "&H00FFFFFF"
  color_outline: "&H00000000"
  outline_size: 2
  max_chars_per_line: 42
```

`subtitles.max_chars_per_line`, `subtitles.font_size`, and `subtitles.outline_size` must be positive.

## Recommended final-stage workflow

For a normal final render:

```bash
python scripts/validate_artifacts.py --config configs/local.yaml
python scripts/06_assemble_final.py --config configs/local.yaml
```

For lip sync:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
```

For subtitle burn-in:

```bash
python scripts/burn_subtitles.py --config configs/local.yaml
```

For a status check across final stages:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 6 --to-stage 8 --status
```

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Stage 06 reports missing chunks | Run `python scripts/validate_artifacts.py --config configs/local.yaml` and check `paths.dub_chunk_dir`. |
| Stage 06 fails before FFmpeg | Check `paths.instrumental_audio`, `paths.input_video`, `paths.refined_json`, and `assembly.missing_chunk_policy`. |
| Stage 07 cannot find inference.py | `models.latentsync_dir` must point to the LatentSync repository root. |
| Stage 08 generates no subtitle events | Confirm `paths.refined_json` has spoken rows with non-empty `en` text. |
| Subtitle burn-in fails in FFmpeg | Check that `paths.subtitle_ass` has no problematic path characters for your FFmpeg build, or run from the repository root. |
