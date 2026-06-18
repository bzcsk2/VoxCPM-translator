# LatentSync integration notes

This project treats LatentSync as an optional final stage after the dubbed audio track has been assembled.

## Goal

Input:

- `paths.input_video`: source video
- `paths.temp_mixed_wav`: assembled dubbed audio track

Output:

- `paths.lipsync_video`: lip-synced final video

## Current integration

`scripts/07_latentsync_lipsync.py` is a thin wrapper around a local LatentSync checkout. Configure:

```yaml
models:
  latentsync_dir: "/path/to/LatentSync"
```

The wrapper calls:

```bash
python /path/to/LatentSync/scripts/inference.py \
  --video_path <input video> \
  --audio_path <assembled wav> \
  --video_out_path <output video>
```

## Practical notes

LatentSync can be GPU-memory-sensitive. For longer videos, split the video into shorter clips, run lip-sync per clip, and concatenate the results.

If face detection fails on dark frames, opening frames, closing frames, or profile shots, preserve the original frame instead of failing the entire pipeline.

If CUDA OOM appears during VAE encoding or restoration, try:

1. Shorter clip lengths.
2. Lower batch size in the LatentSync pipeline.
3. Running VAE-heavy operations on a different GPU if your local fork supports it.
4. Explicit cache clearing between batches.

The exact patching strategy depends on the LatentSync version you use locally, so the repository keeps the wrapper minimal and documents the expected integration point instead of vendoring a patched upstream fork.
