# Pipeline operations

This guide explains how to run the pipeline in a safer, observable way after the local models and media paths have been configured.

Use this document when you want to answer these questions before a long run:

- Is my config complete enough to start?
- Which stages are already complete?
- Can I resume without redoing earlier work?
- Where can I see the last run status for each stage?

## 1. Run preflight checks

Run the environment and configuration checks first:

```bash
python scripts/check_env.py --config configs/local.yaml
```

The command prints `OK`, `WARN`, and `FAIL` rows. `FAIL` means the pipeline is expected to break before or during a required stage. `WARN` means the configuration may still run, but a later optional or conditional stage may fail.

For machine-readable output:

```bash
python scripts/check_env.py --config configs/local.yaml --json
```

For a compact human-readable output without the final summary line:

```bash
python scripts/check_env.py --config configs/local.yaml --no-summary
```

## 2. Preview selected stages

Before running anything, print the exact commands that would run:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --dry-run
```

This is useful after editing `configs/local.yaml`, changing the stage range, or adding `--skip` options.

## 3. Gate a real run with preflight

Use `--preflight` when you want the orchestrator to stop before stage execution if required checks fail:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

You can combine it with `--dry-run` to test the gate and command plan without executing stages:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight --dry-run
```

## 4. Inspect stage status

To see which selected stages appear complete, missing, partial, or check-only:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
```

The status command inspects configured output paths. For the TTS stage, it checks whether every non-noise segment in `paths.refined_json` has a corresponding `raw_<id>.wav` or `dub_<id>.wav` in `paths.dub_chunk_dir`.

## 5. Resume safely

Use `--resume` to skip stages whose expected outputs already exist:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume
```

The verify stage is intentionally not auto-skipped because it has no durable output file. It should still run when selected.

## 6. Skip a stage explicitly

You can skip stages by stage ID or stage name:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --skip 1 --skip transcribe
```

Use explicit skips carefully. A downstream stage may still fail if it depends on outputs from the skipped stage.

## 7. Read stage manifests

After each executed stage, the orchestrator writes a small manifest under:

```text
outputs/.pipeline_state/
```

The manifest records:

- stage ID and name
- success or failure
- start and finish time
- duration
- return code
- config file basename

It intentionally does not store the full command, private absolute config path, model paths, source media paths, or secrets.

## 8. Recommended run patterns

### First full local run

```bash
python scripts/check_env.py --config configs/local.yaml
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --preflight
```

### Continue after fixing a failed middle stage

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume --preflight
```

### Rerun only translation and downstream audio assembly

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 3 --to-stage 6 --preflight
```

### Only inspect subtitles or lip-sync outputs

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 7 --to-stage 8 --status
```

## 9. Troubleshooting

| Symptom | What to check |
| --- | --- |
| `check_env.py` returns `FAIL` for placeholder paths | Replace `/path/to/...` values in `configs/local.yaml` with real local paths. |
| `--preflight` stops before stages run | Fix all `FAIL` rows first, then rerun. |
| `--status` reports TTS as partial | Add missing `raw_<id>.wav` or `dub_<id>.wav` files for non-noise segments. |
| `--resume` reruns verify | This is expected because the verify stage has no durable output. |
| A stage fails but output files exist | Read `outputs/.pipeline_state/stage_*.json` and rerun with a narrower `--from-stage` / `--to-stage` range. |
