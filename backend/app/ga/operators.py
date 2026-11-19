"""GA operators (docs/GA_DESIGN.md section 5): tournament selection, order crossover, swap mutation.

All randomness comes from the `rng` passed in (a seeded random.Random), so runs are reproducible.
Inputs are never modified; every function returns a new list. Crossover and mutation always return
a permutation of the same tasks.
"""

from __future__ import annotations

import random
from collections.abc import Sequence


def tournament_select(
    population: Sequence[Sequence[str]], fitnesses: Sequence[float], k: int, rng: random.Random
) -> list[str]:
    """Draw k chromosomes with replacement and return the one with the lowest fitness.

    On a tie the first one drawn wins.
    """
    best = rng.randrange(len(population))
    for _ in range(k - 1):
        index = rng.randrange(len(population))
        if fitnesses[index] < fitnesses[best]:
            best = index
    return list(population[best])


def order_crossover(
    parent_a: Sequence[str], parent_b: Sequence[str], rng: random.Random
) -> list[str]:
    """Classic order crossover (OX).

    The child keeps parent_a[i..j] in place. The other positions, starting after j and wrapping
    around, get the remaining tasks in parent_b's order, also read from after j and wrapping around.
    """
    n = len(parent_a)
    if n < 2:
        return list(parent_a)
    i, j = sorted((rng.randrange(n), rng.randrange(n)))
    child: list[str | None] = [None] * n
    child[i : j + 1] = parent_a[i : j + 1]
    kept = set(parent_a[i : j + 1])
    fill = [parent_b[(j + 1 + k) % n] for k in range(n)]
    fill = [name for name in fill if name not in kept]
    for offset, name in enumerate(fill):
        child[(j + 1 + offset) % n] = name
    return [name for name in child if name is not None]


def swap_mutation(chromosome: Sequence[str], rate: float, rng: random.Random) -> list[str]:
    """With probability `rate`, swap two different random positions (once per chromosome)."""
    result = list(chromosome)
    if len(result) >= 2 and rng.random() < rate:
        i, j = rng.sample(range(len(result)), 2)
        result[i], result[j] = result[j], result[i]
    return result
