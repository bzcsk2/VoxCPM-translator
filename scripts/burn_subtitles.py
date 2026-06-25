from __future__ import annotations

import json
import re
import subprocess

from common import ensure_parent, get_nested, load_config, parse_args, timestamp_to_ms

PASSTHROUGH = {"[Music]", "[Human Sounds]", "[Silence]", "[Human sounds]"}


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


def main() -> None:
    args = parse_args("Generate ASS subtitles and burn them into the dubbed video")
    cfg = load_config(args.config)
    refined_json = get_nested(cfg, "paths.refined_json")
    ass_file = get_nested(cfg, "paths.subtitle_ass")
    video_in = get_nested(cfg, "paths.final_video")
    video_out = get_nested(cfg, "paths.subtitled_video")
    max_chars = int(get_nested(cfg, "subtitles.max_chars_per_line", 42))
    font = get_nested(cfg, "subtitles.font_name", "Arial")
    size = get_nested(cfg, "subtitles.font_size", 60)
    pos_x = get_nested(cfg, "subtitles.pos_x", 960)
    pos_y = get_nested(cfg, "subtitles.pos_y", 930)
    color_text = get_nested(cfg, "subtitles.color_text", "&H00FFFFFF")
    color_outline = get_nested(cfg, "subtitles.color_outline", "&H00000000")
    outline_size = get_nested(cfg, "subtitles.outline_size", 2)

    with open(refined_json, encoding="utf-8") as f:
        segments = json.load(f)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{color_text},&H000000FF,{color_outline},&H00000000,0,0,0,0,100,100,0,0,1,{outline_size},0,2,10,10,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in segments:
        en = seg.get("en", "").strip()
        if not en or en in PASSTHROUGH:
            continue
        lines = [ass_escape(line) for line in split_into_lines(en, max_chars)]
        text = "\\N".join(lines)
        events.append(
            f"Dialogue: 0,{ms_to_ass(timestamp_to_ms(seg['start']))},{ms_to_ass(timestamp_to_ms(seg['end']))},Default,,0,0,0,,{{\\pos({pos_x},{pos_y})}}{text}"
        )

    ensure_parent(ass_file)
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

    subprocess.run(["ffmpeg", "-y", "-i", video_in, "-vf", f"ass={ass_file}", "-c:a", "copy", video_out], check=True)
    print(f"Done: {video_out}")


if __name__ == "__main__":
    main()
