from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import get_nested, load_config
from data_contracts import (
    FAILED_TRANSLATIONS,
    NON_SPOKEN_MARKERS,
    chunk_exists,
    is_non_spoken_segment,
    load_json_array,
    missing_tts_chunk_ids,
    segment_text,
    summarize_issues,
    timestamp_to_seconds,
    validate_alignment,
    validate_segment_list,
    validate_tts_chunks,
)


@dataclass(frozen=True)
class SegmentSummary:
    exists: bool
    path: str | None
    count: int = 0
    spoken_count: int = 0
    non_spoken_count: int = 0
    failed_translation_count: int = 0
    empty_text_count: int = 0
    speaker_counts: dict[str, int] | None = None
    marker_counts: dict[str, int] | None = None
    start: str | None = None
    end: str | None = None
    duration_seconds: float | None = None
    max_segment_duration_seconds: float | None = None
    avg_segment_duration_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkSummary:
    exists: bool
    path: str | None
    required_count: int = 0
    present_count: int = 0
    missing_count: int = 0
    missing_ids: list[Any] | None = None
    extra_chunk_count: int = 0
    extra_chunks: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect pipeline JSON artifacts and TTS chunk coverage")
    parser.add_argument("--config", default="configs/default.yaml", help="Path to YAML config file")
    parser.add_argument("--asr-json", help="Override paths.asr_json")
    parser.add_argument("--refined-json", help="Override paths.refined_json")
    parser.add_argument("--chunk-dir", help="Override paths.dub_chunk_dir")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--output", help="Optional file path to write the report")
    return parser.parse_args()


def _duration(start: Any, end: Any) -> float | None:
    start_seconds = timestamp_to_seconds(start) if isinstance(start, str) else None
    end_seconds = timestamp_to_seconds(end) if isinstance(end, str) else None
    if start_seconds is None or end_seconds is None or end_seconds < start_seconds:
        return None
    return round(end_seconds - start_seconds, 3)


def summarize_segments(path: str | Path | None, refined: bool = False) -> tuple[SegmentSummary, list[dict[str, Any]], list[str]]:
    if not path:
        return SegmentSummary(False, None), [], ["path is not configured"]

    source = Path(path)
    if not source.exists():
        return SegmentSummary(False, str(source)), [], [f"file does not exist: {source}"]

    try:
        segments = load_json_array(source)
    except Exception as exc:
        return SegmentSummary(False, str(source)), [], [f"cannot load JSON array: {exc}"]

    speaker_counts: Counter[str] = Counter()
    marker_counts: Counter[str] = Counter()
    empty_text_count = 0
    failed_translation_count = 0
    durations: list[float] = []

    for segment in segments:
        speaker_counts[str(segment.get("speaker", ""))] += 1
        text = segment_text(segment)
        if not text:
            empty_text_count += 1
        if text in NON_SPOKEN_MARKERS:
            marker_counts[text] += 1
        if refined and str(segment.get("en", "")).strip() in FAILED_TRANSLATIONS:
            failed_translation_count += 1
        duration = _duration(segment.get("start"), segment.get("end"))
        if duration is not None:
            durations.append(duration)

    first_start = str(segments[0].get("start")) if segments else None
    last_end = str(segments[-1].get("end")) if segments else None
    total_duration = _duration(first_start, last_end) if first_start and last_end else None
    non_spoken_count = sum(1 for segment in segments if is_non_spoken_segment(segment))

    summary = SegmentSummary(
        exists=True,
        path=str(source),
        count=len(segments),
        spoken_count=len(segments) - non_spoken_count,
        non_spoken_count=non_spoken_count,
        failed_translation_count=failed_translation_count,
        empty_text_count=empty_text_count,
        speaker_counts=dict(sorted(speaker_counts.items())),
        marker_counts=dict(sorted(marker_counts.items())),
        start=first_start,
        end=last_end,
        duration_seconds=total_duration,
        max_segment_duration_seconds=max(durations) if durations else None,
        avg_segment_duration_seconds=round(sum(durations) / len(durations), 3) if durations else None,
    )
    return summary, segments, []


def _chunk_id_from_name(path: Path) -> str | None:
    stem = path.stem
    for prefix in ("raw_", "dub_"):
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    return None


def summarize_chunks(chunk_dir: str | Path | None, refined_segments: list[dict[str, Any]]) -> tuple[ChunkSummary, list[str]]:
    if not chunk_dir:
        return ChunkSummary(False, None), ["chunk directory is not configured"]

    directory = Path(chunk_dir)
    if not directory.exists():
        return ChunkSummary(False, str(directory)), [f"chunk directory does not exist: {directory}"]
    if not directory.is_dir():
        return ChunkSummary(False, str(directory)), [f"chunk path is not a directory: {directory}"]

    required_ids = [segment.get("id") for segment in refined_segments if not is_non_spoken_segment(segment)]
    missing_ids = missing_tts_chunk_ids(refined_segments, directory)
    present_count = sum(1 for seg_id in required_ids if chunk_exists(directory, seg_id))

    expected_names = {f"raw_{seg_id}.wav" for seg_id in required_ids} | {f"dub_{seg_id}.wav" for seg_id in required_ids}
    extra_chunks = sorted(path.name for path in directory.glob("*.wav") if path.name not in expected_names and _chunk_id_from_name(path) is not None)

    return (
        ChunkSummary(
            exists=True,
            path=str(directory),
            required_count=len(required_ids),
            present_count=present_count,
            missing_count=len(missing_ids),
            missing_ids=missing_ids,
            extra_chunk_count=len(extra_chunks),
            extra_chunks=extra_chunks[:20],
        ),
        [],
    )


def collect_report(config_path: str, asr_json: str | None = None, refined_json: str | None = None, chunk_dir: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    asr_path = asr_json or get_nested(cfg, "paths.asr_json")
    refined_path = refined_json or get_nested(cfg, "paths.refined_json")
    chunks_path = chunk_dir or get_nested(cfg, "paths.dub_chunk_dir")

    asr_summary, asr_segments, asr_load_errors = summarize_segments(asr_path, refined=False)
    refined_summary, refined_segments, refined_load_errors = summarize_segments(refined_path, refined=True)
    chunk_summary, chunk_load_errors = summarize_chunks(chunks_path, refined_segments)

    issues = []
    if asr_segments:
        issues.extend(validate_segment_list(asr_segments, "asr", refined=False))
    if refined_segments:
        issues.extend(validate_segment_list(refined_segments, "refined", refined=True))
    if asr_segments and refined_segments:
        issues.extend(validate_alignment(asr_segments, refined_segments))
    if refined_segments and chunk_summary.exists:
        issues.extend(validate_tts_chunks(refined_segments, chunks_path))

    return {
        "config": config_path,
        "paths": {
            "asr_json": str(asr_path) if asr_path else None,
            "refined_json": str(refined_path) if refined_path else None,
            "chunk_dir": str(chunks_path) if chunks_path else None,
        },
        "asr": asr_summary.to_dict(),
        "refined": refined_summary.to_dict(),
        "chunks": chunk_summary.to_dict(),
        "load_errors": asr_load_errors + refined_load_errors + chunk_load_errors,
        "validation_summary": summarize_issues(issues),
        "validation_issues": [issue.to_dict() for issue in issues],
    }


def _dict_items_text(data: dict[str, int] | None) -> str:
    if not data:
        return "-"
    return ", ".join(f"{key}={value}" for key, value in data.items())


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Artifact inspection report")
    lines.append("")
    lines.append(f"- Config: `{report['config']}`")
    lines.append(f"- ASR JSON: `{report['paths']['asr_json']}`")
    lines.append(f"- Refined JSON: `{report['paths']['refined_json']}`")
    lines.append(f"- Chunk dir: `{report['paths']['chunk_dir']}`")

    load_errors = report.get("load_errors") or []
    if load_errors:
        lines.append("")
        lines.append("## Load errors")
        for error in load_errors:
            lines.append(f"- {error}")

    for key, title in [("asr", "ASR"), ("refined", "Refined")]:
        summary = report[key]
        lines.append("")
        lines.append(f"## {title} segments")
        lines.append(f"- Exists: `{summary['exists']}`")
        lines.append(f"- Count: `{summary['count']}`")
        lines.append(f"- Spoken / non-spoken: `{summary['spoken_count']} / {summary['non_spoken_count']}`")
        lines.append(f"- Time span: `{summary['start']} -> {summary['end']}`")
        lines.append(f"- Duration seconds: `{summary['duration_seconds']}`")
        lines.append(f"- Avg / max segment seconds: `{summary['avg_segment_duration_seconds']} / {summary['max_segment_duration_seconds']}`")
        lines.append(f"- Empty text rows: `{summary['empty_text_count']}`")
        if key == "refined":
            lines.append(f"- Failed translation markers: `{summary['failed_translation_count']}`")
        lines.append(f"- Speakers: `{_dict_items_text(summary['speaker_counts'])}`")
        lines.append(f"- Non-spoken markers: `{_dict_items_text(summary['marker_counts'])}`")

    chunks = report["chunks"]
    lines.append("")
    lines.append("## TTS chunks")
    lines.append(f"- Exists: `{chunks['exists']}`")
    lines.append(f"- Required / present / missing: `{chunks['required_count']} / {chunks['present_count']} / {chunks['missing_count']}`")
    lines.append(f"- Missing IDs: `{', '.join(map(str, chunks['missing_ids'] or [])) or '-'}`")
    lines.append(f"- Extra chunk count: `{chunks['extra_chunk_count']}`")
    lines.append(f"- Extra chunks: `{', '.join(chunks['extra_chunks'] or []) or '-'}`")

    validation_summary = report["validation_summary"]
    lines.append("")
    lines.append("## Validation")
    lines.append(
        f"- Summary: `ERROR={validation_summary.get('ERROR', 0)} WARN={validation_summary.get('WARN', 0)} INFO={validation_summary.get('INFO', 0)}`"
    )
    for issue in report["validation_issues"][:50]:
        lines.append(f"- [{issue['level']}] {issue['path']}: {issue['message']}")
    if len(report["validation_issues"]) > 50:
        lines.append(f"- ... {len(report['validation_issues']) - 50} more issues")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    report = collect_report(args.config, asr_json=args.asr_json, refined_json=args.refined_json, chunk_dir=args.chunk_dir)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
