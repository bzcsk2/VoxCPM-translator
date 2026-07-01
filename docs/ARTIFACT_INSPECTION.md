# Artifact inspection

`inspect_artifacts.py` summarizes ASR JSON, refined JSON, and TTS chunk coverage without running models, FFmpeg, LatentSync, or API calls.

Use it when you want to answer:

- How many segments are in the ASR and refined artifacts?
- Do the ASR and refined files still align?
- How many spoken vs non-spoken rows exist?
- Which speakers appear, and how many rows does each speaker have?
- What is the time span and average segment duration?
- Are there failed translation markers?
- Which TTS chunks are missing?
- Are there extra `raw_*.wav` or `dub_*.wav` files in the chunk directory?

## Basic usage

```bash
python scripts/inspect_artifacts.py --config configs/local.yaml
```

Write a Markdown report:

```bash
python scripts/inspect_artifacts.py --config configs/local.yaml --output outputs/artifact_report.md
```

Machine-readable JSON:

```bash
python scripts/inspect_artifacts.py --config configs/local.yaml --json
```

## Override paths

You can inspect files without editing a config file:

```bash
python scripts/inspect_artifacts.py \
  --config configs/default.yaml \
  --asr-json outputs/test_recognition_vibe.json \
  --refined-json outputs/workflow_data_refined_vibe.json \
  --chunk-dir outputs/dub_chunks
```

## Report sections

The Markdown report contains:

| Section | Meaning |
| --- | --- |
| `ASR segments` | Count, spoken/non-spoken split, speakers, marker counts, time span, and duration stats. |
| `Refined segments` | Same as ASR, plus failed translation marker count. |
| `TTS chunks` | Required, present, missing, extra chunk counts, and missing IDs. |
| `Validation` | Data contract issue summary and issue list. |

## Relationship to other checks

| Command | Purpose |
| --- | --- |
| `scripts/inspect_artifacts.py` | Summarize artifact shape and coverage for humans or agents. |
| `scripts/validate_artifacts.py` | Strict validation gate for ASR/refined alignment and chunk coverage. |
| `scripts/diagnose.py` | Larger local troubleshooting report with system/config/stage/artifact information. |

`inspect_artifacts.py` is read-only. It does not modify artifacts or generate media.

## Demo smoke integration

The no-model demo smoke runs artifact inspection and writes:

```text
outputs/demo_smoke/artifact_report.md
```

Run it with:

```bash
python scripts/run_demo_smoke.py
```
