from __future__ import annotations

from pathlib import Path
from typing import Any


_INITIALIZED_MODEL: Any | None = None


def _load_model(config: dict[str, Any]) -> Any:
    """Load and cache your local VoxCPM model.

    This file is a template. Keep model weights outside this repository and adapt
    the import/call code to the VoxCPM version installed in your local environment.
    """
    global _INITIALIZED_MODEL
    if _INITIALIZED_MODEL is not None:
        return _INITIALIZED_MODEL

    model_path = config.get("models", {}).get("voxcpm_model_path")
    if not model_path:
        raise RuntimeError("Missing config key: models.voxcpm_model_path")

    # Example shape only. Replace with your local VoxCPM import and loader.
    # from voxcpm import VoxCPM
    # _INITIALIZED_MODEL = VoxCPM.from_pretrained(model_path)
    raise NotImplementedError(
        "Edit examples/voxcpm_adapter_template.py for your local VoxCPM API before using it. "
        f"Configured model path: {model_path}"
    )


def generate_audio(segment: dict[str, Any], output_path: Path, config: dict[str, Any]) -> None:
    """Generate one WAV file for a single segment.

    `scripts/05_generate_audio_chunks.py` calls this function when:

    ```yaml
    tts:
      backend: "voxcpm"
      voxcpm_adapter: "examples.voxcpm_adapter_template"
      voxcpm_adapter_function: "generate_audio"
    ```

    The function must write a WAV file to `output_path`.
    """
    model = _load_model(config)
    text = str(segment.get("en") or segment.get("zh_fixed") or segment.get("text_zh") or "").strip()
    speaker = str(segment.get("speaker", ""))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Example shape only. Replace with your local VoxCPM inference call.
    # model.generate_to_file(
    #     text=text,
    #     speaker=speaker,
    #     output_path=str(output_path),
    #     cfg_value=config.get("tts", {}).get("cfg_value", 2.0),
    #     inference_timesteps=config.get("tts", {}).get("inference_timesteps", 15),
    # )
    raise NotImplementedError(
        "Replace the template inference call with your local VoxCPM generation code. "
        f"Segment={segment.get('id')} speaker={speaker!r} text={text[:80]!r} output={output_path} model={model!r}"
    )
