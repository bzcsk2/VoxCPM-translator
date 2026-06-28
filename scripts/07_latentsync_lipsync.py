from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from common import get_nested, load_config, parse_args
from runtime_checks import ensure_parent_dir, require_dir, require_file


def main() -> None:
    args = parse_args("Optional LatentSync lip-sync step")
    cfg = load_config(args.config)

    latentsync_dir = require_dir(get_nested(cfg, "models.latentsync_dir"), "models.latentsync_dir")
    video_input = require_file(get_nested(cfg, "paths.input_video"), "paths.input_video")
    audio_input = require_file(get_nested(cfg, "paths.temp_mixed_wav"), "paths.temp_mixed_wav")
    video_output = ensure_parent_dir(get_nested(cfg, "paths.lipsync_video"), "paths.lipsync_video")

    inference_py = latentsync_dir / "scripts" / "inference.py"
    if not inference_py.exists():
        raise FileNotFoundError(f"LatentSync inference script not found: {inference_py}")

    cmd = [
        sys.executable,
        str(inference_py),
        "--video_path",
        str(video_input),
        "--audio_path",
        str(audio_input),
        "--video_out_path",
        str(video_output),
    ]
    env = os.environ.copy()
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    subprocess.run(cmd, check=True, env=env)
    print(f"Done: {video_output}")


if __name__ == "__main__":
    main()
