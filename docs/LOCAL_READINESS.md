# Local readiness runbook

`readiness_report.py` is the project-level entry point for deciding what to do before a real local run.

It combines the existing checks into one report:

- YAML schema validation
- environment and local path checks
- selected pipeline stage status
- optional ASR/refined/chunk artifact inspection
- recommended next actions in priority order

It does not run models, FFmpeg muxing, LatentSync, or API calls.

## Basic usage

```bash
python scripts/readiness_report.py --config configs/local.yaml
```

Include artifact inspection:

```bash
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts
```

Write a report file:

```bash
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts --output outputs/readiness_report.md
```

Machine-readable output:

```bash
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts --json
```

Fail in automation when blocking issues exist:

```bash
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts --strict
```

## Stage range

Limit the status report and recommended pipeline command to a stage range:

```bash
python scripts/readiness_report.py --config configs/local.yaml --from-stage 3 --to-stage 6
```

This is useful after ASR is complete and you are iterating on translation, TTS chunks, and final assembly.

## How to interpret the report

### Schema

Schema issues mean the YAML structure itself is wrong: missing keys, wrong types, unsupported enum values, invalid numeric ranges, or invalid cross-field combinations.

Follow the suggested command:

```bash
python scripts/check_config_schema.py --config configs/local.yaml
```

### Environment

Environment failures mean local requirements are not ready: missing executables, nonexistent model paths, missing media paths, missing adapter modules, or missing required values.

Follow the suggested command:

```bash
python scripts/check_env.py --config configs/local.yaml
```

### Stage status

Stage status tells you which selected outputs are complete, missing, partial, unknown, or check-only.

Common states:

| Status | Meaning |
| --- | --- |
| `complete` | Expected output exists. |
| `missing` | Expected output does not exist. |
| `partial` | Some but not all expected outputs exist, or TTS chunks are incomplete. |
| `check` | The stage has no durable output and should run when selected. |
| `unknown` | No expected output key is configured. |

### Artifacts

When `--include-artifacts` is set, the report embeds a compact artifact summary:

- ASR segment count
- refined segment count
- TTS chunks required / present / missing
- validation issue summary

For more detail:

```bash
python scripts/inspect_artifacts.py --config configs/local.yaml
```

## Recommended flow

### First-time user

```bash
python scripts/run_demo_smoke.py
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts
```

### Before a real pipeline run

```bash
python scripts/readiness_report.py --config configs/local.yaml --from-stage 0 --to-stage 6 --include-artifacts
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --resume --preflight
```

### After a failed run

```bash
python scripts/readiness_report.py --config configs/local.yaml --include-artifacts --output outputs/readiness_report.md
python scripts/diagnose.py --config configs/local.yaml --include-artifacts --output outputs/diagnostic_report.md
```

Paste both reports into an issue or hand them to an agent.

## Relationship to other commands

| Command | Purpose |
| --- | --- |
| `readiness_report.py` | Decide what to fix or run next. |
| `check_config_schema.py` | Validate YAML structure only. |
| `check_env.py` | Validate local environment and paths. |
| `inspect_artifacts.py` | Summarize ASR/refined/chunk artifacts. |
| `validate_artifacts.py` | Strict artifact validation gate. |
| `diagnose.py` | Full troubleshooting bundle for handoff. |
| `run_pipeline.py` | Actually execute selected stages. |
