"""Checks on the container, pipeline and Render files the spec asks for."""

import re
from pathlib import Path

PRODUCT_DIR = Path(__file__).resolve().parents[1]
SECRETS = ("API_KEYS", "CF_ACCOUNT_ID", "CF_API_TOKEN")


def _read(relative):
    return (PRODUCT_DIR / relative).read_text(encoding="utf-8")


def _job(text, name):
    """Return the text of one job of the workflow."""
    match = re.search(
        rf"^  {name}:\n(.*?)(?=^  \w[\w-]*:\n|\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert match, f"job {name} not found"
    return match.group(1)


def test_container_runs_uvicorn_as_non_root_and_ignores_secrets_and_tests():
    dockerfile = _read("Dockerfile")
    assert "FROM python:3.12-slim" in dockerfile
    users = re.findall(r"^USER\s+(\S+)", dockerfile, re.MULTILINE)
    assert users and users[-1] not in ("root", "0")
    assert "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}" in dockerfile
    lines = {
        line.strip().rstrip("/")
        for line in _read(".dockerignore").splitlines()
        if line.strip()
    }
    assert {".env", "tests", "e2e"} <= lines
    assert any("__pycache__" in line for line in lines)


def test_render_blueprint_deploys_only_after_checks_and_keeps_secrets_out():
    text = _read("render.yaml")
    for setting in ("runtime: docker", "plan: free", "healthCheckPath: /health"):
        assert setting in text
    assert "autoDeployTrigger: checksPass" in text
    for name, value in (
        ("ENVIRONMENT", "production"),
        ("MODEL_PROVIDER", "gateway"),
        ("HIDE_INPUTS", "true"),
        ("HIDE_OUTPUTS", "true"),
    ):
        assert re.search(rf'key: {name}\s+value: "?{value}"?', text)
    for name in SECRETS:
        assert re.search(rf"key: {name}\s+sync: false", text), name
    assert "LANGSMITH_API_KEY" not in text


def test_ci_pipeline_chains_four_jobs_on_push_and_pull_request():
    text = _read(".github/workflows/ci.yml")
    assert "push" in text and "pull_request" in text
    expected = {"style": None, "unit": "style", "e2e": "unit", "docker": "e2e"}
    for name, previous in expected.items():
        block = _job(text, name)
        if previous:
            assert re.search(rf"needs:\s*\[?\s*{previous}\b", block), name
    assert "88" in _job(text, "style")
    assert "80" in _job(text, "unit")
    assert "docker build" in _job(text, "docker")
