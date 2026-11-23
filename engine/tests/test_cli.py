"""CLI behaviour that needs no API and no keys: the budget exit code and failure logging."""

import json

import pytest
from tenacity import wait_none
from typer.testing import CliRunner

from asl_engine import budget, client, cli
from asl_engine.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_results(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(budget, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr(client, "RETRY_WAIT", wait_none())
    return tmp_path


def test_batch_stops_with_exit_code_3_once_the_budget_is_reached(monkeypatch, isolated_results):
    monkeypatch.setenv("ASL_MAX_USD", "0")  # already at the cap, so no run may start
    r = runner.invoke(app, ["batch", "--models", "fake", "--runs", "2", "--seed", "0"])
    assert r.exit_code == 3
    assert "not started" in r.output
    assert json.loads((isolated_results / "spend.json").read_text())["total_usd"] == 0


def test_failed_runs_are_logged_and_skipped(monkeypatch, isolated_results):
    monkeypatch.setenv("ASL_API_URL", "http://127.0.0.1:9")  # nothing listens here
    r = runner.invoke(app, ["batch", "--models", "fake", "--runs", "1", "--seed", "5"])
    assert r.exit_code == 0
    rows = [json.loads(line) for line in (isolated_results / "failures.jsonl").read_text().splitlines()]
    assert len(rows) == 6  # 2 scenarios x 3 conditions x 1 seed
    assert {x["seed"] for x in rows} == {5} and all(x["model"] == "fake" for x in rows)
    assert all("error" in x for x in rows)


def test_unknown_model_is_rejected():
    assert runner.invoke(app, ["batch", "--models", "gpt-5", "--runs", "1"]).exit_code != 0


def test_make_personas_and_graph_write_files(tmp_path):
    p, g = tmp_path / "p.json", tmp_path / "g.mmd"
    assert runner.invoke(app, ["make-personas", "--seed", "42", "--out", str(p)]).exit_code == 0
    assert len(json.loads(p.read_text(encoding="utf-8"))) == 30
    assert runner.invoke(app, ["graph", "--out", str(g)]).exit_code == 0
    text = g.read_text(encoding="utf-8")
    assert "focal_turn" in text and "validate" in text and "tick_start" in text


def test_dotenv_is_loaded_but_the_shell_wins(tmp_path, monkeypatch):
    from asl_engine import config

    env = tmp_path / ".env"
    env.write_text("ASL_TEST_FROM_FILE=file\nASL_TEST_BOTH=file\n", encoding="utf-8")
    for name in ("ASL_TEST_FROM_FILE", "ASL_TEST_BOTH"):
        monkeypatch.setenv(name, "x")  # registers cleanup so the test leaves no variables behind
        monkeypatch.delenv(name)
    monkeypatch.setenv("ASL_TEST_BOTH", "shell")
    assert config.load_env(env) is True
    import os
    assert os.environ["ASL_TEST_FROM_FILE"] == "file" and os.environ["ASL_TEST_BOTH"] == "shell"
    assert config.load_env(tmp_path / "missing.env") is False
