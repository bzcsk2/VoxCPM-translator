from __future__ import annotations

import importlib
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from string import Template
from typing import Any, Callable, Protocol

from data_contracts import is_non_spoken_segment, segment_text

TTS_BACKENDS = {"manual", "custom_command", "voxcpm"}


class TTSAdapter(Protocol):
    def __call__(self, segment: dict[str, Any], output_path: Path, config: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class TTSChunkRequest:
    segment_id: Any
    text: str
    speaker: str
    start: str
    end: str
    output_path: Path

    def to_template_mapping(self) -> dict[str, str]:
        return {
            "id": str(self.segment_id),
            "speaker": self.speaker,
            "text": self.text,
            "output": str(self.output_path),
            "start": self.start,
            "end": self.end,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["output_path"] = str(self.output_path)
        return payload


def is_spoken_segment(segment: dict[str, Any]) -> bool:
    return bool(segment_text(segment)) and not is_non_spoken_segment(segment)


def output_chunk_path(chunk_dir: str | Path, segment_id: Any, prefix: str = "raw") -> Path:
    return Path(chunk_dir) / f"{prefix}_{segment_id}.wav"


def build_chunk_request(segment: dict[str, Any], chunk_dir: str | Path, prefix: str = "raw") -> TTSChunkRequest:
    return TTSChunkRequest(
        segment_id=segment.get("id"),
        text=segment_text(segment),
        speaker=str(segment.get("speaker", "")),
        start=str(segment.get("start", "")),
        end=str(segment.get("end", "")),
        output_path=output_chunk_path(chunk_dir, segment.get("id"), prefix=prefix),
    )


def iter_spoken_chunk_requests(segments: list[dict[str, Any]], chunk_dir: str | Path, prefix: str = "raw") -> list[TTSChunkRequest]:
    return [build_chunk_request(segment, chunk_dir, prefix=prefix) for segment in segments if is_spoken_segment(segment)]


def render_custom_command(template: str, request: TTSChunkRequest) -> list[str]:
    rendered = Template(template).safe_substitute(request.to_template_mapping())
    return shlex.split(rendered)


def load_adapter(module_name: str, function_name: str = "generate_audio") -> TTSAdapter:
    if not module_name:
        raise RuntimeError("empty TTS adapter module name")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Could not import TTS adapter module {module_name!r}. "
            "Install it, add it to PYTHONPATH, or use tts.backend=custom_command/manual."
        ) from exc

    function = getattr(module, function_name, None)
    if function is None or not callable(function):
        raise RuntimeError(f"Adapter module {module_name!r} does not define callable {function_name!r}.")
    return function


def ensure_chunk_created(path: str | Path, producer: str) -> None:
    output_path = Path(path)
    if not output_path.exists():
        raise FileNotFoundError(f"{producer} completed but did not create: {output_path}")
    if not output_path.is_file():
        raise FileNotFoundError(f"{producer} created a non-file output: {output_path}")


def validate_backend_name(backend: str) -> str:
    if backend not in TTS_BACKENDS:
        expected = ", ".join(sorted(TTS_BACKENDS))
        raise RuntimeError(f"Unsupported tts.backend: {backend!r}. Supported: {expected}")
    return backend
