import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("burn_subtitles", ROOT / "scripts" / "burn_subtitles.py")
burn_subtitles = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(burn_subtitles)


def _segment(en: str = "Hello world.") -> dict:
    return {
        "id": 0,
        "start": "00:00:00.000",
        "end": "00:00:01.000",
        "speaker": "spk1",
        "text_zh": "你好",
        "zh_fixed": "你好。",
        "en": en,
    }


def test_ass_escape_protects_override_syntax() -> None:
    assert burn_subtitles.ass_escape(r"{\pos(1,2)}") == r"\{\\pos(1,2)\}"


def test_split_into_lines_rejects_non_positive_limit() -> None:
    with pytest.raises(ValueError):
        burn_subtitles.split_into_lines("hello", 0)


def test_build_ass_events_skips_non_spoken_segments() -> None:
    events = burn_subtitles.build_ass_events([_segment("[Music]"), _segment("Hello world.")], 42, 960, 930)

    assert len(events) == 1
    assert "Hello world." in events[0]
    assert "[Music]" not in events[0]


def test_validate_subtitle_inputs_creates_ass_parent(tmp_path: Path) -> None:
    refined = tmp_path / "refined.json"
    video = tmp_path / "final.mp4"
    refined.write_text("[]", encoding="utf-8")
    video.write_bytes(b"video")

    result = burn_subtitles.validate_subtitle_inputs(
        str(refined),
        str(video),
        str(tmp_path / "nested" / "subtitles.ass"),
        str(tmp_path / "out.mp4"),
        42,
        60,
        2,
    )

    assert result[2].parent.exists()


def test_validate_subtitle_segments_accepts_minimal_subtitle_contract() -> None:
    burn_subtitles.validate_subtitle_segments(
        [
            {
                "start": "00:00:00.000",
                "end": "00:00:01.000",
                "en": "Hello.",
            }
        ]
    )


def test_validate_subtitle_segments_rejects_bad_timestamp() -> None:
    with pytest.raises(ValueError):
        burn_subtitles.validate_subtitle_segments([{"start": "bad", "end": "00:00:01.000", "en": "Hello."}])
