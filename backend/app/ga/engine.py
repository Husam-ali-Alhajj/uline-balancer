"""GA entry point: the genetic algorithm loop (docs/GA_DESIGN.md sections 6 and 7).

Chromosome: a permutation of task names. Every chromosome is decoded into a feasible solution
(decoder.py), scored with compute_fitness (lower is better), and evolved with tournament selection,
order crossover, swap mutation and elitism. All randomness goes through one random.Random(seed),
so the same input and seed give the same result.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Sequence

from .decoder import decode
from .fitness import compute_fitness
from .metrics import compute_metrics
from .operators import order_crossover, swap_mutation, tournament_select
from .placement import place_station
from .types import Instance, Placement, SolveOutcome

ProgressCallback = Callable[[int, int], None]

DEFAULTS = {
    "population_size": 50,
    "max_generations": 100,
    "crossover_rate": 0.8,
    "mutation_rate": 0.1,
    "elitism_count": 2,
    "tournament_size": 3,
    "stagnation_limit": 30,
}


def _settings(settings: dict) -> dict:
    merged = {key: settings.get(key) if settings.get(key) is not None else value
              for key, value in DEFAULTS.items()}
    # GA_DESIGN.md section 8: keep at least one non-elite slot so the population can change
    merged["elitism_count"] = max(0, min(int(merged["elitism_count"]),
                                         int(merged["population_size"]) - 1))
    return merged


def _score(instance: Instance, chromosome: Sequence[str]) -> float:
    stations = decode(instance, chromosome)
    loads = [sum(instance.times[name] for name in station) for station in stations]
    metrics = compute_metrics(instance.cycle_time, loads)
    return compute_fitness(len(stations), metrics.smoothness_index, instance.cycle_time)


def _place(instance: Instance, stations: list[list[str]]) -> list[list[Placement]]:
    placed_stations: list[list[Placement]] = []
    assigned: set[str] = set()
    for group in stations:
        placed = place_station(instance, group, assigned)
        if placed is None:
            raise AssertionError("decoded station violates the U-line rule")
        placed_stations.append(placed)
        assigned.update(group)
    return placed_stations


def solve(
    instance: Instance,
    settings: dict,
    seed: int | None = None,
    progress: ProgressCallback | None = None,
    time_limit_s: float = 60.0,
) -> SolveOutcome:
    started = time.perf_counter()
    used_seed = seed if seed is not None else random.randrange(2**31)
    rng = random.Random(used_seed)
    cfg = _settings(settings)
    pop_size = int(cfg["population_size"])
    max_generations = int(cfg["max_generations"])
    elitism = int(cfg["elitism_count"])
    tasks = list(instance.order)

    # Decoding is deterministic, so a chromosome's fitness can be cached.
    cache: dict[tuple[str, ...], float] = {}

    def fitness_of(chromosome: list[str]) -> float:
        key = tuple(chromosome)
        if key not in cache:
            cache[key] = _score(instance, chromosome)
        return cache[key]

    population = [rng.sample(tasks, len(tasks)) for _ in range(pop_size)]
    fitnesses = [fitness_of(c) for c in population]

    best_index = min(range(pop_size), key=lambda i: fitnesses[i])
    best_chromosome = list(population[best_index])
    best_fitness = fitnesses[best_index]
    convergence = [(0, best_fitness, round(sum(fitnesses) / pop_size, 4))]
    if progress:
        progress(0, max_generations)

    generation = 0
    stall = 0
    stop_reason = "max_generations"
    while True:
        if time.perf_counter() - started >= time_limit_s:
            stop_reason = "time_limit"
            break
        if stall >= cfg["stagnation_limit"]:
            stop_reason = "stagnation"
            break
        if generation >= max_generations:
            stop_reason = "max_generations"
            break

        ranked = sorted(range(pop_size), key=lambda i: fitnesses[i])  # stable: ties keep order
        next_population = [list(population[i]) for i in ranked[:elitism]]
        while len(next_population) < pop_size:
            parent_a = tournament_select(population, fitnesses, cfg["tournament_size"], rng)
            parent_b = tournament_select(population, fitnesses, cfg["tournament_size"], rng)
            if rng.random() < cfg["crossover_rate"]:
                child = order_crossover(parent_a, parent_b, rng)
            else:
                child = parent_a
            next_population.append(swap_mutation(child, cfg["mutation_rate"], rng))

        population = next_population
        fitnesses = [fitness_of(c) for c in population]
        generation += 1

        gen_best = min(range(pop_size), key=lambda i: fitnesses[i])
        if fitnesses[gen_best] < best_fitness:
            best_fitness = fitnesses[gen_best]
            best_chromosome = list(population[gen_best])
            stall = 0
        else:
            stall += 1
        convergence.append((generation, best_fitness, round(sum(fitnesses) / pop_size, 4)))
        if progress:
            progress(generation, max_generations)

    return SolveOutcome(
        stations=_place(instance, decode(instance, best_chromosome)),
        generations_run=generation,
        stop_reason=stop_reason,
        best_fitness=best_fitness,
        seed=used_seed,
        runtime_seconds=round(time.perf_counter() - started, 4),
        convergence=convergence,
    )
