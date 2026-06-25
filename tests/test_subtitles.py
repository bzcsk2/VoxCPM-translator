from burn_subtitles import ass_escape, ms_to_ass, split_into_lines


def test_ms_to_ass() -> None:
    assert ms_to_ass(3723450) == "1:02:03.45"


def test_ass_escape_protects_override_syntax() -> None:
    assert ass_escape("Hello {tag}") == r"Hello \{tag\}"


def test_split_into_lines_keeps_short_text() -> None:
    assert split_into_lines("Short line.", 42) == ["Short line."]
