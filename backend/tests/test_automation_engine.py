"""Unit tests for the automation engine condition evaluator."""

from unittest.mock import MagicMock

from app.models.asset import AssetStatus
from app.services.automation_engine import _evaluate_conditions


def _make_asset(**kwargs) -> MagicMock:
    """Create a mock asset with given attributes."""
    asset = MagicMock()
    asset.status = kwargs.get("status", AssetStatus.draft)
    asset.file_type = kwargs.get("file_type", "image/jpeg")
    asset.file_size = kwargs.get("file_size", 1024)
    asset.compliance_score = kwargs.get("compliance_score", None)
    asset.caption = kwargs.get("caption", "Test caption")
    return asset


# ---------------------------------------------------------------------------
# Condition evaluation tests
# ---------------------------------------------------------------------------


def test_eq_condition_matches():
    asset = _make_asset(file_type="image/jpeg")
    conditions = [{"field": "file_type", "operator": "eq", "value": "image/jpeg"}]
    assert _evaluate_conditions(conditions, asset) is True


def test_eq_condition_fails():
    asset = _make_asset(file_type="image/png")
    conditions = [{"field": "file_type", "operator": "eq", "value": "image/jpeg"}]
    assert _evaluate_conditions(conditions, asset) is False


def test_gt_condition():
    asset = _make_asset(file_size=5_000_000)
    assert _evaluate_conditions(
        [{"field": "file_size", "operator": "gt", "value": 2_000_000}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "file_size", "operator": "gt", "value": 10_000_000}], asset
    ) is False


def test_lt_condition():
    asset = _make_asset(file_size=1024)
    assert _evaluate_conditions(
        [{"field": "file_size", "operator": "lt", "value": 2048}], asset
    ) is True


def test_gte_lte_conditions():
    asset = _make_asset(compliance_score=70)
    assert _evaluate_conditions(
        [{"field": "compliance_score", "operator": "gte", "value": 70}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "compliance_score", "operator": "lte", "value": 70}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "compliance_score", "operator": "gte", "value": 71}], asset
    ) is False


def test_contains_condition():
    asset = _make_asset(file_type="image/jpeg")
    assert _evaluate_conditions(
        [{"field": "file_type", "operator": "contains", "value": "image"}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "file_type", "operator": "contains", "value": "video"}], asset
    ) is False


def test_starts_with_condition():
    asset = _make_asset(caption="Hello world")
    assert _evaluate_conditions(
        [{"field": "caption", "operator": "starts_with", "value": "Hello"}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "caption", "operator": "starts_with", "value": "Goodbye"}], asset
    ) is False


def test_neq_condition():
    asset = _make_asset(file_type="image/jpeg")
    assert _evaluate_conditions(
        [{"field": "file_type", "operator": "neq", "value": "video/mp4"}], asset
    ) is True
    assert _evaluate_conditions(
        [{"field": "file_type", "operator": "neq", "value": "image/jpeg"}], asset
    ) is False


def test_multiple_conditions_all_must_match():
    asset = _make_asset(file_type="image/jpeg", file_size=5_000_000)
    conditions = [
        {"field": "file_type", "operator": "contains", "value": "image"},
        {"field": "file_size", "operator": "gt", "value": 2_000_000},
    ]
    assert _evaluate_conditions(conditions, asset) is True

    # If one fails, overall fails
    conditions.append({"field": "file_size", "operator": "lt", "value": 1000})
    assert _evaluate_conditions(conditions, asset) is False


def test_missing_field_returns_false():
    asset = _make_asset()
    asset.nonexistent_field = None
    conditions = [{"field": "nonexistent_field", "operator": "eq", "value": "foo"}]
    assert _evaluate_conditions(conditions, asset) is False


def test_empty_conditions_returns_true():
    asset = _make_asset()
    assert _evaluate_conditions([], asset) is True
