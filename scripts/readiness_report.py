from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import load_config
from config_checks import FAIL, has_failures as env_has_failures
from config_checks import run_environment_checks, summarize_results
from config_schema import has_errors as schema_has_errors
from config_schema import summarize_issues as summarize_schema_issues
from config_schema import validate_config_schema
from inspect_artifacts import collect_report as collect_artifact_report
from run_pipeline import selected_stages, stage_status


@dataclass(frozen=True)
class StageReadiness:
    stage_id: int
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextAction:
    priority: int
    title: str
    command: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a local readiness report before running the pipeline")
    parser.add_argument("--config", default="configs/local.yaml", help="Path to YAML config file")
    parser.add_argument("--from-stage", type=int, default=0, help="First stage to inspect")
    parser.add_argument("--to-stage", type=int, default=6, help="Last stage to inspect")
    parser.add_argument("--include-artifacts", action="store_true", help="Include artifact inspection summary when artifacts exist")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--output", help="Optional file path to write the report")
    parser.add_argument("--strict", action="store_true", help="Exit with status 1 when blocking issues are present")
    return parser.parse_args()


def collect_stage_readiness(cfg: dict[str, Any], from_stage: int, to_stage: int) -> list[StageReadiness]:
    rows: list[StageReadiness] = []
    for stage_id, name, _cmd in selected_stages(from_stage, to_stage):
        status, detail = stage_status(stage_id, cfg)
        rows.append(StageReadiness(stage_id=stage_id, name=name, status=status, detail=detail))
    return rows


def _artifact_blockers(artifact_report: dict[str, Any] | None) -> bool:
    if not artifact_report:
        return False
    summary = artifact_report.get("validation_summary") or {}
    chunks = artifact_report.get("chunks") or {}
    return bool(summary.get("ERROR", 0) or chunks.get("missing_count", 0))


def _first_incomplete_stage(stages: list[StageReadiness]) -> StageReadiness | None:
    for stage in stages:
        if stage.status in {"missing", "partial", "unknown"}:
            return stage
    return None


def suggest_next_actions(
    config_path: str,
    schema_issues: list[Any],
    env_results: list[Any],
    stages: list[StageReadiness],
    artifact_report: dict[str, Any] | None,
    from_stage: int,
    to_stage: int,
) -> list[NextAction]:
    actions: list[NextAction] = []

    if schema_has_errors(schema_issues):
        actions.append(
            NextAction(
                1,
                "Fix config schema errors",
                f"python scripts/check_config_schema.py --config {config_path}",
                "The YAML config has missing keys, type errors, unsupported enum values, or invalid cross-field settings.",
            )
        )

    if env_has_failures(env_results):
        actions.append(
            NextAction(
                2,
                "Fix environment and local paths",
                f"python scripts/check_env.py --config {config_path}",
                "Local executables, media paths, model paths, adapter modules, or required values are not ready.",
            )
        )

    if artifact_report and _artifact_blockers(artifact_report):
        actions.append(
            NextAction(
                3,
                "Inspect and repair artifacts",
                f"python scripts/inspect_artifacts.py --config {config_path}",
                "ASR/refined JSON or TTS chunk coverage has validation errors or missing chunks.",
            )
        )
        actions.append(
            NextAction(
                4,
                "Run strict artifact validation",
                f"python scripts/validate_artifacts.py --config {config_path}",
                "Use the strict validator as the gate before final assembly.",
            )
        )

    incomplete = _first_incomplete_stage(stages)
    if incomplete:
        actions.append(
            NextAction(
                5,
                "Run or resume the selected pipeline range",
                f"python scripts/run_pipeline.py --config {config_path} --from-stage {from_stage} --to-stage {to_stage} --resume --preflight",
                f"First incomplete selected stage is [{incomplete.stage_id}] {incomplete.name}: {incomplete.status}.",
            )
        )
    elif not actions:
        actions.append(
            NextAction(
                10,
                "Selected range appears ready",
                f"python scripts/run_pipeline.py --config {config_path} --from-stage {from_stage} --to-stage {to_stage} --preflight",
                "Schema, environment checks, and selected stage outputs do not show blocking issues.",
            )
        )

    actions.append(
        NextAction(
            20,
            "Generate a full troubleshooting report",
            f"python scripts/diagnose.py --config {config_path} --include-artifacts",
            "Use this when asking for help or handing the run to another human or agent.",
        )
    )
    return sorted(actions, key=lambda item: item.priority)


def collect_report(config_path: str, from_stage: int = 0, to_stage: int = 6, include_artifacts: bool = False) -> dict[str, Any]:
    try:
        cfg = load_config(config_path)
    except Exception as exc:
        return {
            "config": {"path": config_path, "loaded": False, "error": str(exc)},
            "schema": {"summary": {"ERROR": 1, "WARN": 0, "INFO": 0}, "issues": []},
            "environment": {"summary": {"OK": 0, "WARN": 0, "FAIL": 1}, "results": []},
            "stages": [],
            "artifacts": None,
            "next_actions": [
                NextAction(1, "Fix config load error", f"python scripts/check_config_schema.py --config {config_path}", str(exc)).to_dict()
            ],
            "blocking": True,
        }

    schema_issues = validate_config_schema(cfg)
    env_results = run_environment_checks(cfg)
    stages = collect_stage_readiness(cfg, from_stage, to_stage)
    artifact_report = collect_artifact_report(config_path) if include_artifacts else None
    actions = suggest_next_actions(config_path, schema_issues, env_results, stages, artifact_report, from_stage, to_stage)
    blocking = bool(schema_has_errors(schema_issues) or env_has_failures(env_results) or _artifact_blockers(artifact_report))

    return {
        "config": {"path": config_path, "loaded": True, "error": None},
        "schema": {
            "summary": summarize_schema_issues(schema_issues),
            "issues": [issue.to_dict() for issue in schema_issues],
        },
        "environment": {
            "summary": summarize_results(env_results),
            "results": [result.to_dict() for result in env_results],
        },
        "stages": [stage.to_dict() for stage in stages],
        "artifacts": artifact_report,
        "next_actions": [action.to_dict() for action in actions],
        "blocking": blocking,
    }


def _summary_text(summary: dict[str, int], keys: list[str]) -> str:
    return " ".join(f"{key}={summary.get(key, 0)}" for key in keys)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Local readiness report")
    lines.append("")
    lines.append(f"- Config: `{report['config']['path']}`")
    lines.append(f"- Loaded: `{report['config']['loaded']}`")
    lines.append(f"- Blocking: `{report['blocking']}`")
    if report["config"].get("error"):
        lines.append(f"- Config error: `{report['config']['error']}`")

    lines.append("")
    lines.append("## Schema")
    lines.append(f"- Summary: `{_summary_text(report['schema']['summary'], ['ERROR', 'WARN', 'INFO'])}`")
    for issue in report["schema"].get("issues", [])[:20]:
        lines.append(f"- [{issue['level']}] {issue['path']}: {issue['message']}")

    lines.append("")
    lines.append("## Environment")
    lines.append(f"- Summary: `{_summary_text(report['environment']['summary'], ['OK', 'WARN', 'FAIL'])}`")
    failures = [item for item in report["environment"].get("results", []) if item.get("level") == FAIL]
    for item in failures[:20]:
        lines.append(f"- [FAIL] {item['name']}: {item['message']}")

    lines.append("")
    lines.append("## Stage status")
    for stage in report.get("stages", []):
        lines.append(f"- [{stage['stage_id']}] {stage['name']}: `{stage['status']}` — {stage['detail']}")

    artifacts = report.get("artifacts")
    if artifacts:
        chunks = artifacts.get("chunks") or {}
        validation = artifacts.get("validation_summary") or {}
        lines.append("")
        lines.append("## Artifacts")
        lines.append(f"- ASR segments: `{(artifacts.get('asr') or {}).get('count', 0)}`")
        lines.append(f"- Refined segments: `{(artifacts.get('refined') or {}).get('count', 0)}`")
        lines.append(
            f"- Chunks required / present / missing: `{chunks.get('required_count', 0)} / {chunks.get('present_count', 0)} / {chunks.get('missing_count', 0)}`"
        )
        lines.append(f"- Validation: `{_summary_text(validation, ['ERROR', 'WARN', 'INFO'])}`")

    lines.append("")
    lines.append("## Recommended next actions")
    for action in report.get("next_actions", []):
        lines.append(f"### {action['priority']}. {action['title']}")
        lines.append(f"Reason: {action['reason']}")
        lines.append("")
        lines.append("```bash")
        lines.append(action["command"])
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    report = collect_report(args.config, from_stage=args.from_stage, to_stage=args.to_stage, include_artifacts=args.include_artifacts)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if args.json else render_markdown(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 1 if args.strict and report.get("blocking") else 0


if __name__ == "__main__":
    raise SystemExit(main())
