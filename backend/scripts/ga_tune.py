"""GA tuning on separate instance sets (task A.2.6). Not part of the app; run from backend/:

    python scripts/ga_tune.py --set A --size 50 --count 20 --variants before,a_greedy,b_mutation,c_scale_2x1
    python scripts/ga_tune.py --set B --size 50 --count 20 --variants before,after,greedy_only
    python scripts/ga_tune.py --set B --size 12 --count 30 --variants before,after,greedy_only

Set A was used for tuning; set B only for the final numbers (instances from ga_quality.make_instance).
Reference per instance: the exact optimum for chains (DP) and for up to 12 tasks (branch-and-bound); for 50-task
wide and mixed graphs, the best result max settings found (1 run, seed 1; it stops on the 60 s time limit, so the
reference can differ slightly on a slower or faster machine). Each variant runs with GA seeds 1, 2, 3 at the
default settings. Gap = stations - reference. Runtimes are under parallel load: compare them only with each
other (the idle single-process timing is in docs/GA_DESIGN.md section 9).

Variants: "after" is the real engine (app/ga/engine.py). The others use `_solve` below, a copy of the GA loop
with switches, so changes that were tried and rejected can still be measured:
  before       generation 0 all random (the engine before greedy seeding)
  a_greedy     one greedy chromosome in generation 0 (what the engine does now)
  b_mutation   swap, insertion or inversion mutation, one at random
  c_scale_KPxKS  population = KP x tasks, stagnation limit = KS x tasks (for example c_scale_2x1)
  greedy_only  no GA: the greedy chromosome alone, decoded
A self-check at start-up confirms that `_solve` with greedy seeding gives the same result as the real engine.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ga_quality import MODES, SHAPES, make_instance  # noqa: E402

from app.ga import engine  # noqa: E402
from app.ga.decoder import decode  # noqa: E402
from app.ga.exact import solve_chain, solve_exact  # noqa: E402
from app.ga.operators import order_crossover, swap_mutation, tournament_select  # noqa: E402

GA_SEEDS = (1, 2, 3)


def _mixed_mutation(chromosome, rate, rng):
    result = list(chromosome)
    if len(result) >= 2 and rng.random() < rate:
        op = rng.randrange(3)
        i, j = rng.sample(range(len(result)), 2)
        if op == 0:
            result[i], result[j] = result[j], result[i]
        elif op == 1:
            result.insert(j, result.pop(i))
        else:
            a, b = min(i, j), max(i, j)
            result[a : b + 1] = reversed(result[a : b + 1])
    return result


def _variant(name: str) -> dict:
    if name == "before":
        return {}
    if name == "a_greedy":
        return {"greedy": True}
    if name == "b_mutation":
        return {"mutation": True}
    if name.startswith("c_scale_"):
        kp, ks = name.removeprefix("c_scale_").split("x")
        return {"scale": (float(kp), float(ks))}
    raise ValueError(f"unknown variant {name}")


def _solve(inst, settings: dict, seed: int, variant: dict, time_limit_s: float = 60.0) -> tuple[int, float]:
    """The engine's GA loop with switches. Returns (stations, seconds)."""
    started = time.perf_counter()
    rng = random.Random(seed)
    s = dict(settings)
    n = len(inst.order)
    if "scale" in variant:
        kp, ks = variant["scale"]
        s.setdefault("population_size", max(20, min(500, round(kp * n))))
        s.setdefault("stagnation_limit", max(30, round(ks * n)))
        s.setdefault("max_generations", max(100, 2 * s["stagnation_limit"]))
    cfg = engine._settings(s)
    pop_size, max_gen, elitism = int(cfg["population_size"]), int(cfg["max_generations"]), int(cfg["elitism_count"])
    tasks = list(inst.order)
    cache: OrderedDict = OrderedDict()

    def fitness(chromosome):
        key = tuple(chromosome)
        if key not in cache:
            cache[key] = engine._score(inst, chromosome)
            if len(cache) > engine.FITNESS_CACHE_SIZE:
                cache.popitem(last=False)
        return cache[key]

    population = [rng.sample(tasks, len(tasks)) for _ in range(pop_size)]
    if variant.get("greedy"):
        population[0] = engine.greedy_chromosome(inst)
    mutate = _mixed_mutation if variant.get("mutation") else swap_mutation
    fits = [fitness(c) for c in population]
    best, generation, stall = min(fits), 0, 0
    while time.perf_counter() - started < time_limit_s and stall < cfg["stagnation_limit"] and generation < max_gen:
        ranked = sorted(range(pop_size), key=lambda i: fits[i])
        nxt = [list(population[i]) for i in ranked[:elitism]]
        while len(nxt) < pop_size:
            a = tournament_select(population, fits, cfg["tournament_size"], rng)
            b = tournament_select(population, fits, cfg["tournament_size"], rng)
            child = order_crossover(a, b, rng) if rng.random() < cfg["crossover_rate"] else a
            nxt.append(mutate(child, cfg["mutation_rate"], rng))
        population, fits, generation = nxt, [fitness(c) for c in nxt], generation + 1
        if min(fits) < best:
            best, stall = min(fits), 0
        else:
            stall += 1
    return int(best), time.perf_counter() - started


def _job(job: tuple) -> tuple:
    shape, n, index, seed_set, seed, name = job
    inst = make_instance(shape, n, index, seed_set)
    started = time.perf_counter()
    if name == "max":
        outcome = engine.solve(inst, MODES["max"], seed=seed)
        return job, len(outcome.stations), outcome.runtime_seconds
    if name == "after":
        outcome = engine.solve(inst, {}, seed=seed)
        return job, len(outcome.stations), outcome.runtime_seconds
    if name == "greedy_only":
        return job, len(decode(inst, engine.greedy_chromosome(inst))), time.perf_counter() - started
    stations, seconds = _solve(inst, {}, seed, _variant(name))
    return job, stations, seconds


def _self_check(seed_set: str) -> None:
    for shape in SHAPES:
        inst = make_instance(shape, 30, 0, seed_set)
        real = engine.solve(inst, {}, seed=1)
        assert int(real.best_fitness) == _solve(inst, {}, 1, {"greedy": True})[0], "_solve drifted from engine"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="B", help="instance set: A (tuning) or B (final)")
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--variants", default="before,after,greedy_only")
    parser.add_argument("--workers", type=int, default=14)
    args = parser.parse_args()
    names = args.variants.split(",")
    _self_check(args.set)

    ref: dict[tuple[str, int], int] = {}
    jobs = []
    for shape in SHAPES:
        for i in range(args.count):
            inst = make_instance(shape, args.size, i, args.set)
            if args.size <= 12:
                ref[(shape, i)] = solve_exact(inst).num_stations
            elif shape == "chain":
                ref[(shape, i)] = solve_chain(inst).num_stations
            else:
                jobs.append((shape, args.size, i, args.set, 1, "max"))
            for name in names:
                for seed in GA_SEEDS[:1] if name == "greedy_only" else GA_SEEDS:
                    jobs.append((shape, args.size, i, args.set, seed, name))
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_job, jobs))
    for (shape, _, i, _, _, name), stations, _ in results:
        if name == "max":
            ref[(shape, i)] = stations

    print(f"set {args.set}, {args.size} tasks, {args.count} instances per shape; gap = stations - reference "
          "(exact, or best known from max settings)\n")
    print("| variant | " + " | ".join(f"{s} gap | {s} = ref | {s} time (s)" for s in SHAPES) + " |")
    print("|---|" + "---|---|---|" * len(SHAPES))
    for name in names:
        row = [name]
        for shape in SHAPES:
            rs = [(i, st, sec) for (sh, _, i, _, _, nm), st, sec in results if (sh, nm) == (shape, name)]
            gaps = [st - ref[(shape, i)] for i, st, _ in rs]
            row += [f"{statistics.mean(gaps):.2f}", f"{100 * sum(g <= 0 for g in gaps) / len(gaps):.0f}%",
                    f"{statistics.mean(sec for _, _, sec in rs):.2f}"]
        print("| " + " | ".join(row) + " |")
    print("\nreference per instance:", json.dumps({f"{s}-{i}": v for (s, i), v in sorted(ref.items())}))


if __name__ == "__main__":
    main()
