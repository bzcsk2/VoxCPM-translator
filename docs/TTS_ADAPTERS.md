# TTS adapter contract

Stage 05 generates or validates one WAV chunk per spoken segment. The shared contract code lives in:

```text
scripts/tts_contracts.py
```

The stage runner is:

```text
scripts/05_generate_audio_chunks.py
```

## Backends

`tts.backend` supports three modes:

| Backend | Purpose |
| --- | --- |
| `manual` | Do not generate audio. Verify that required chunks already exist. |
| `custom_command` | Call an external CLI command once per spoken segment. |
| `voxcpm` | Import a Python adapter function and call it once per spoken segment. |

## Spoken segment rule

A row is considered spoken when it has usable text and is not one of the non-spoken markers handled by the shared data contracts:

- `[Music]`
- `[Human Sounds]`
- `[Human sounds]`
- `[Silence]`

Each spoken row must produce one WAV file:

```text
raw_<id>.wav
```

Manual validation also accepts existing normalized files:

```text
dub_<id>.wav
```

## Custom command backend

Example:

```yaml
tts:
  backend: "custom_command"
  custom_command: "python my_tts.py --text '$text' --speaker '$speaker' --output '$output'"
  overwrite: false
```

Supported variables:

| Variable | Value |
| --- | --- |
| `$id` | Segment ID. |
| `$speaker` | Segment speaker label. |
| `$text` | Preferred segment text, normally English. |
| `$output` | Required output WAV path, usually `raw_<id>.wav`. |
| `$start` | Segment start timestamp. |
| `$end` | Segment end timestamp. |

The command must write a WAV file to `$output`. If the command exits successfully but does not create the file, stage 05 fails.

## Python adapter backend

Example config:

```yaml
tts:
  backend: "voxcpm"
  voxcpm_adapter: "my_voxcpm_adapter"
  voxcpm_adapter_function: "generate_audio"
  overwrite: false
```

The adapter module must be importable from the current Python environment. The configured function must be callable with this signature:

```python
def generate_audio(segment: dict, output_path: Path, config: dict) -> None:
    ...
```

The function must write a WAV file to `output_path`.

The stage runner validates that the output file exists after the adapter returns. It does not validate audio codec details, duration, loudness, or sample rate. Those belong to backend-specific tests or later media QA.

## Adapter function responsibilities

An adapter should:

1. Load and cache its local model outside the per-segment hot path.
2. Use `segment["en"]` for English dubbing text unless intentionally configured otherwise.
3. Create `output_path.parent` before writing.
4. Write exactly one WAV file to `output_path`.
5. Raise a clear exception if local model loading or generation fails.
6. Keep model weights, checkpoints, prompts, and private paths outside the repository.

## Minimal adapter skeleton

```python
from pathlib import Path
from typing import Any

_MODEL: Any | None = None


def _load_model(config: dict[str, Any]) -> Any:
    global _MODEL
    if _MODEL is None:
        model_path = config["models"]["voxcpm_model_path"]
        # Load your local model here.
        _MODEL = object()
    return _MODEL


def generate_audio(segment: dict[str, Any], output_path: Path, config: dict[str, Any]) -> None:
    model = _load_model(config)
    text = str(segment.get("en") or "").strip()
    speaker = str(segment.get("speaker", ""))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Replace this with real inference code and write output_path.
    raise NotImplementedError(f"Generate {output_path} for {speaker}: {text[:80]} using {model!r}")
```

See `examples/voxcpm_adapter_template.py` for a longer template.

## Debugging

List missing chunks:

```bash
python scripts/05_generate_audio_chunks.py --config configs/local.yaml
```

Validate artifacts and chunks together:

```bash
python scripts/validate_artifacts.py --config configs/local.yaml
```

Generate a full diagnostic report:

```bash
python scripts/diagnose.py --config configs/local.yaml --include-artifacts
```
