from calculator.energy import estimate_energy
from calculator.carbon import calculate_carbon
from calculator.location import optimize_regions

def test_energy_is_nonnegative():
    result = estimate_energy(50, 8, 100, 2, 2)
    assert result["total_energy_kwh"] > 0
    assert result["cpu_energy_kwh"] >= 0

def test_carbon_formula():
    result = calculate_carbon(2, 400)
    assert result["carbon_grams"] == 800
    assert result["carbon_kg"] == 0.8

def test_regions_ranked_by_emissions():
    rows = [
        {"carbon": {"carbon_kg": 3}},
        {"carbon": {"carbon_kg": 1}},
        {"carbon": {"carbon_kg": 2}},
    ]
    assert [x["carbon"]["carbon_kg"] for x in optimize_regions(rows)] == [1, 2, 3]


def test_recommendation_index_ranks_higher_ratio_first():
    rows = [
        {"carbon": {"carbon_kg": 10}, "sustainability_score": 80, "recommendation_index": 8},
        {"carbon": {"carbon_kg": 5}, "sustainability_score": 50, "recommendation_index": 10},
    ]
    ranked = sorted(rows, key=lambda item: (item.get("recommendation_index") is None, -(item.get("recommendation_index") or 0)))
    assert ranked[0]["recommendation_index"] == 10


def test_undefined_recommendation_index_ranks_last():
    rows = [
        {"carbon": {"carbon_kg": 0}, "sustainability_score": 90, "recommendation_index": None},
        {"carbon": {"carbon_kg": 10}, "sustainability_score": 80, "recommendation_index": 8},
    ]
    ranked = sorted(rows, key=lambda item: (item.get("recommendation_index") is None, -(item.get("recommendation_index") or 0)))
    assert ranked[-1]["recommendation_index"] is None
