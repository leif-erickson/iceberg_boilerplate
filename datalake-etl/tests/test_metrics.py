from __future__ import annotations

from scripts.metrics import REGISTRY, StageResult, observe_stage, record_stage_result


def test_observe_stage_records_success() -> None:
    before = REGISTRY.get_sample_value(
        "etl_stage_last_success_total",
        {"stage": "unit", "layer": "test"},
    )
    assert before is None or before >= 0

    with observe_stage("unit", "test") as result:
        result.row_counts["sample"] = 3

    success = REGISTRY.get_sample_value("etl_stage_last_success", {"stage": "unit", "layer": "test"})
    rows = REGISTRY.get_sample_value(
        "etl_stage_rows", {"stage": "unit", "layer": "test", "entity": "sample"}
    )
    assert success == 1.0
    assert rows == 3.0


def test_record_stage_result_failure() -> None:
    result = StageResult(stage="fail", layer="test", duration_seconds=0.1, success=False)
    record_stage_result(result)
    success = REGISTRY.get_sample_value("etl_stage_last_success", {"stage": "fail", "layer": "test"})
    assert success == 0.0
