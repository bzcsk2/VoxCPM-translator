from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from string import Template
from typing import Any

from common import ensure_dir, get_nested, load_config, parse_args, require_nested


NOISE_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}


def expected_chunk_path(chunk_dir: Path, seg_id: Any) -> Path:
    raw_path = chunk_dir / f"raw_{seg_id}.wav"
    if raw_path.exists():
        return raw_path
    return chunk_dir / f"dub_{seg_id}.wav"


def _segment_text(segment: dict[str, Any]) -> str:
    return str(segment.get("en") or segment.get("zh_fixed") or segment.get("text_zh") or "").strip()


def _render_command(template: str, segment: dict[str, Any], output_path: Path) -> list[str]:
    mapping = {
        "id": str(segment.get("id")),
        "speaker": str(segment.get("speaker", "")),
        "text": _segment_text(segment),
        "output": str(output_path),
        "start": str(segment.get("start", "")),
        "end": str(segment.get("end", "")),
    }
    rendered = Template(template).safe_substitute(mapping)
    return shlex.split(rendered)


def validate_manual_chunks(segments: list[dict[str, Any]], chunk_dir: Path) -> list[Any]:
    missing: list[Any] = []
    for segment in segments:
        text = _segment_text(segment)
        if text in NOISE_MARKERS:
            continue
        seg_id = segment.get("id")
        if not expected_chunk_path(chunk_dir, seg_id).exists():
            missing.append(seg_id)
    return missing


def run_custom_command(segments: list[dict[str, Any]], chunk_dir: Path, command_template: str, overwrite: bool) -> None:
    for segment in segments:
        text = _segment_text(segment)
        if not text or text in NOISE_MARKERS:
            continue
        seg_id = segment.get("id")
        output_path = chunk_dir / f"raw_{seg_id}.wav"
        if output_path.exists() and not overwrite:
            print(f"Skipping existing chunk: {output_path}")
            continue
        cmd = _render_command(command_template, segment, output_path)
        print(f"Generating chunk ID {seg_id}: {output_path}")
        subprocess.run(cmd, check=True)
        if not output_path.exists():
            raise FileNotFoundError(f"Custom TTS command completed but did not create: {output_path}")


def main() -> int:
    args = parse_args("Generate or validate per-segment audio chunks")
    cfg = load_config(args.config)

    refined_json = Path(require_nested(cfg, "paths.refined_json"))
    chunk_dir = ensure_dir(require_nested(cfg, "paths.dub_chunk_dir"))
    backend = get_nested(cfg, "tts.backend", "manual")
    overwrite = bool(get_nested(cfg, "tts.overwrite", False))

    with refined_json.open("r", encoding="utf-8") as f:
        segments = json.load(f)

    if backend == "manual":
        missing = validate_manual_chunks(segments, chunk_dir)
        if missing:
            print("Manual TTS backend selected, but audio chunks are missing.")
            print(f"Place WAV files in {chunk_dir} named raw_<id>.wav or dub_<id>.wav.")
            print("Missing segment IDs: " + ", ".join(map(str, missing)))
            return 1
        print(f"SUCCESS: all required chunks are present in {chunk_dir}")
        return 0

    if backend == "custom_command":
        command_template = get_nested(cfg, "tts.custom_command", "")
        if not command_template:
            raise RuntimeError("tts.backend is custom_command but tts.custom_command is empty")
        run_custom_command(segments, Path(chunk_dir), command_template, overwrite=overwrite)
        return 0

    raise RuntimeError(f"Unsupported tts.backend: {backend!r}. Supported: manual, custom_command")


if __name__ == "__main__":
    sys.exit(main())
