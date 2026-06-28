# Data contracts

This document defines the JSON and chunk-file contracts between pipeline stages. These contracts are intentionally strict because later stages depend on stable segment IDs, timestamps, speakers, and text fields.

## ASR JSON contract

`paths.asr_json` is produced by stage 02 and consumed by translation / refinement.

It must be a JSON array. Each row must be an object with these keys:

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | integer recommended | Sequential segment ID. Generated ASR output should use `0, 1, 2, ...`. |
| `start` | string | Segment start timestamp in `HH:MM:SS.mmm` format. |
| `end` | string | Segment end timestamp in `HH:MM:SS.mmm` format. Must be after `start`. |
| `speaker` | string | Speaker identifier. |
| `text_zh` | string | Original or ASR-transcribed Chinese text. |

Example:

```json
[
  {
    "id": 0,
    "start": "00:00:00.000",
    "end": "00:00:01.320",
    "speaker": "spk1",
    "text_zh": "你去哪儿了"
  }
]
```

## Refined JSON contract

`paths.refined_json` is produced by stage 03 and consumed by verification, TTS generation, audio assembly, and subtitle generation.

It must preserve all immutable ASR fields exactly:

- `id`
- `start`
- `end`
- `speaker`
- `text_zh`

It must add:

| Key | Type | Meaning |
| --- | --- | --- |
| `zh_fixed` | string | Corrected Chinese text with better punctuation and ASR fixes. |
| `en` | string | English dubbing translation. |

Example:

```json
[
  {
    "id": 0,
    "start": "00:00:00.000",
    "end": "00:00:01.320",
    "speaker": "spk1",
    "text_zh": "你去哪儿了",
    "zh_fixed": "你去哪儿了？",
    "en": "Where did you go?"
  }
]
```

The verifier treats `[Error]` and `[Translation Failed]` as failed translations.

## Timestamp rules

Timestamps must use this exact format:

```text
HH:MM:SS.mmm
```

Examples:

```text
00:00:00.000
00:01:02.345
01:12:03.900
```

The contract validator reports an error when `end <= start`. It reports a warning when a segment starts before the previous segment ends.

## Alignment rules

Stage 04 validates that ASR and refined JSON are aligned:

- same number of rows
- same `id`
- same `start`
- same `end`
- same `speaker`
- same `text_zh`
- refined row has non-empty `zh_fixed`
- refined row has non-empty `en`

Only `zh_fixed` and `en` should be changed by the refinement / translation stage.

## Non-spoken markers

These exact markers are treated as non-spoken rows for TTS chunk coverage:

```text
[Music]
[Human Sounds]
[Human sounds]
[Silence]
```

They may remain in the JSON but do not require a generated audio chunk.

Do not use broad bracketed text as a substitute for dialogue. For example, `[Lyric] ...` should still be treated as content unless a later stage deliberately supports a separate lyric policy.

## TTS chunk contract

For every spoken row in `paths.refined_json`, stage 05 expects one WAV file in `paths.dub_chunk_dir` named either:

```text
raw_<id>.wav
```

or:

```text
dub_<id>.wav
```

Examples:

```text
outputs/dub_chunks/raw_0.wav
outputs/dub_chunks/dub_1.wav
```

The validator accepts either prefix for compatibility. Newly generated chunks use `raw_<id>.wav`.

## Validation commands

Validate ASR and refined JSON alignment only:

```bash
python scripts/validate_artifacts.py --config configs/local.yaml --skip-chunks
```

Validate ASR, refined JSON alignment, and chunks together:

```bash
python scripts/validate_artifacts.py --config configs/local.yaml
```

Stage 04 runs the same alignment checks:

```bash
python scripts/04_verify_translation.py --config configs/local.yaml
```

Stage 05 validates refined JSON before checking or generating audio chunks:

```bash
python scripts/05_generate_audio_chunks.py --config configs/local.yaml
```

Pipeline status also uses the shared chunk-coverage logic for stage 05:

```bash
python scripts/run_pipeline.py --config configs/local.yaml --from-stage 0 --to-stage 6 --status
```

## Developer notes

The shared implementation lives in `scripts/data_contracts.py`. New scripts should reuse this module instead of copying timestamp, alignment, marker, or chunk-coverage logic.
