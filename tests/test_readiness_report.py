from __future__ import annotations

import readiness_report
from config_checks import CheckResult
from config_schema import SchemaIssue


def test_suggest_next_actions_prioritizes_schema_errors() -> None:
    actions = readiness_report.suggest_next_actions(
        "config.yaml",
        [SchemaIssue("ERROR", "tts.backend", "bad backend")],
        [],
        [],
        None,
        0,
        6,
    )

    assert actions[0].title == "Fix config schema errors"
    assert "check_config_schema.py" in actions[0].command


def test_suggest_next_actions_includes_environment_failures() -> None:
    actions = readiness_report.suggest_next_actions(
        "config.yaml",
        [],
        [CheckResult("FAIL", "ffmpeg", "missing")],
        [],
        None,
        0,
        6,
    )

    assert any(action.title == "Fix environment and local paths" for action in actions)


def test_suggest_next_actions_uses_first_incomplete_stage() -> None:
    actions = readiness_report.suggest_next_actions(
        "config.yaml",
        [],
        [],
        [
            readiness_report.StageReadiness(0, "extract-audio", "complete", "ok"),
            readiness_report.StageReadiness(1, "process-vocals", "missing", "missing vocals"),
        ],
        None,
        0,
        6,
    )

    pipeline_action = next(action for action in actions if action.title == "Run or resume the selected pipeline range")
    assert "process-vocals" in pipeline_action.reason
    assert "--resume --preflight" in pipeline_action.command


def test_suggest_next_actions_reports_ready_when_no_blockers() -> None:
    actions = readiness_report.suggest_next_actions(
        "config.yaml",
        [],
        [],
        [readiness_report.StageReadiness(0, "extract-audio", "complete", "ok")],
        None,
        0,
        0,
    )

    assert actions[0].title == "Selected range appears ready"


def test_collect_report_handles_config_load_error(monkeypatch) -> None:
    monkeypatch.setattr(readiness_report, "load_config", lambda path: (_ for _ in ()).throw(RuntimeError("bad yaml")))

    report = readiness_report.collect_report("bad.yaml")

    assert report["config"]["loaded"] is False
    assert report["blocking"] is True
    assert report["next_actions"][0]["title"] == "Fix config load error"


def test_collect_report_combines_schema_environment_stages_and_artifacts(monkeypatch) -> None:
    monkeypatch.setattr(readiness_report, "load_config", lambda path: {"paths": {"output_dir": "outputs"}})
    monkeypatch.setattr(readiness_report, "validate_config_schema", lambda cfg: [])
    monkeypatch.setattr(readiness_report, "run_environment_checks", lambda cfg: [CheckResult("OK", "ffmpeg", "found")])
    monkeypatch.setattr(
        readiness_report,
        "collect_stage_readiness",
        lambda cfg, start, end: [readiness_report.StageReadiness(0, "extract-audio", "complete", "ok")],
    )
    monkeypatch.setattr(
        readiness_report,
        "collect_artifact_report",
        lambda config_path: {
            "asr": {"count": 3},
            "refined": {"count": 3},
            "chunks": {"required_count": 2, "present_count": 2, "missing_count": 0},
            "validation_summary": {"ERROR": 0, "WARN": 0, "INFO": 0},
        },
    )

    report = readiness_report.collect_report("config.yaml", include_artifacts=True)

    assert report["blocking"] is False
    assert report["schema"]["summary"]["ERROR"] == 0
    assert report["environment"]["summary"]["OK"] == 1
    assert report["stages"][0]["name"] == "extract-audio"
    assert report["artifacts"]["chunks"]["missing_count"] == 0


def test_render_markdown_contains_key_sections() -> None:
    report = {
        "config": {"path": "config.yaml", "loaded": True, "error": None},
        "schema": {"summary": {"ERROR": 0, "WARN": 0, "INFO": 0}, "issues": []},
        "environment": {"summary": {"OK": 1, "WARN": 0, "FAIL": 0}, "results": []},
        "stages": [{"stage_id": 0, "name": "extract-audio", "status": "complete", "detail": "ok"}],
        "artifacts": {
            "asr": {"count": 3},
            "refined": {"count": 3},
            "chunks": {"required_count": 2, "present_count": 2, "missing_count": 0},
            "validation_summary": {"ERROR": 0, "WARN": 0, "INFO": 0},
        },
        "next_actions": [
            {"priority": 10, "title": "Selected range appears ready", "command": "python scripts/run_pipeline.py", "reason": "ok"}
        ],
        "blocking": False,
    }

    rendered = readiness_report.render_markdown(report)

    assert "# Local readiness report" in rendered
    assert "## Schema" in rendered
    assert "## Environment" in rendered
    assert "## Stage status" in rendered
    assert "## Artifacts" in rendered
    assert "## Recommended next actions" in rendered
