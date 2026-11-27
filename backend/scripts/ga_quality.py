"""GA quality against exact optima (task A.2.6). Not part of the app; run from backend/:

    python scripts/ga_quality.py [--workers 14] [--skip-max] [--out results.json]

Instances (all seeds fixed): cycle time 20, task times uniform 1..20, input order shuffled.
  chain: T0 -> T1 -> ... -> Tn-1.
  wide:  each task after the first gets, with probability 0.5, one predecessor drawn from all earlier tasks
         (a forest: many tasks can go in parallel).
  mixed: each task after the first gets 1 or 2 predecessors drawn from the 5 tasks just before it
         (a typical assembly network: long paths with branching).
Sizes 8, 10, 12: 30 instances per shape and size, solved exactly (branch-and-bound). Size 50: 30 instances
per shape; chains are solved exactly (DP), wide and mixed are compared with N_min only.
Each instance is run with GA seeds 1, 2, 3, at the defaults and at the maximum settings (population 500,
1000 generations, stagnation limit 1000), with the server's 60 s time limit.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ga import engine  # noqa: E402
from app.ga.exact import solve_chain, solve_exact  # noqa: E402
from app.ga.placement import check_solution  # noqa: E402
from app.ga.types import EPS, Instance  # noqa: E402

CYCLE = 20
SHAPES = ("chain", "wide", "mixed")
SMALL_SIZES = (8, 10, 12)
LARGE_SIZE = 50
INSTANCES = 30
GA_SEEDS = (1, 2, 3)
TIME_LIMIT_S = 60.0
MODES = {
    "default": {},
    "max": {"population_size": 500, "max_generations": 1000, "stagnation_limit": 1000},
}


def make_instance(shape: str, n: int, index: int) -> Instance:
    rng = random.Random(f"{shape}-{n}-{index}")  # str seeds are hashed with SHA-512: stable everywhere
    names = [f"T{i}" for i in range(n)]
    preds: dict[str, tuple[str, ...]] = {names[0]: ()}
    for i in range(1, n):
        if shape == "chain":
            preds[names[i]] = (names[i - 1],)
        elif shape == "wide":
            preds[names[i]] = (rng.choice(names[:i]),) if rng.random() < 0.5 else ()
        else:
            window = names[max(0, i - 5) : i]
            preds[names[i]] = tuple(sorted(rng.sample(window, min(len(window), rng.choice([1, 2])))))
    times = {x: float(rng.randint(1, CYCLE)) for x in names}
    order = names[:]
    rng.shuffle(order)
    return Instance(times=times, predecessors=preds, cycle_time=float(CYCLE), order=tuple(order))


def n_min(inst: Instance) -> int:
    return max(1, math.ceil(sum(inst.times.values()) / inst.cycle_time - EPS))


def run_ga(job: tuple[str, int, int, str, int]) -> dict:
    shape, n, index, mode, seed = job
    inst = make_instance(shape, n, index)
    outcome = engine.solve(inst, MODES[mode], seed=seed, time_limit_s=TIME_LIMIT_S)
    stations = [[p.name for p in s] for s in outcome.stations]
    assert check_solution(inst, stations) == []
    return {"shape": shape, "n": n, "index": index, "mode": mode, "seed": seed, "stations": len(stations),
            "runtime": outcome.runtime_seconds, "generations": outcome.generations_run,
            "stop": outcome.stop_reason}


def exact_of(shape: str, n: int, index: int) -> int | None:
    inst = make_instance(shape, n, index)
    if n <= 12:
        result = solve_exact(inst)
        if result.status != "optimal":
            raise RuntimeError(f"exact solver hit its limit on {shape}-{n}-{index}")
        return result.num_stations
    return solve_chain(inst).num_stations if shape == "chain" else None


def table(runs: list[dict], exact: dict, nmin: dict, modes: list[str]) -> str:
    def pct(xs):
        return f"{100 * sum(xs) / len(xs):.0f}%"

    def mean(xs):
        return f"{statistics.mean(xs):.2f}"

    head = ["shape", "size", "exact = N_min"]
    for m in modes:
        head += [f"GA {m} = exact", f"GA {m} gap to exact", f"GA {m} gap to N_min", f"GA {m} runtime (s)"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for n in (*SMALL_SIZES, LARGE_SIZE):
        for shape in SHAPES:
            keys = [(shape, n, i) for i in range(INSTANCES)]
            known = all(exact[k] is not None for k in keys)
            row = [shape, str(n), pct([exact[k] == nmin[k] for k in keys]) if known else "n/a"]
            for m in modes:
                rs = [r for r in runs if (r["shape"], r["n"], r["mode"]) == (shape, n, m)]
                pairs = [(r, (r["shape"], r["n"], r["index"])) for r in rs]
                if known:
                    row += [pct([r["stations"] == exact[k] for r, k in pairs]),
                            mean([r["stations"] - exact[k] for r, k in pairs])]
                else:
                    row += ["n/a", "n/a"]
                row += [mean([r["stations"] - nmin[k] for r, k in pairs]),
                        mean([r["runtime"] for r in rs])]
            lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=14)
    parser.add_argument("--skip-max", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    modes = ["default"] if args.skip_max else list(MODES)

    keys = [(s, n, i) for n in (*SMALL_SIZES, LARGE_SIZE) for s in SHAPES for i in range(INSTANCES)]
    started = time.perf_counter()
    exact = {k: exact_of(*k) for k in keys}
    nmin = {k: n_min(make_instance(*k)) for k in keys}
    print(f"exact optima: {time.perf_counter() - started:.1f} s", flush=True)

    jobs = [(*k, m, seed) for m in reversed(modes) for k in keys for seed in GA_SEEDS]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        runs = list(pool.map(run_ga, jobs))
    print(f"GA runs: {len(runs)} in {time.perf_counter() - started:.0f} s, {args.workers} workers\n")
    print(table(runs, exact, nmin, modes))
    if args.out:
        args.out.write_text(json.dumps({"exact": {"-".join(map(str, k)): v for k, v in exact.items()},
                                        "nmin": {"-".join(map(str, k)): v for k, v in nmin.items()},
                                        "runs": runs}, indent=1))


if __name__ == "__main__":
    main()
