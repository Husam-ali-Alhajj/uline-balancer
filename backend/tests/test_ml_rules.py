from app.ga.metrics import compute_metrics
from app.ml.interface import RecommendationInput
from app.ml.rule_based import RuleBasedRecommender


def _codes(cycle, loads, min_stations, times):
    m = compute_metrics(cycle, loads)
    data = RecommendationInput(cycle, min_stations, len(loads), m.efficiency, loads, times, m.high_idle_stations)
    return [r.code for r in RuleBasedRecommender().recommend(data)]


def test_well_balanced_solution_at_minimum():
    codes = _codes(8.0, [8, 8, 7], 3, {"A": 4.0})
    assert codes == ["MIN_STATIONS_REACHED", "WELL_BALANCED"]


def test_above_minimum_and_high_idle():
    codes = _codes(10.0, [10, 10, 3], 2, {"A": 4.0})
    assert "ABOVE_MIN_STATIONS" in codes
    assert "HIGH_IDLE_STATION" in codes


def test_long_task_is_reported():
    assert "LONG_TASK" in _codes(10.0, [9, 8], 2, {"X": 9.0})


def test_every_recommendation_names_its_trigger():
    m = compute_metrics(10.0, [10, 3])
    data = RecommendationInput(10.0, 2, 2, m.efficiency, [10, 3], {"X": 9.0}, m.high_idle_stations)
    assert all(r.triggered_by for r in RuleBasedRecommender().recommend(data))
