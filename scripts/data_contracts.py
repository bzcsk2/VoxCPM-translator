from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

ASR_REQUIRED_KEYS = ["id", "start", "end", "speaker", "text_zh"]
REFINED_REQUIRED_KEYS = [*ASR_REQUIRED_KEYS, "zh_fixed", "en"]
IMMUTABLE_KEYS = ["id", "start", "end", "speaker", "text_zh"]
NON_SPOKEN_MARKERS = {"[Music]", "[Human Sounds]", "[Human sounds]", "[Silence]"}
FAILED_TRANSLATIONS = {"[Error]", "[Translation Failed]"}
TIMESTAMP_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}$")


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_json_array(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{source} must contain a JSON array")
    for idx, row in enumerate(data):
        if not isinstance(row, dict):
            raise ValueError(f"{source} row {idx} must be a JSON object")
    return data


def timestamp_to_seconds(value: str) -> float | None:
    if not isinstance(value, str) or not TIMESTAMP_PATTERN.match(value):
        return None
    hours, minutes, seconds = value.split(":")
    try:
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return None


def segment_text(segment: dict[str, Any]) -> str:
    return str(segment.get("en") or segment.get("zh_fixed") or segment.get("text_zh") or "").strip()


def is_non_spoken_segment(segment: dict[str, Any]) -> bool:
    return segment_text(segment) in NON_SPOKEN_MARKERS


def _issue(level: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(level=level, path=path, message=message)


def _validate_required_keys(segment: dict[str, Any], idx: int, keys: Iterable[str], schema_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key in keys:
        if key not in segment:
            issues.append(_issue(ERROR, f"{schema_name}[{idx}].{key}", "missing required key"))
    return issues


def _validate_id(segment: dict[str, Any], idx: int, schema_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seg_id = segment.get("id")
    if seg_id is None or seg_id == "":
        issues.append(_issue(ERROR, f"{schema_name}[{idx}].id", "id must be present"))
    elif not isinstance(seg_id, int):
        issues.append(_issue(WARN, f"{schema_name}[{idx}].id", f"id is {type(seg_id).__name__}; integer IDs are recommended"))
    elif seg_id != idx:
        issues.append(_issue(WARN, f"{schema_name}[{idx}].id", f"id is {seg_id}; expected sequential id {idx}"))
    return issues


def _validate_timestamps(segment: dict[str, Any], idx: int, schema_name: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    start = segment.get("start")
    end = segment.get("end")
    start_seconds = timestamp_to_seconds(start) if isinstance(start, str) else None
    end_seconds = timestamp_to_seconds(end) if isinstance(end, str) else None

    if start_seconds is None:
        issues.append(_issue(ERROR, f"{schema_name}[{idx}].start", f"invalid timestamp: {start!r}; expected HH:MM:SS.mmm"))
    if end_seconds is None:
        issues.append(_issue(ERROR, f"{schema_name}[{idx}].end", f"invalid timestamp: {end!r}; expected HH:MM:SS.mmm"))
    if start_seconds is not None and end_seconds is not None and end_seconds <= start_seconds:
        issues.append(_issue(ERROR, f"{schema_name}[{idx}]", f"end must be after start: {start!r} -> {end!r}"))
    return issues


def _validate_text_field(segment: dict[str, Any], idx: int, schema_name: str, key: str, required: bool = True) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    value = segment.get(key)
    if value is None:
        if required:
            issues.append(_issue(ERROR, f"{schema_name}[{idx}].{key}", "missing text value"))
        return issues
    if not isinstance(value, str):
        issues.append(_issue(ERROR, f"{schema_name}[{idx}].{key}", f"expected string, got {type(value).__name__}"))
        return issues
    if required and not value.strip():
        issues.append(_issue(ERROR, f"{schema_name}[{idx}].{key}", "text value is empty"))
    return issues


def validate_segment_list(segments: list[dict[str, Any]], schema_name: str, refined: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not segments:
        issues.append(_issue(WARN, schema_name, "segment list is empty"))
        return issues

    required_keys = REFINED_REQUIRED_KEYS if refined else ASR_REQUIRED_KEYS
    seen_ids: set[Any] = set()
    previous_end: float | None = None

    for idx, segment in enumerate(segments):
        issues.extend(_validate_required_keys(segment, idx, required_keys, schema_name))
        issues.extend(_validate_id(segment, idx, schema_name))
        issues.extend(_validate_timestamps(segment, idx, schema_name))
        issues.extend(_validate_text_field(segment, idx, schema_name, "speaker"))
        issues.extend(_validate_text_field(segment, idx, schema_name, "text_zh"))

        seg_id = segment.get("id")
        if seg_id in seen_ids:
            issues.append(_issue(ERROR, f"{schema_name}[{idx}].id", f"duplicate segment id: {seg_id!r}"))
        seen_ids.add(seg_id)

        start_seconds = timestamp_to_seconds(segment.get("start")) if isinstance(segment.get("start"), str) else None
        end_seconds = timestamp_to_seconds(segment.get("end")) if isinstance(segment.get("end"), str) else None
        if previous_end is not None and start_seconds is not None and start_seconds < previous_end:
            issues.append(_issue(WARN, f"{schema_name}[{idx}].start", "segment overlaps the previous segment"))
        if end_seconds is not None:
            previous_end = end_seconds

        if refined:
            issues.extend(_validate_text_field(segment, idx, schema_name, "zh_fixed"))
            issues.extend(_validate_text_field(segment, idx, schema_name, "en"))
            en = str(segment.get("en", "")).strip()
            if en in FAILED_TRANSLATIONS:
                issues.append(_issue(ERROR, f"{schema_name}[{idx}].en", f"translation failed marker: {en}"))

    return issues


def validate_alignment(asr_segments: list[dict[str, Any]], refined_segments: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_segment_list(asr_segments, "asr", refined=False))
    issues.extend(validate_segment_list(refined_segments, "refined", refined=True))

    if len(asr_segments) != len(refined_segments):
        issues.append(_issue(ERROR, "alignment", f"ASR has {len(asr_segments)} rows, refined data has {len(refined_segments)} rows"))
        return issues

    for idx, (src, out) in enumerate(zip(asr_segments, refined_segments)):
        for key in IMMUTABLE_KEYS:
            if src.get(key) != out.get(key):
                issues.append(_issue(ERROR, f"alignment[{idx}].{key}", f"{src.get(key)!r} != {out.get(key)!r}"))
    return issues


def expected_chunk_paths(chunk_dir: str | Path, seg_id: Any) -> tuple[Path, Path]:
    directory = Path(chunk_dir)
    return directory / f"raw_{seg_id}.wav", directory / f"dub_{seg_id}.wav"


def chunk_exists(chunk_dir: str | Path, seg_id: Any) -> bool:
    raw_path, dub_path = expected_chunk_paths(chunk_dir, seg_id)
    return raw_path.exists() or dub_path.exists()


def missing_tts_chunk_ids(refined_segments: list[dict[str, Any]], chunk_dir: str | Path) -> list[Any]:
    missing: list[Any] = []
    for segment in refined_segments:
        if is_non_spoken_segment(segment):
            continue
        seg_id = segment.get("id")
        if not chunk_exists(chunk_dir, seg_id):
            missing.append(seg_id)
    return missing


def validate_tts_chunks(refined_segments: list[dict[str, Any]], chunk_dir: str | Path) -> list[ValidationIssue]:
    issues = validate_segment_list(refined_segments, "refined", refined=True)
    directory = Path(chunk_dir)
    if not directory.exists():
        issues.append(_issue(ERROR, "tts_chunks", f"chunk directory does not exist: {directory}"))
        return issues
    if not directory.is_dir():
        issues.append(_issue(ERROR, "tts_chunks", f"chunk path is not a directory: {directory}"))
        return issues

    missing = missing_tts_chunk_ids(refined_segments, directory)
    if missing:
        preview = ", ".join(map(str, missing[:10]))
        suffix = "..." if len(missing) > 10 else ""
        issues.append(_issue(ERROR, "tts_chunks", f"missing chunks for segment IDs: {preview}{suffix}"))
    return issues


def has_errors(issues: Iterable[ValidationIssue]) -> bool:
    return any(issue.level == ERROR for issue in issues)


def summarize_issues(issues: Iterable[ValidationIssue]) -> dict[str, int]:
    summary = {ERROR: 0, WARN: 0, INFO: 0}
    for issue in issues:
        summary[issue.level] = summary.get(issue.level, 0) + 1
    return summary


def render_issues(issues: Iterable[ValidationIssue], include_summary: bool = True) -> str:
    materialized = list(issues)
    lines = [f"[{issue.level}] {issue.path}: {issue.message}" for issue in materialized]
    if include_summary:
        summary = summarize_issues(materialized)
        lines.append(f"[SUMMARY] ERROR={summary.get(ERROR, 0)} WARN={summary.get(WARN, 0)} INFO={summary.get(INFO, 0)}")
    return "\n".join(lines)
