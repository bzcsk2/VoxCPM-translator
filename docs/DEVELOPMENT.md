# Development workflow

This document defines the lightweight development loop for contributors and coding agents.

The goal is to keep routine validation fast, deterministic, and independent of local model weights, paid APIs, GPUs, source media, VibeVoice, VoxCPM, and LatentSync.

## Install development dependencies

```bash
pip install -r requirements-dev.txt
```

`requirements-dev.txt` includes the runtime requirements plus lightweight test tooling.

## Run the standard lightweight check suite

```bash
python scripts/dev_check.py
```

This is the same command used by CI. It runs:

1. Python compilation for `scripts/`.
2. Shell syntax check for `scripts/01_process_vocals.sh` when `bash` is available.
3. YAML config schema validation for `configs/default.yaml`.
4. Unit tests with `pytest -q`.
5. Pipeline dry-run against `configs/default.yaml` from stage 0 to stage 6.
6. No-model demo smoke against `examples/demo` fixtures.

The command should not require local media, model weights, GPU runtime, API keys, FFmpeg execution, or external model repositories.

## Run only one check

Use `--check` to run a focused subset:

```bash
python scripts/dev_check.py --check config-schema
python scripts/dev_check.py --check tests
python scripts/dev_check.py --check pipeline-dry-run
python scripts/dev_check.py --check demo-smoke
python scripts/dev_check.py --check compile --check shell
```

Available checks:

```bash
python scripts/dev_check.py --list
```

## Preview commands without executing

```bash
python scripts/dev_check.py --dry-run
```

## Continue after failures

By default the command stops at the first failure. To collect all lightweight failures in one pass:

```bash
python scripts/dev_check.py --keep-going
```

## Config schema validation

Use schema-only validation when editing committed config templates or adding config keys:

```bash
python scripts/check_config_schema.py --config configs/default.yaml
```

This checks required keys, value types, enum values, numeric ranges, and cross-field rules without checking local files or executables. See [CONFIG_SCHEMA.md](CONFIG_SCHEMA.md).

## Artifact inspection

Use artifact inspection when changing JSON contracts, chunk coverage, diagnostics, or demo fixtures:

```bash
python scripts/inspect_artifacts.py --config outputs/demo_smoke/config.yaml
```

This reports segment counts, speakers, time spans, non-spoken markers, failed translation markers, missing chunks, extra chunks, and validation issue summaries. See [ARTIFACT_INSPECTION.md](ARTIFACT_INSPECTION.md).

## No-model demo smoke

The demo smoke proves the fixture data path without real models:

```bash
python scripts/run_demo_smoke.py
```

It creates `outputs/demo_smoke/`, generates silent WAV chunks for spoken rows, then runs translation alignment verification, artifact validation, manual TTS chunk validation, artifact inspection, and diagnostic report generation.

The committed fixtures live in:

```text
examples/demo/
```

See [../examples/demo/README.md](../examples/demo/README.md) for details.

## CI policy

There is one Python workflow:

```text
.github/workflows/python-checks.yml
```

It installs development dependencies and runs:

```bash
python scripts/dev_check.py
```

Avoid adding another overlapping Python workflow. Add new lightweight checks to `scripts/dev_check.py` so local development and CI stay aligned.

## Full local validation

Use full local validation only when a change affects real media processing, model integration, TTS, assembly, subtitles, or lip sync:

```bash
python scripts/check_env.py --config configs/local.yaml
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
python scripts/validate_artifacts.py --config configs/local.yaml
```

Optional final stages:

```bash
python scripts/07_latentsync_lipsync.py --config configs/local.yaml
python scripts/burn_subtitles.py --config configs/local.yaml
```

Record the OS, Python version, FFmpeg version, GPU/CUDA details, backend mode, model directories or model IDs, and exact stages run in the pull request.

## Repository hygiene

Do not commit:

- `.env`
- `configs/local.yaml`
- model weights
- input media
- generated audio or video
- machine-specific absolute paths
- private API keys or credentials

Use `configs/local.example.yaml` and documentation examples for shareable configuration patterns.
