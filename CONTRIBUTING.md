# Contributing

VoxCPM Translator is a research workflow for local AI dubbing. Contributions are welcome when they keep the repository usable without bundling private models, copyrighted media, generated output, or machine-specific paths.

## Good contribution areas

- Documentation fixes for setup, models, and troubleshooting.
- Safer validation around JSON, timestamps, and missing files.
- Backend adapters for local audio generation, as long as model weights stay outside the repository.
- CI checks that do not require GPUs, paid APIs, local media, or model downloads.

## Development setup

```bash
conda create -n voxcpm-translator python=3.10 -y
conda activate voxcpm-translator
pip install -r requirements-dev.txt
```

Create local configuration from the template only when you need to run real pipeline stages:

```bash
cp configs/local.example.yaml configs/local.yaml
```

Do not commit `configs/local.yaml`, `.env`, model files, input videos, generated audio, or generated videos.

## Lightweight checks

These are the default checks for ordinary documentation, helper, and validation changes. They are the same checks run by CI:

```bash
python scripts/dev_check.py
```

The development check runner includes Python compilation, shell syntax validation when `bash` is available, unit tests, and a pipeline dry-run against `configs/default.yaml`.

Run a subset when iterating on a focused change:

```bash
python scripts/dev_check.py --check tests
python scripts/dev_check.py --check compile --check shell
python scripts/dev_check.py --check pipeline-dry-run
```

They should not require GPUs, paid APIs, local media, model downloads, VibeVoice, VoxCPM, or LatentSync.

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the local check workflow and CI policy.

## Full local pipeline checks

Run these only when a change affects real media processing, ASR, translation, TTS, assembly, subtitle generation, or lip sync:

```bash
python scripts/check_env.py --config configs/local.yaml
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
python scripts/validate_artifacts.py --config configs/local.yaml
```

For data contracts, status inspection, resume behavior, stage manifests, and safe rerun patterns, see [docs/DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) and [docs/PIPELINE_OPERATIONS.md](docs/PIPELINE_OPERATIONS.md).

Optional stages:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
python scripts/burn_subtitles.py --config configs/local.yaml
```

Full local runs require external models and local media. Record what you used in the pull request: OS, Python version, CUDA / GPU, FFmpeg version, key model directories or model IDs, backend mode, and which stages were run.

## Pull request checklist

Before opening a pull request:

- Keep the diff focused on one topic.
- Do not include model weights, generated media, `.env`, `configs/local.yaml`, or machine-specific absolute paths.
- Run `python scripts/dev_check.py` unless the change is documentation-only.
- Run full local pipeline checks when the change touches runtime behavior that CI cannot cover.
- In the PR body, state exactly what you ran and what you could not run.

## Legal and content policy

Only test with content you have the right to process. Do not upload copyrighted media, voice samples, model weights, private datasets, secrets, or generated output that cannot be redistributed.
