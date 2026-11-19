"""Tests for the decoder (docs/GA_DESIGN.md section 2). Every decoded result must pass check_solution."""

import random

import pytest
from helpers import instance_from_input, load_example

from app.ga.decoder import decode
from app.ga.placement import check_solution
from app.ga.types import Instance


def _six():
    return instance_from_input(load_example("six_task_input.json"))


def _eight():
    # IE formulas document section 8, cycle time 10
    spec = [
        ("A", 7, []), ("B", 4, ["A"]), ("C", 6, ["B"]), ("D", 3, ["C"]),
        ("E", 6, []), ("F", 4, ["E"]), ("G", 5, ["F"]), ("H", 4, ["G"]),
    ]
    return Instance(
        times={n: float(t) for n, t, _ in spec},
        predecessors={n: tuple(p) for n, _, p in spec},
        cycle_time=10.0,
        order=tuple(n for n, _, _ in spec),
    )


def _random_instance(rng: random.Random) -> Instance:
    n = rng.randint(1, 15)
    cycle = float(rng.randint(5, 20))
    names = [f"T{i}" for i in range(n)]
    predecessors = {
        name: tuple(p for p in names[:i] if rng.random() < 0.3) for i, name in enumerate(names)
    }
    times = {name: float(rng.randint(1, int(cycle))) for name in names}
    order = names[:]
    rng.shuffle(order)  # input order differs from the topological order
    return Instance(times=times, predecessors=predecessors, cycle_time=cycle, order=tuple(order))


def test_six_task_trace_from_design_note():
    assert decode(_six(), ["A", "F", "B", "C", "D", "E"]) == [["A", "F"], ["B", "C"], ["D", "E"]]


def test_six_task_identity_order_needs_four_stations():
    stations = decode(_six(), ["A", "B", "C", "D", "E", "F"])
    assert stations == [["A", "B"], ["C", "D"], ["E"], ["F"]]
    assert check_solution(_six(), stations) == []


def test_eight_task_ie_example_reaches_four_stations():
    stations = decode(_eight(), ["A", "D", "C", "B", "E", "F", "H", "G"])
    assert stations == [["A", "D"], ["B", "C"], ["E", "F"], ["G", "H"]]
    assert check_solution(_eight(), stations) == []


def test_every_permutation_of_six_task_example_is_feasible():
    instance = _six()
    rng = random.Random(1)
    for _ in range(300):
        chromosome = list(instance.order)
        rng.shuffle(chromosome)
        assert check_solution(instance, decode(instance, chromosome)) == []


def test_random_small_instances_are_feasible():
    rng = random.Random(2026)
    for _ in range(300):
        instance = _random_instance(rng)
        for _ in range(5):
            chromosome = list(instance.order)
            rng.shuffle(chromosome)
            stations = decode(instance, chromosome)
            assert check_solution(instance, stations) == [], (instance, chromosome)


def test_decoder_is_deterministic():
    instance = _six()
    chromosome = ["C", "A", "E", "F", "B", "D"]
    assert decode(instance, chromosome) == decode(instance, chromosome)


@pytest.mark.parametrize("chromosome", [["A", "B"], ["A", "A", "B", "C", "D", "E"], list("ABCDEZ")])
def test_rejects_chromosome_that_is_not_a_permutation(chromosome):
    with pytest.raises(ValueError):
        decode(_six(), chromosome)
