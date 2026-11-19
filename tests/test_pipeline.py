"""Unit tests for scripts/pipeline.py, the factory observability script."""

import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Imported by name: ``scripts`` lives above the product folder, so pylint
# cannot resolve a regular import statement.
try:
    pipeline = importlib.import_module("scripts.pipeline")
except ImportError:
    # Published product/ repository: the factory script is not there.
    pytest.skip(
        "scripts.pipeline belongs to the factory, not to the product",
        allow_module_level=True,
    )

START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def event(seconds, agent, tool, target="", ok=True):
    """Build one JSON line of the activity log, ``seconds`` after START."""
    moment = (START + timedelta(seconds=seconds)).isoformat()
    return json.dumps(
        {"ts": moment, "agent": agent, "tool": tool, "target": target, "ok": ok}
    )


def step(seconds, is_agent=True, ok=True):
    """Build a found step launched ``seconds`` after START."""
    return {
        "name": "x",
        "ok": ok,
        "launch": START + timedelta(seconds=seconds),
        "is_agent": is_agent,
        "seconds": 1,
    }


def test_agent_duration_runs_until_its_last_tool():
    lines = [
        event(0, "orchestrator", "Agent", "architect"),
        event(30, "architect", "Write"),
        event(40, "orchestrator", "Agent", "developer"),
    ]
    found = pipeline.steps(lines)
    assert [s["name"] for s in found] == ["architect", "developer"]
    assert found[0]["seconds"] == 30
    assert found[0]["is_agent"] is True


def test_failed_verification_is_reported_with_its_name():
    lines = [
        event(0, "orchestrator", "Agent", "qa-unit"),
        event(30, "qa-unit", "Write"),
        event(45, "orchestrator", "Bash", "uv run python -m verification unit", False),
    ]
    verify = pipeline.steps(lines)[-1]
    assert verify["name"] == "verify unit"
    assert verify["ok"] is False
    assert verify["seconds"] == 15
    assert verify["is_agent"] is False


def test_other_orchestrator_tools_are_not_steps():
    lines = [
        event(0, "orchestrator", "Read", "plan.md"),
        event(5, "orchestrator", "Bash", "ls"),
    ]
    assert not pipeline.steps(lines)


def test_empty_log_has_no_steps_and_renders_a_header():
    assert not pipeline.steps(["", "  "])
    assert "# Pipeline de la fábrica" in pipeline.render([])


def test_log_line_without_required_fields_raises_key_error():
    broken = json.dumps({"ts": START.isoformat(), "tool": "Agent"})
    with pytest.raises(KeyError):
        pipeline.steps([broken])


def test_agents_launched_together_share_a_column():
    assert pipeline.columns([step(0), step(2)]) == [[0, 1]]


@pytest.mark.parametrize(
    ("gap", "expected"),
    [(pipeline.PARALLEL_GAP, [[0, 1]]), (pipeline.PARALLEL_GAP + 1, [[0], [1]])],
)
def test_parallel_gap_boundary(gap, expected):
    assert pipeline.columns([step(0), step(gap)]) == expected


def test_verification_never_joins_an_agent_column():
    assert pipeline.columns([step(0), step(1, is_agent=False)]) == [[0], [1]]


def test_render_draws_nodes_arrows_and_a_table_row_per_step():
    text = pipeline.render([step(0), step(60, ok=False)])
    assert "flowchart LR" in text
    assert "s0 --> s1" in text
    assert ":::fail" in text
    assert "| 2 | x | falló | 1 |" in text


def test_main_without_a_log_fails_with_exit_code_one(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "LOG", tmp_path / "missing.jsonl")
    assert pipeline.main() == 1


def test_main_writes_the_pipeline_file(monkeypatch, tmp_path):
    log = tmp_path / "activity.jsonl"
    log.write_text(event(0, "orchestrator", "Agent", "architect") + "\n")
    out = tmp_path / "pipeline.md"
    monkeypatch.setattr(pipeline, "LOG", log)
    monkeypatch.setattr(pipeline, "PIPELINE", out)
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    assert pipeline.main() == 0
    assert "architect" in out.read_text(encoding="utf-8")
