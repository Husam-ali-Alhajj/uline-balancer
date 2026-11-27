"""The fitness cache bound changes memory and speed only, never results (A.2.7)."""

import random

from helpers import random_instance

from app.ga import engine

SETTINGS = {"population_size": 40, "max_generations": 60, "stagnation_limit": 1000}  # 2,440 chromosomes
SIZES = [0, 1_000, engine.FITNESS_CACHE_SIZE, None]  # off, small (evicts), default, unbounded


def _run(inst, seed, size, monkeypatch, calls):
    original = engine._score

    def counting(instance, chromosome):
        calls[size] = calls.get(size, 0) + 1
        return original(instance, chromosome)

    monkeypatch.setattr(engine, "_score", counting)
    outcome = engine.solve(inst, SETTINGS, seed=seed, time_limit_s=1e9, cache_size=size)
    monkeypatch.setattr(engine, "_score", original)
    return (
        [[(p.name, p.side) for p in s] for s in outcome.stations],
        outcome.best_fitness,
        outcome.convergence,
        outcome.generations_run,
    )


def test_cache_size_does_not_change_results(monkeypatch):
    rng = random.Random(707)
    evicted = 0
    for seed in range(20):
        inst = random_instance(rng, rng.randint(8, 20), rng.choice([0.05, 0.15, 0.3]), rng.randint(8, 20))
        calls: dict = {}
        results = [_run(inst, seed, size, monkeypatch, calls) for size in SIZES]
        assert all(r == results[0] for r in results[1:]), seed
        # the cache works: turning it off scores more chromosomes than keeping everything
        assert calls[0] > calls[None]
        evicted += calls[1_000] > calls[None]
    assert evicted > 0  # the 1,000-entry cache really dropped entries in some runs


def test_cache_never_holds_more_than_its_size(monkeypatch):
    sizes_seen = []
    original_od = engine.OrderedDict

    class Watched(original_od):
        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            sizes_seen.append(len(self))

    monkeypatch.setattr(engine, "OrderedDict", Watched)
    inst = random_instance(random.Random(3), 30, 0.15, 15)
    engine.solve(inst, SETTINGS, seed=1, time_limit_s=1e9, cache_size=100)
    # it fills up to the bound, goes one over on an insert, and the oldest entry is dropped at once
    assert max(sizes_seen) == 101
    assert sizes_seen.count(101) > 1
