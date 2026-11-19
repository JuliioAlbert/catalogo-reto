"""Unit tests for load_env_file and the startup rule CATALOG_SKIP_DOTENV.

The real .env is never read: files live in tmp_path and the dotenv loader is
replaced by a spy when the module is imported again.
"""

import importlib
import os
from pathlib import Path

import pytest

import app.main as main_module
from app.main import load_env_file


def test_missing_env_file_returns_false(tmp_path):
    assert load_env_file(tmp_path / "absent.env") is False


def test_present_env_file_loads_its_variables(tmp_path, monkeypatch):
    monkeypatch.delenv("HR_TEST_FROM_FILE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("HR_TEST_FROM_FILE=loaded\n", encoding="utf-8")
    try:
        assert load_env_file(env_file) is True
        assert os.environ["HR_TEST_FROM_FILE"] == "loaded"
    finally:
        os.environ.pop("HR_TEST_FROM_FILE", None)


def test_an_exported_variable_is_not_overridden(tmp_path, monkeypatch):
    monkeypatch.setenv("HR_TEST_EXPORTED", "from-shell")
    env_file = tmp_path / ".env"
    env_file.write_text("HR_TEST_EXPORTED=from-file\n", encoding="utf-8")
    load_env_file(env_file)
    assert os.environ["HR_TEST_EXPORTED"] == "from-shell"


@pytest.fixture
def startup(monkeypatch):
    """Import app.main again and report whether the .env loader was called."""
    calls = []

    def spy(*args, **_kwargs):
        calls.append(args)
        return False

    real_is_file = Path.is_file
    monkeypatch.setattr(
        Path, "is_file", lambda self: self.name == ".env" or real_is_file(self)
    )
    monkeypatch.setattr("dotenv.load_dotenv", spy)

    def run(skip):
        if skip:
            monkeypatch.setenv("CATALOG_SKIP_DOTENV", "1")
        else:
            monkeypatch.delenv("CATALOG_SKIP_DOTENV", raising=False)
        importlib.reload(main_module)
        return calls

    yield run
    # Restore the module without touching the real .env.
    monkeypatch.undo()
    os.environ["CATALOG_SKIP_DOTENV"] = "1"
    try:
        importlib.reload(main_module)
    finally:
        os.environ.pop("CATALOG_SKIP_DOTENV", None)


def test_startup_skips_the_env_file_when_hr_skip_dotenv_is_set(startup):
    assert startup(skip=True) == []


def test_startup_loads_the_env_file_when_hr_skip_dotenv_is_not_set(startup):
    assert len(startup(skip=False)) == 1
