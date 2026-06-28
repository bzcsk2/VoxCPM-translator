from __future__ import annotations

import argparse
import sys

from common import get_nested, load_config
from data_contracts import has_errors, load_json_array, render_issues, validate_alignment, validate_tts_chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate pipeline JSON and audio chunk artifacts")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config file")
    parser.add_argument("--skip-chunks", action="store_true", help="Validate JSON alignment without checking TTS chunk files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config)
    asr = load_json_array(get_nested(cfg, "paths.asr_json"))
    refined = load_json_array(get_nested(cfg, "paths.refined_json"))
    issues = []
    issues.extend(validate_alignment(asr, refined))
    if not args.skip_chunks:
        issues.extend(validate_tts_chunks(refined, get_nested(cfg, "paths.dub_chunk_dir")))
    if issues:
        print(render_issues(issues))
    if has_errors(issues):
        print("FAILED: artifact validation found errors")
        return 1
    print("SUCCESS: artifact validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
