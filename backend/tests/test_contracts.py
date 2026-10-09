"""The example JSON files, the JSON Schemas, the Pydantic models and the GA code must agree."""

import json

from jsonschema import Draft202012Validator

from app.ga.metrics import compute_metrics
from app.ga.placement import check_solution
from app.ml.interface import RecommendationInput
from app.ml.rule_based import RuleBasedRecommender
from app.schemas.problem import ProblemInput
from app.schemas.result import RunResult
from app.schemas.run import RunStatus
from app.services.instance import summarize

from helpers import CONTRACTS, instance_from_input, load_example


def _schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text())


def test_schemas_are_valid_json_schema():
    for name in ("problem_input", "run_result", "run_status"):
        Draft202012Validator.check_schema(_schema(f"{name}.schema.json"))


def test_examples_match_json_schemas():
    pairs = [
        ("six_task_input.json", "problem_input.schema.json"),
        ("six_task_result.json", "run_result.schema.json"),
        ("six_task_run_status_succeeded.json", "run_status.schema.json"),
    ]
    for example, schema in pairs:
        Draft202012Validator(_schema(schema)).validate(load_example(example))


def test_examples_parse_with_pydantic():
    ProblemInput.model_validate(load_example("six_task_input.json"))
    RunResult.model_validate(load_example("six_task_result.json"))
    RunStatus.model_validate(load_example("six_task_run_status_succeeded.json"))


def test_example_summary_matches_result_instance():
    problem = ProblemInput.model_validate(load_example("six_task_input.json"))
    result = load_example("six_task_result.json")
    assert summarize(problem).model_dump() == result["instance"]


def test_example_solution_is_feasible_and_metrics_are_consistent():
    data = load_example("six_task_input.json")
    result = load_example("six_task_result.json")
    instance = instance_from_input(data)
    names = [[t["name"] for t in s["tasks"]] for s in result["solution"]["stations"]]
    assert check_solution(instance, names) == []

    loads = [s["load"] for s in result["solution"]["stations"]]
    m = compute_metrics(instance.cycle_time, loads)
    assert m.efficiency == result["metrics"]["efficiency"]
    assert m.smoothness_index == result["metrics"]["smoothness_index"]
    assert m.bottleneck_stations == result["metrics"]["bottleneck_stations"]


def test_example_recommendations_match_rule_based_output():
    data = load_example("six_task_input.json")
    result = load_example("six_task_result.json")
    instance = instance_from_input(data)
    loads = [s["load"] for s in result["solution"]["stations"]]
    m = compute_metrics(instance.cycle_time, loads)
    rec_input = RecommendationInput(
        instance.cycle_time, result["instance"]["min_stations"], len(loads),
        m.efficiency, loads, dict(instance.times), m.high_idle_stations,
    )
    codes = [r.code for r in RuleBasedRecommender().recommend(rec_input)]
    assert codes == [r["code"] for r in result["recommendations"]]
