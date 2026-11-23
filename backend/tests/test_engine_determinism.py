"""Engine determinism, elitism and quality tests (Sprint 1 check D2, D4, D5, D9, D10)."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest
from helpers import instance_from_input, load_example, random_instance

from app.ga import engine
from app.ga.decoder import decode
from app.ga.fitness import compute_fitness
from app.ga.metrics import compute_metrics
from app.ga.placement import check_solution

BACKEND = Path(__file__).resolve().parents[1]

_CHILD = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
from app.ga import engine
from app.ga.types import Instance
d = json.loads(sys.argv[2])
inst = Instance(times=d["times"], predecessors={k: tuple(v) for k, v in d["preds"].items()},
                cycle_time=d["c"], order=tuple(d["order"]))
o = engine.solve(inst, {}, seed=777)
sys.stdout.write(json.dumps({"st": [[p.name + ":" + p.side for p in s] for s in o.stations],
                             "best": o.best_fitness, "conv": o.convergence}))
"""


def _fitness_of(inst, stations):
    loads = [sum(inst.times[x] for x in s) for s in stations]
    return compute_fitness(len(stations), compute_metrics(inst.cycle_time, loads).smoothness_index,
                           inst.cycle_time)


def test_same_result_across_hash_seeds():
    inst = random_instance(random.Random(21), 30, 0.15, 15)
    payload = json.dumps({"times": inst.times, "preds": inst.predecessors, "c": inst.cycle_time,
                          "order": list(inst.order)})
    outputs = set()
    for hash_seed in ("1", "2", "3"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        proc = subprocess.run([sys.executable, "-c", _CHILD, str(BACKEND), payload],
                              capture_output=True, text=True, env=env, check=True)
        outputs.add(proc.stdout)
    assert len(outputs) == 1
    o = engine.solve(inst, {}, seed=777)
    assert json.loads(outputs.pop()) == json.loads(json.dumps({
        "st": [[p.name + ":" + p.side for p in s] for s in o.stations],
        "best": o.best_fitness, "conv": o.convergence}))


@pytest.mark.parametrize("seed", [42, *range(100, 120)])
def test_six_task_example_three_stations_for_many_seeds(seed):
    inst = instance_from_input(load_example("six_task_input.json"))
    outcome = engine.solve(inst, {}, seed=seed)
    assert len(outcome.stations) == 3


@pytest.mark.parametrize("elitism", [0, 2])
def test_best_fitness_never_increases(elitism):
    rng = random.Random(55)
    for seed in range(15):
        inst = random_instance(rng, rng.randint(5, 40), 0.2, 15)
        outcome = engine.solve(inst, {"elitism_count": elitism}, seed=seed)
        best = [b for _, b, _ in outcome.convergence]
        assert all(later <= earlier for earlier, later in zip(best, best[1:], strict=False))
        assert best[-1] == outcome.best_fitness


def _greedy_topological_fill(inst):
    """The Sprint 0 walking-skeleton solver, kept here only as a comparison baseline."""
    indegree = {x: len(inst.predecessors[x]) for x in inst.order}
    succ = inst.successors()
    ready = [x for x in inst.order if indegree[x] == 0]
    topo = []
    while ready:
        x = ready.pop(0)
        topo.append(x)
        for y in succ[x]:
            indegree[y] -= 1
            if indegree[y] == 0:
                ready.append(y)
    groups, load = [[]], 0.0
    for x in topo:
        if groups[-1] and load + inst.times[x] > inst.cycle_time + 1e-9:
            groups.append([])
            load = 0.0
        groups[-1].append(x)
        load += inst.times[x]
    return groups


def test_ga_is_never_worse_than_greedy_fill():
    rng = random.Random(90)
    for seed in range(15):
        inst = random_instance(rng, rng.randint(5, 50), rng.choice([0.05, 0.15, 0.3]), rng.randint(8, 20))
        greedy = _greedy_topological_fill(inst)
        assert check_solution(inst, greedy) == []
        outcome = engine.solve(inst, {}, seed=seed)
        assert outcome.best_fitness <= _fitness_of(inst, greedy), seed


def test_fitness_cache_is_keyed_by_order_and_matches_fresh_decodes(monkeypatch):
    inst = random_instance(random.Random(21), 30, 0.15, 15)
    scored = {}
    original = engine._score

    def spy(instance, chromosome):
        key = tuple(chromosome)
        assert key not in scored, "a cached chromosome was scored again"
        scored[key] = original(instance, chromosome)
        return scored[key]

    monkeypatch.setattr(engine, "_score", spy)
    engine.solve(inst, {}, seed=3)
    keys = list(scored)
    random.Random(10).shuffle(keys)
    for key in keys[:100]:
        assert scored[key] == _fitness_of(inst, decode(inst, list(key)))

    six = instance_from_input(load_example("six_task_input.json"))
    # same set of tasks, different order: must not share a cache entry
    assert original(six, list("AFBCDE")) != original(six, list("ABCDEF"))
