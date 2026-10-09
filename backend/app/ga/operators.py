"""TODO (GA design session): selection, order crossover, mutation, elitism.

Crossover and mutation must keep the chromosome a valid permutation of all tasks.
"""


def tournament_select(population, fitnesses, k, rng):  # noqa: ANN001
    raise NotImplementedError


def order_crossover(parent_a, parent_b, rng):  # noqa: ANN001
    raise NotImplementedError


def swap_mutation(chromosome, rate, rng):  # noqa: ANN001
    raise NotImplementedError
