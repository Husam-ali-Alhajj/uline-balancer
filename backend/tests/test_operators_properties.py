"""Operator property and edge-case tests (Sprint 1 check C1, C2, C3)."""

import random

import pytest

from app.ga.operators import order_crossover, swap_mutation, tournament_select


@pytest.mark.parametrize("size", [1, 2, 3, 6, 50])
def test_order_crossover_10000_pairs(size):
    rng = random.Random(size)
    tasks = [f"T{i}" for i in range(size)]
    for _ in range(10000):
        a, b = tasks[:], tasks[:]
        rng.shuffle(a)
        rng.shuffle(b)
        a0, b0 = list(a), list(b)
        child = order_crossover(a, b, rng)
        assert sorted(child) == sorted(tasks)
        assert a == a0 and b == b0


def test_swap_mutation_rate_zero_returns_equal_copy():
    tasks = [f"T{i}" for i in range(10)]
    child = swap_mutation(tasks, 0.0, random.Random(1))
    assert child == tasks and child is not tasks


def test_swap_mutation_rate_one_is_valid_and_leaves_input():
    tasks = [f"T{i}" for i in range(10)]
    before = list(tasks)
    child = swap_mutation(tasks, 1.0, random.Random(2))
    assert sorted(child) == sorted(tasks) and child != tasks
    assert tasks == before


def test_swap_mutation_size_one():
    assert swap_mutation(["A"], 1.0, random.Random(3)) == ["A"]


POP = [["A", "B"], ["B", "A"], ["A", "B"]]
FIT = [3.0, 1.0, 2.0]


@pytest.mark.parametrize("k", [2, 3, 10])
def test_tournament_k_smaller_equal_and_larger_than_population(k):
    assert tournament_select(POP, FIT, k, random.Random(k)) in POP


def test_tournament_all_fitnesses_equal():
    assert tournament_select(POP, [1.0, 1.0, 1.0], 3, random.Random(4)) in POP


def test_tournament_lowest_fitness_wins_with_large_k():
    for seed in range(200):
        assert tournament_select(POP, FIT, 50, random.Random(seed)) == ["B", "A"]


def test_tournament_returns_a_copy():
    chosen = tournament_select(POP, FIT, 2, random.Random(5))
    assert all(chosen is not p for p in POP)
