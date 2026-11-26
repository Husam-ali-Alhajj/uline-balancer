"""Side labelling rule R2 (docs/DECISIONS.md, A.2.3).

R2: front if all predecessors are in earlier stations; else back if all successors are in
earlier stations; then front closure inside the station; the rest is back."""

import random

from helpers import instance_from_input, load_example, random_instance

from app.ga.decoder import decode
from app.ga.placement import check_solution, place_station
from app.ga.types import Instance


def _labels(inst: Instance, stations: list[list[str]]) -> dict[str, str]:
    done: set[str] = set()
    out: dict[str, str] = {}
    for tasks in stations:
        placed = place_station(inst, tasks, done)
        assert placed is not None
        out.update({p.name: p.side for p in placed})
        done.update(tasks)
    return out


def _random_solution(rng: random.Random):
    inst = random_instance(rng, rng.randint(2, 30), rng.choice([0.05, 0.15, 0.3, 0.5]), rng.randint(5, 25))
    chromosome = list(inst.order)
    rng.shuffle(chromosome)
    return inst, decode(inst, chromosome)


def test_labels_do_not_depend_on_input_order():
    rng = random.Random(2023)
    for _ in range(200):
        inst, stations = _random_solution(rng)
        assert check_solution(inst, stations) == []
        base = _labels(inst, stations)
        for _ in range(3):
            order = list(inst.order)
            rng.shuffle(order)
            shuffled = Instance(inst.times, inst.predecessors, inst.cycle_time, tuple(order))
            assert check_solution(shuffled, stations) == []
            assert _labels(shuffled, stations) == base


def test_labels_satisfy_the_unfolded_u_condition():
    """IE formulas document section 6: p_i = s_i on the entry leg, 2M + 1 - s_i on the exit leg,
    and p_h <= p_i for every arc (h, i). Inside one station an entry task cannot follow an exit one."""
    rng = random.Random(77)
    for _ in range(300):
        inst, stations = _random_solution(rng)
        labels = _labels(inst, stations)
        m = len(stations)
        station_of = {t: k for k, tasks in enumerate(stations, start=1) for t in tasks}

        def position(t, labels=labels, m=m, station_of=station_of):
            return station_of[t] if labels[t] == "front" else 2 * m + 1 - station_of[t]

        for i, preds in inst.predecessors.items():
            for h in preds:
                assert position(h) <= position(i), (h, i)
                if position(h) == position(i):
                    assert labels[h] == labels[i], (h, i)


def test_station_order_puts_front_before_back_and_respects_precedence():
    rng = random.Random(5)
    for _ in range(200):
        inst, stations = _random_solution(rng)
        succ = inst.successors()
        done: set[str] = set()
        for tasks in stations:
            placed = place_station(inst, tasks, done)
            sides = [p.side for p in placed]
            assert sides == sorted(sides, key=lambda s: s != "front")
            for p in placed:
                needed = inst.predecessors[p.name] if p.side == "front" else succ[p.name]
                assert all(x in done for x in needed), p
                done.add(p.name)


def test_ie_eight_task_example_labels():
    inst = instance_from_input(load_example("eight_task_input.json"))
    stations = [["A", "D"], ["B", "C"], ["E", "F"], ["G", "H"]]  # IE formulas document, section 8
    # the IE table (entry = front, exit = back), confirmed by the IE team on 2026-11-27
    ie_table = {"A": "front", "D": "back", "B": "front", "C": "back",
                "E": "front", "F": "front", "G": "front", "H": "back"}
    assert _labels(inst, stations) == ie_table


def test_six_task_contract_example_labels():
    inst = instance_from_input(load_example("six_task_input.json"))
    labels = _labels(inst, [["A", "F"], ["B", "E"], ["C", "D"]])
    assert labels == {"A": "front", "F": "back", "B": "front", "E": "back", "C": "front", "D": "back"}
