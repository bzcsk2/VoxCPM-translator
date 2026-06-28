from __future__ import annotations

import sys
from typing import Any

from common import get_nested, load_config, parse_args
from data_contracts import has_errors, load_json_array, render_issues, validate_alignment


IMMUTABLE_KEYS = ["id", "start", "end", "speaker", "text_zh"]


def verify_alignment(asr_data: list[dict[str, Any]], refined_data: list[dict[str, Any]]) -> list[str]:
    """Backward-compatible string API used by older tests and scripts."""
    return [f"{issue.path}: {issue.message}" for issue in validate_alignment(asr_data, refined_data) if issue.level == "ERROR"]


def main() -> int:
    args = parse_args("Verify ASR and refined translation JSON alignment")
    cfg = load_config(args.config)
    asr_file = get_nested(cfg, "paths.asr_json")
    refined_file = get_nested(cfg, "paths.refined_json")

    asr_data = load_json_array(asr_file)
    refined_data = load_json_array(refined_file)

    issues = validate_alignment(asr_data, refined_data)
    if issues:
        print(render_issues(issues))
    if has_errors(issues):
        return 1

    print(f"SUCCESS: {len(refined_data)} rows verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
