import pytest

from asl_engine.budget import Budget


def test_cost_uses_the_registry_prices():
    assert Budget.cost("claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(0.10 + 0.50)
    assert Budget.cost("gpt-oss-120b", 1_000_000, 0) == pytest.approx(0.35)
    assert Budget.cost("fake", 10**9, 10**9) == 0


def test_exceeded_once_the_cap_is_reached(tmp_path):
    b = Budget(0.01, tmp_path / "spend.json")
    assert not b.exceeded
    b.add("llama-3.1-8b", 10_000, 10_000)  # about $0.0044
    assert not b.exceeded
    b.add("llama-3.1-8b", 20_000, 10_000)
    assert b.exceeded


def test_total_persists_across_batches(tmp_path):
    path = tmp_path / "results" / "spend.json"
    a = Budget(8, path)
    a.add("claude-haiku-5-5", 2_000_000, 1_000_000)
    a.save()
    b = Budget(8, path)
    assert b.total == pytest.approx(a.total)
    assert b.by_model["claude-haiku-5-5"] == pytest.approx(0.70)
    b.add("claude-haiku-5-5", 1_000_000, 0)
    assert b.total == pytest.approx(0.80)


def test_a_lower_cap_applies_to_an_existing_total(tmp_path):
    path = tmp_path / "spend.json"
    a = Budget(8, path)
    a.add("gpt-oss-120b", 10_000_000, 0)  # $3.50
    a.save()
    assert not Budget(8, path).exceeded
    assert Budget(3, path).exceeded
