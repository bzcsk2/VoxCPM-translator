from __future__ import annotations

import subprocess
from pathlib import Path

from common import ensure_parent, get_nested, load_config, parse_args, require_nested


def main() -> None:
    args = parse_args("Extract a WAV track from the configured input video")
    cfg = load_config(args.config)

    input_video = Path(require_nested(cfg, "paths.input_video"))
    input_wav = Path(require_nested(cfg, "paths.input_wav"))
    sample_rate = str(get_nested(cfg, "audio_extract.sample_rate", 44100))
    channels = str(get_nested(cfg, "audio_extract.channels", 2))

    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    ensure_parent(input_wav)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vn",
        "-ac",
        channels,
        "-ar",
        sample_rate,
        str(input_wav),
    ]
    subprocess.run(cmd, check=True)
    print(f"Done: {input_wav}")


if __name__ == "__main__":
    main()
