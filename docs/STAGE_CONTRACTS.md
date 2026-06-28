# Stage contracts

The pipeline stage registry lives in `scripts/stage_contracts.py`. It is the canonical source for stage IDs, names, commands, output keys, optional status, resumability, and short descriptions.

## Why this exists

Earlier versions kept stage commands and output keys directly inside `scripts/run_pipeline.py` as separate structures. That worked, but it made future changes easy to desynchronize:

- a stage command could change without its status outputs changing
- documentation could drift from runtime behavior
- diagnostics and tools needed to duplicate stage metadata

The stage contract registry keeps those values together.

## List stages

Human-readable table:

```bash
python scripts/list_stages.py
```

Machine-readable JSON:

```bash
python scripts/list_stages.py --json
```

## Contract fields

Each stage is represented by `StageContract`:

| Field | Meaning |
| --- | --- |
| `id` | Numeric stage ID used by `--from-stage`, `--to-stage`, manifests, and status output. |
| `name` | Stable stage name used by `--skip` and manifest filenames. |
| `command` | Base command before config injection. |
| `output_keys` | Config keys whose files/directories determine stage status. |
| `description` | Short human-readable purpose. |
| `auto_resumable` | Whether `--resume` can skip the stage when outputs are complete. |
| `optional` | Whether the stage is outside the core stage 0-6 pipeline. |

## Current stages

| ID | Name | Core / optional | Main output contract |
| --- | --- | --- | --- |
| 0 | `extract-audio` | Core | `paths.input_wav` |
| 1 | `process-vocals` | Core | `paths.vocal_source_for_asr`, `paths.instrumental_audio` |
| 2 | `transcribe` | Core | `paths.asr_json` |
| 3 | `refine-translate` | Core | `paths.refined_json` |
| 4 | `verify` | Core check | No durable output; not auto-resumable |
| 5 | `generate-audio-chunks` | Core | `paths.dub_chunk_dir` plus per-segment chunk coverage |
| 6 | `assemble` | Core | `paths.final_video` |
| 7 | `latentsync` | Optional | `paths.lipsync_video` |
| 8 | `burn-subtitles` | Optional | `paths.subtitled_video` |

## Compatibility policy

`run_pipeline.py` still exposes:

```python
STAGES
STAGE_OUTPUT_KEYS
```

These are now derived from `stage_contracts.py` to preserve existing tests and direct callers.

New code should import from `stage_contracts.py` instead of copying stage lists from `run_pipeline.py`.

## Maintenance rules

When adding or changing a stage:

1. Update `scripts/stage_contracts.py`.
2. Keep stage IDs stable unless there is a deliberate migration.
3. Add or update output keys so `--status` and `--resume` stay accurate.
4. Keep `auto_resumable=False` for check-only stages with no durable output.
5. Update `docs/PIPELINE_OPERATIONS.md` if user-facing behavior changes.
6. Run:

```bash
python scripts/dev_check.py
python scripts/list_stages.py
python scripts/list_stages.py --json
```
