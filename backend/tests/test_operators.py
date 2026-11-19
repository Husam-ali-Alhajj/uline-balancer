"""Tests for the GA operators (docs/GA_DESIGN.md section 5). Every child must be a permutation of all tasks."""

import random

from app.ga.operators import order_crossover, swap_mutation, tournament_select


class FixedRandom(random.Random):
    """A Random whose randrange returns preset values, to force cut points and tournament draws."""

    def __init__(self, values):
        super().__init__(0)
        self._values = list(values)

    def randrange(self, *args, **kwargs):
        return self._values.pop(0)


def _tasks(n):
    return [f"T{i}" for i in range(n)]


def test_order_crossover_matches_design_note_example():
    child = order_crossover(list("ABCDEF"), list("FEDCBA"), FixedRandom([3, 2]))
    assert child == list("FECDBA")


def test_order_crossover_full_segment_copies_parent_a():
    assert order_crossover(list("ABCD"), list("DCBA"), FixedRandom([0, 3])) == list("ABCD")


def test_order_crossover_children_are_permutations():
    rng = random.Random(7)
    for _ in range(1000):
        tasks = _tasks(rng.randint(1, 50))
        a, b = tasks[:], tasks[:]
        rng.shuffle(a)
        rng.shuffle(b)
        child = order_crossover(a, b, rng)
        assert len(child) == len(tasks)
        assert sorted(child) == sorted(tasks)


def test_swap_mutation_children_are_permutations():
    rng = random.Random(8)
    for _ in range(1000):
        tasks = _tasks(rng.randint(1, 50))
        rng.shuffle(tasks)
        child = swap_mutation(tasks, rng.random(), rng)
        assert sorted(child) == sorted(tasks)


def test_swap_mutation_rate_one_swaps_exactly_two_positions():
    rng = random.Random(9)
    tasks = _tasks(10)
    for _ in range(100):
        child = swap_mutation(tasks, 1.0, rng)
        assert sum(1 for x, y in zip(tasks, child, strict=True) if x != y) == 2


def test_swap_mutation_rate_zero_changes_nothing():
    tasks = _tasks(10)
    assert swap_mutation(tasks, 0.0, random.Random(1)) == tasks


def test_operators_do_not_modify_inputs():
    a, b = list("ABCDEF"), list("FEDCBA")
    rng = random.Random(3)
    order_crossover(a, b, rng)
    swap_mutation(a, 1.0, rng)
    tournament_select([a, b], [1.0, 2.0], 3, rng)
    assert a == list("ABCDEF") and b == list("FEDCBA")


def test_tournament_returns_lowest_fitness_among_drawn():
    population = [["A"], ["B"], ["C"], ["D"]]
    fitnesses = [3.0, 1.0, 2.0, 4.0]
    assert tournament_select(population, fitnesses, 3, FixedRandom([0, 2, 3])) == ["C"]
    assert tournament_select(population, fitnesses, 2, FixedRandom([3, 1])) == ["B"]


def test_tournament_tie_goes_to_first_drawn():
    population = [["A"], ["B"], ["C"]]
    assert tournament_select(population, [2.0, 1.0, 1.0], 2, FixedRandom([2, 1])) == ["C"]


def test_tournament_returns_a_copy():
    population = [["A", "B"]]
    chosen = tournament_select(population, [1.0], 2, random.Random(0))
    chosen.append("X")
    assert population == [["A", "B"]]


def test_same_seed_gives_same_children():
    a, b = _tasks(20), list(reversed(_tasks(20)))

    def run(seed):
        rng = random.Random(seed)
        return [swap_mutation(order_crossover(a, b, rng), 0.5, rng) for _ in range(20)]

    assert run(42) == run(42)
