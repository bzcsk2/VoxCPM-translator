from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from common import get_nested, load_config, parse_args, timestamp_to_ms
from data_contracts import is_non_spoken_segment, load_json_array, segment_text
from runtime_checks import ensure_parent_dir, require_file, require_positive_float


def ms_to_ass(ms: int) -> str:
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h}:{m:02d}:{s:02d}.{ms // 10:02d}"


def ass_escape(text: str) -> str:
    # ASS uses braces for override tags and backslash sequences for drawing/formatting commands.
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def split_into_lines(text: str, max_chars: int) -> list[str]:
    if max_chars <= 0:
        raise ValueError(f"subtitles.max_chars_per_line must be positive; got {max_chars}")
    sentences = re.split(r"(?<=[.!?…—])\s+", text.strip())
    lines: list[str] = []
    for sent in sentences:
        if len(sent) <= max_chars:
            lines.append(sent)
            continue
        current = ""
        for word in sent.split():
            test = (current + " " + word).strip()
            if len(test) <= max_chars:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return [line for line in lines if line] or [text.strip()]


def subtitle_segment_errors(segments: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for idx, segment in enumerate(segments):
        for key in ("start", "end", "en"):
            if key not in segment:
                errors.append(f"segment[{idx}].{key}: missing required subtitle field")
        if "start" in segment and "end" in segment:
            try:
                start_ms = timestamp_to_ms(str(segment["start"]))
                end_ms = timestamp_to_ms(str(segment["end"]))
            except Exception as exc:
                errors.append(f"segment[{idx}]: invalid timestamp: {exc}")
            else:
                if end_ms <= start_ms:
                    errors.append(f"segment[{idx}]: end must be after start")
    return errors


def validate_subtitle_segments(segments: list[dict[str, Any]]) -> None:
    errors = subtitle_segment_errors(segments)
    if errors:
        raise ValueError("Refined JSON failed subtitle validation:\n" + "\n".join(errors))


def validate_subtitle_inputs(
    refined_json: str,
    video_in: str,
    ass_file: str,
    video_out: str,
    max_chars: Any,
    font_size: Any,
    outline_size: Any,
) -> tuple[Path, Path, Path, Path, int, float, float]:
    refined_path = require_file(refined_json, "paths.refined_json")
    input_video = require_file(video_in, "paths.final_video")
    ass_path = ensure_parent_dir(ass_file, "paths.subtitle_ass")
    output_video = ensure_parent_dir(video_out, "paths.subtitled_video")
    max_chars_int = int(require_positive_float(max_chars, "subtitles.max_chars_per_line"))
    size = require_positive_float(font_size, "subtitles.font_size")
    outline = require_positive_float(outline_size, "subtitles.outline_size")
    return refined_path, input_video, ass_path, output_video, max_chars_int, size, outline


def build_ass_events(segments: list[dict[str, Any]], max_chars: int, pos_x: Any, pos_y: Any) -> list[str]:
    events: list[str] = []
    for seg in segments:
        if is_non_spoken_segment(seg):
            continue
        en = segment_text(seg)
        if not en:
            continue
        lines = [ass_escape(line) for line in split_into_lines(en, max_chars)]
        text = "\\N".join(lines)
        events.append(
            f"Dialogue: 0,{ms_to_ass(timestamp_to_ms(seg['start']))},{ms_to_ass(timestamp_to_ms(seg['end']))},Default,,0,0,0,,{{\\pos({pos_x},{pos_y})}}{text}"
        )
    return events


def main() -> None:
    args = parse_args("Generate ASS subtitles and burn them into the dubbed video")
    cfg = load_config(args.config)
    refined_json = get_nested(cfg, "paths.refined_json")
    ass_file = get_nested(cfg, "paths.subtitle_ass")
    video_in = get_nested(cfg, "paths.final_video")
    video_out = get_nested(cfg, "paths.subtitled_video")
    max_chars = get_nested(cfg, "subtitles.max_chars_per_line", 42)
    font = get_nested(cfg, "subtitles.font_name", "Arial")
    size = get_nested(cfg, "subtitles.font_size", 60)
    pos_x = get_nested(cfg, "subtitles.pos_x", 960)
    pos_y = get_nested(cfg, "subtitles.pos_y", 930)
    color_text = get_nested(cfg, "subtitles.color_text", "&H00FFFFFF")
    color_outline = get_nested(cfg, "subtitles.color_outline", "&H00000000")
    outline_size = get_nested(cfg, "subtitles.outline_size", 2)

    refined_path, input_video, ass_path, output_video, max_chars_int, font_size, outline = validate_subtitle_inputs(
        refined_json,
        video_in,
        ass_file,
        video_out,
        max_chars,
        size,
        outline_size,
    )

    segments = load_json_array(refined_path)
    validate_subtitle_segments(segments)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{color_text},&H000000FF,{color_outline},&H00000000,0,0,0,0,100,100,0,0,1,{outline},0,2,10,10,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = build_ass_events(segments, max_chars_int, pos_x, pos_y)

    ass_path.write_text(header + "\n".join(events), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-i", str(input_video), "-vf", f"ass={ass_path}", "-c:a", "copy", str(output_video)], check=True)
    print(f"Subtitle summary: segments={len(segments)}, events={len(events)}, ass={ass_path}")
    print(f"Done: {output_video}")


if __name__ == "__main__":
    main()
