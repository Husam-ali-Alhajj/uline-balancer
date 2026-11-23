"""Decoder property and edge-case tests (Sprint 1 check B3, B4, B5)."""

import random

import pytest
from helpers import instance_from_input, load_example, make_instance, random_instance

from app.ga.decoder import decode
from app.ga.placement import check_solution


def _shuffled(rng, items):
    items = list(items)
    rng.shuffle(items)
    return items


def test_500_random_instances_20_permutations_each_are_feasible():
    rng = random.Random(500)
    for _ in range(500):
        inst = random_instance(rng, rng.randint(2, 12), rng.choice([0.0, 0.2, 0.4, 0.8]), rng.randint(5, 20))
        for _ in range(20):
            stations = decode(inst, _shuffled(rng, inst.order))
            assert check_solution(inst, stations) == [], (inst, stations)
            assert all(stations)
            assert sorted(t for s in stations for t in s) == sorted(inst.order)


def test_one_task():
    assert decode(make_instance([("A", 5, [])], 5), ["A"]) == [["A"]]


def test_no_precedence():
    inst = make_instance([(x, 3, []) for x in "ABCD"], 6)
    stations = decode(inst, list("DCBA"))
    assert check_solution(inst, stations) == []
    assert len(stations) == 2


@pytest.mark.parametrize("order", ["ABCD", "DCBA", "BDAC", "CADB"])
def test_pure_chain(order):
    inst = make_instance([("A", 2, []), ("B", 2, ["A"]), ("C", 2, ["B"]), ("D", 2, ["C"])], 4)
    stations = decode(inst, list(order))
    assert check_solution(inst, stations) == []
    assert len(stations) == 2


def test_task_equal_to_cycle_time_is_alone():
    inst = make_instance([("A", 3, []), ("B", 6, ["A"]), ("C", 3, ["B"])], 6)
    stations = decode(inst, list("BCA"))
    assert check_solution(inst, stations) == []
    assert ["B"] in stations


def test_every_task_equal_to_cycle_time():
    inst = make_instance([(x, 4, []) for x in "ABCDE"], 4)
    stations = decode(inst, list("EDCBA"))
    assert check_solution(inst, stations) == []
    assert len(stations) == 5


@pytest.mark.parametrize("chromosome", [list("AABCDE"), list("ABCDE"), list("ABCDEZ")])
def test_duplicate_missing_or_unknown_name_raises(chromosome):
    inst = instance_from_input(load_example("six_task_input.json"))
    with pytest.raises(ValueError):
        decode(inst, chromosome)


def test_float_times_fit_with_eps():
    # 0.1 + 0.2 == 0.30000000000000004 > 0.3; EPS must let them share one station
    inst = make_instance([("A", 0.1, []), ("B", 0.2, ["A"])], 0.3)
    stations = decode(inst, ["A", "B"])
    assert stations == [["A", "B"]]
    assert check_solution(inst, stations) == []
