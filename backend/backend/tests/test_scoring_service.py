
import pytest

from services.scoring_service import calculate_preparedness_score


def test_complete_score():
    result = calculate_preparedness_score({
        "weather": 45,
        "health": 35,
        "vulnerability": 67,
        "readiness": 90,
    })

    assert result["score"] == 55.9
    assert result["data_status"] == "complete"
    assert result["coverage_percent"] == 100


def test_missing_component():
    result = calculate_preparedness_score({
        "weather": 80,
        "health": 60,
        "vulnerability": None,
        "readiness": 70,
    })

    assert result["score"] == 71.25
    assert result["data_status"] == "partial"
    assert "vulnerability" in result["missing_components"]


def test_all_components_missing():
    result = calculate_preparedness_score({
        "weather": None,
        "health": None,
        "vulnerability": None,
        "readiness": None,
    })

    assert result["score"] is None
    assert result["data_status"] == "unavailable"


@pytest.mark.parametrize("invalid_value", [-1, 101, True])
def test_invalid_component_value(invalid_value):
    with pytest.raises(ValueError):
        calculate_preparedness_score({
            "weather": invalid_value,
            "health": None,
            "vulnerability": None,
            "readiness": None,
        })
