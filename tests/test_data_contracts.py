from pathlib import Path

from data_contracts import (
    has_errors,
    missing_tts_chunk_ids,
    timestamp_to_seconds,
    validate_alignment,
    validate_segment_list,
    validate_tts_chunks,
)


def _asr_segment(seg_id: int = 0) -> dict:
    return {
        "id": seg_id,
        "start": "00:00:00.000",
        "end": "00:00:01.000",
        "speaker": "spk1",
        "text_zh": "你好",
    }


def _refined_segment(seg_id: int = 0, en: str = "Hello.") -> dict:
    segment = _asr_segment(seg_id)
    segment.update({"zh_fixed": "你好。", "en": en})
    return segment


def test_timestamp_to_seconds_accepts_pipeline_format() -> None:
    assert timestamp_to_seconds("00:01:02.345") == 62.345
    assert timestamp_to_seconds("bad") is None


def test_validate_segment_list_catches_bad_timestamp_and_missing_key() -> None:
    segments = [{"id": 0, "start": "0", "end": "00:00:01.000", "speaker": "spk1"}]

    issues = validate_segment_list(segments, "asr")

    assert has_errors(issues)
    assert any(issue.path == "asr[0].text_zh" for issue in issues)
    assert any(issue.path == "asr[0].start" for issue in issues)


def test_validate_alignment_catches_immutable_mismatch() -> None:
    asr = [_asr_segment()]
    refined = [_refined_segment()]
    refined[0]["speaker"] = "spk2"

    issues = validate_alignment(asr, refined)

    assert has_errors(issues)
    assert any(issue.path == "alignment[0].speaker" for issue in issues)


def test_missing_tts_chunk_ids_skips_non_spoken_markers(tmp_path: Path) -> None:
    chunk_dir = tmp_path / "chunks"
    chunk_dir.mkdir()
    segments = [_refined_segment(0), _refined_segment(1, en="[Music]")]

    assert missing_tts_chunk_ids(segments, chunk_dir) == [0]
    (chunk_dir / "dub_0.wav").write_bytes(b"wav")
    assert missing_tts_chunk_ids(segments, chunk_dir) == []


def test_validate_tts_chunks_reports_missing_directory(tmp_path: Path) -> None:
    issues = validate_tts_chunks([_refined_segment()], tmp_path / "missing")

    assert has_errors(issues)
    assert any(issue.path == "tts_chunks" for issue in issues)
