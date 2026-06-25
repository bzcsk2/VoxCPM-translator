from __future__ import annotations

import json
import sys
from typing import Any

from common import get_nested, load_config, parse_args


IMMUTABLE_KEYS = ["id", "start", "end", "speaker", "text_zh"]


def verify_alignment(asr_data: list[dict[str, Any]], refined_data: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(asr_data) != len(refined_data):
        errors.append(f"ASR has {len(asr_data)} rows, refined data has {len(refined_data)} rows.")
        return errors

    for idx, (src, out) in enumerate(zip(asr_data, refined_data)):
        for key in IMMUTABLE_KEYS:
            if src.get(key) != out.get(key):
                errors.append(f"row {idx} key {key!r} mismatch: {src.get(key)!r} != {out.get(key)!r}")
        en = out.get("en", "")
        if not en or en in {"[Error]", "[Translation Failed]"}:
            errors.append(f"row {idx} ID {out.get('id')} has empty/error translation.")
    return errors


def main() -> int:
    args = parse_args("Verify ASR and refined translation JSON alignment")
    cfg = load_config(args.config)
    asr_file = get_nested(cfg, "paths.asr_json")
    refined_file = get_nested(cfg, "paths.refined_json")

    with open(asr_file, "r", encoding="utf-8") as f:
        asr_data = json.load(f)
    with open(refined_file, "r", encoding="utf-8") as f:
        refined_data = json.load(f)

    errors = verify_alignment(asr_data, refined_data)
    if errors:
        for error in errors:
            print(f"FAILED: {error}")
        return 1

    print(f"SUCCESS: {len(refined_data)} rows verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
