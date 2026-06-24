# Troubleshooting

## `NVIDIA_API_KEY` is missing

Set the key in your shell:

```bash
export NVIDIA_API_KEY="your_key_here"
```

Or put it in `.env` and load it before running scripts.

## FFmpeg cannot find input files

Check `configs/local.yaml`. The scripts do not assume your local machine paths. Every video, audio, model, and output path should be configured explicitly.

## ASR import fails

`scripts/02_transcribe_vibe.py` appends `models.vibevoice_repo` to `sys.path`. Make sure it points to the local VibeVoice source directory that contains the `vibevoice` Python package.

## Audio generation backend import fails

Install your selected local audio generation backend according to its upstream instructions. The repository expects the backend stage to produce one WAV file per segment in `paths.dub_chunk_dir`, named `raw_<id>.wav`.

## GPU out of memory during LatentSync

LatentSync is memory-sensitive. Try shorter clips first. Splitting the video into shorter segments is usually more reliable than forcing a full-length clip through one pass.

## Generated speech is too fast or too slow

Adjust:

```yaml
assembly:
  min_speed_ratio: 0.70
```

Lower values allow stronger slowing, but may introduce artifacts.

## Translation output JSON is invalid

Run:

```bash
python scripts/04_verify_translation.py --config configs/local.yaml
```

If invalid JSON is returned by the LLM, reduce `llm.batch_size` or increase `llm.max_tokens`.
