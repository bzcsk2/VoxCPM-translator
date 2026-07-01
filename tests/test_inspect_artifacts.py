from __future__ import annotations

import json
from pathlib import Path

import inspect_artifacts


def _segments() -> list[dict]:
    return [
        {
            "id": 0,
            "start": "00:00:00.000",
            "end": "00:00:01.000",
            "speaker": "A",
            "text_zh": "你好",
            "zh_fixed": "你好。",
            "en": "Hello.",
        },
        {
            "id": 1,
            "start": "00:00:01.000",
            "end": "00:00:02.000",
            "speaker": "A",
            "text_zh": "[Music]",
            "zh_fixed": "[Music]",
            "en": "[Music]",
        },
        {
            "id": 2,
            "start": "00:00:02.000",
            "end": "00:00:04.000",
            "speaker": "B",
            "text_zh": "再见",
            "zh_fixed": "再见。",
            "en": "Goodbye.",
        },
    ]


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_summarize_segments_counts_speakers_markers_and_duration(tmp_path: Path) -> None:
    path = tmp_path / "refined.json"
    write_json(path, _segments())

    summary, segments, errors = inspect_artifacts.summarize_segments(path, refined=True)

    assert errors == []
    assert len(segments) == 3
    assert summary.exists is True
    assert summary.count == 3
    assert summary.spoken_count == 2
    assert summary.non_spoken_count == 1
    assert summary.speaker_counts == {"A": 2, "B": 1}
    assert summary.marker_counts == {"[Music]": 1}
    assert summary.duration_seconds == 4.0
    assert summary.max_segment_duration_seconds == 2.0


def test_summarize_segments_reports_load_errors(tmp_path: Path) -> None:
    summary, segments, errors = inspect_artifacts.summarize_segments(tmp_path / "missing.json")

    assert summary.exists is False
    assert segments == []
    assert errors


def test_summarize_chunks_reports_missing_and_extra(tmp_path: Path) -> None:
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    (chunk_dir / "raw_0.wav").write_bytes(b"wav")
    (chunk_dir / "raw_99.wav").write_bytes(b"wav")

    summary, errors = inspect_artifacts.summarize_chunks(chunk_dir, _segments())

    assert errors == []
    assert summary.exists is True
    assert summary.required_count == 2
    assert summary.present_count == 1
    assert summary.missing_count == 1
    assert summary.missing_ids == [2]
    assert summary.extra_chunk_count == 1
    assert summary.extra_chunks == ["raw_99.wav"]


def test_collect_report_uses_configured_paths(monkeypatch, tmp_path: Path) -> None:
    asr_path = tmp_path / "asr.json"
    refined_path = tmp_path / "refined.json"
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    asr = [{k: v for k, v in row.items() if k not in {"zh_fixed", "en"}} for row in _segments()]
    refined = _segments()
    write_json(asr_path, asr)
    write_json(refined_path, refined)
    (chunk_dir / "raw_0.wav").write_bytes(b"wav")
    (chunk_dir / "raw_2.wav").write_bytes(b"wav")

    monkeypatch.setattr(
        inspect_artifacts,
        "load_config",
        lambda path: {
            "paths": {
                "asr_json": str(asr_path),
                "refined_json": str(refined_path),
                "dub_chunk_dir": str(chunk_dir),
            }
        },
    )

    report = inspect_artifacts.collect_report("config.yaml")

    assert report["asr"]["count"] == 3
    assert report["refined"]["spoken_count"] == 2
    assert report["chunks"]["missing_count"] == 0
    assert report["validation_summary"]["ERROR"] == 0


def test_render_markdown_contains_key_sections() -> None:
    report = {
        "config": "config.yaml",
        "paths": {"asr_json": "asr.json", "refined_json": "refined.json", "chunk_dir": "chunks"},
        "asr": inspect_artifacts.SegmentSummary(True, "asr.json", count=1, spoken_count=1, speaker_counts={"A": 1}, marker_counts={}).to_dict(),
        "refined": inspect_artifacts.SegmentSummary(True, "refined.json", count=1, spoken_count=1, speaker_counts={"A": 1}, marker_counts={}).to_dict(),
        "chunks": inspect_artifacts.ChunkSummary(True, "chunks", required_count=1, present_count=1).to_dict(),
        "load_errors": [],
        "validation_summary": {"ERROR": 0, "WARN": 0, "INFO": 0},
        "validation_issues": [],
    }

    rendered = inspect_artifacts.render_markdown(report)

    assert "# Artifact inspection report" in rendered
    assert "## ASR segments" in rendered
    assert "## Refined segments" in rendered
    assert "## TTS chunks" in rendered
    assert "## Validation" in rendered
