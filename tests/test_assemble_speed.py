import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("assemble_final", ROOT / "scripts" / "06_assemble_final.py")
assemble_final = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(assemble_final)


def test_atempo_filters_splits_large_ratio() -> None:
    assert assemble_final.atempo_filters(4.5) == ["atempo=2.0", "atempo=2.25"]


def test_atempo_filters_splits_small_ratio() -> None:
    assert assemble_final.atempo_filters(0.25) == ["atempo=0.5", "atempo=0.5"]


def test_speed_adjustment_ratio_skips_near_identity() -> None:
    assert assemble_final.speed_adjustment_ratio(1.0, 1.0, 0.7) is None


def test_speed_adjustment_ratio_uses_current_over_target_for_long_audio() -> None:
    assert assemble_final.speed_adjustment_ratio(2.0, 1.0, 0.7) == 2.0


def test_speed_adjustment_ratio_clamps_short_audio_to_minimum() -> None:
    assert assemble_final.speed_adjustment_ratio(0.2, 1.0, 0.7) == 0.7


def test_speed_adjustment_ratio_returns_none_for_invalid_duration() -> None:
    assert assemble_final.speed_adjustment_ratio(0.0, 1.0, 0.7) is None
    assert assemble_final.speed_adjustment_ratio(1.0, 0.0, 0.7) is None
