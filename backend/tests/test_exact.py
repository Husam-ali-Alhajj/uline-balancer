"""Exact solvers (A.2.6): known examples, brute force on small instances, chain DP vs branch-and-bound."""

import itertools
import random

from helpers import instance_from_input, load_example, random_instance

from app.ga.decoder import decode
from app.ga.exact import chain_order, solve_chain, solve_exact
from app.ga.placement import check_solution
from app.ga.types import Instance


def _chain(rng, n, cycle):
    names = [f"T{i}" for i in range(n)]
    order = names[:]
    rng.shuffle(order)
    return Instance(times={x: float(rng.randint(1, cycle)) for x in names},
                    predecessors={x: ((names[i - 1],) if i else ()) for i, x in enumerate(names)},
                    cycle_time=float(cycle), order=tuple(order))


def test_six_task_example_needs_three_stations():
    inst = instance_from_input(load_example("six_task_input.json"))
    result = solve_exact(inst)
    assert (result.status, result.num_stations) == ("optimal", 3)
    assert check_solution(inst, result.stations) == []


def test_eight_task_example_needs_four_stations():
    inst = instance_from_input(load_example("eight_task_input.json"))
    result = solve_exact(inst)
    assert (result.status, result.num_stations) == ("optimal", 4)
    assert check_solution(inst, result.stations) == []


def test_matches_brute_force_over_all_decoded_permutations():
    rng = random.Random(606)
    for _ in range(200):
        inst = random_instance(rng, rng.randint(5, 7), rng.choice([0.1, 0.3, 0.6]), rng.randint(6, 15))
        brute = min(len(decode(inst, p)) for p in itertools.permutations(inst.order))
        result = solve_exact(inst)
        assert result.status == "optimal"
        assert result.num_stations == brute
        assert check_solution(inst, result.stations) == []


def test_limit_returns_unknown_instead_of_hanging():
    inst = random_instance(random.Random(5), 12, 0.05, 20)
    result = solve_exact(inst, node_limit=3)
    assert result.status in ("unknown", "optimal")  # optimal only if the start already meets the bound
    assert result.nodes <= 4
    assert check_solution(inst, result.stations) == []
    rng = random.Random(8)
    unknown = [solve_exact(random_instance(rng, 12, 0.1, 20), node_limit=2).status for _ in range(20)]
    assert "unknown" in unknown


def test_chain_dp_matches_branch_and_bound():
    rng = random.Random(909)
    for _ in range(60):
        inst = _chain(rng, rng.randint(3, 11), rng.randint(5, 20))
        assert chain_order(inst) is not None
        dp, bb = solve_chain(inst), solve_exact(inst)
        assert bb.status == "optimal"
        assert dp.num_stations == bb.num_stations
        assert check_solution(inst, dp.stations) == []


def test_chain_order_rejects_other_graphs():
    inst = instance_from_input(load_example("six_task_input.json"))
    assert chain_order(inst) is None
