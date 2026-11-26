# GA design note

Design of the genetic algorithm in `backend/app/ga/` (Sprint 1, task A.1.2). Code in `decoder.py`,
`operators.py` and `engine.py` must follow this note. Formulas come from MASTER.md section 5; this note
adds no new formula.

Source: *U-Shaped Assembly Line Balancing: Formulas and Worked Example* (IE team), called "IE doc" below.
Section 5 (The U-Line Assignment Rule) defines the rule the decoder uses, section 9 the station-filling
procedure, section 10 the GA objectives and section 11 the fitness chosen for this project.

## 1. Chromosome

A chromosome is a **permutation of all task names**, for example `[A, F, B, C, D, E]`. Each task appears
exactly once. The order is a priority list: a task earlier in the list is tried earlier by the decoder.

Why a permutation: every permutation decodes to a feasible solution (section 2), so the GA never needs
a repair step or a penalty for infeasible solutions, and order crossover and swap mutation keep the
chromosome a permutation.

## 2. Decoder rule

`decode(instance, chromosome) -> list[list[str]]` builds stations one by one.

**Eligible task** (IE doc section 5): an unassigned task is eligible when all its predecessors are already
assigned, or all its successors are already assigned. "Assigned" includes the tasks already put in the
current station.

**Filling a station** (IE doc sections 5 and 9, "a station is filled until no assignable task fits"):

1. Open a new station with remaining time C.
2. Scan the chromosome from the start. Take the **first** unassigned task that is eligible **and** fits
   (time <= remaining time). Add it to the station and subtract its time.
3. Repeat step 2 until no eligible task fits. Close the station.
4. If tasks remain, go to step 1.

The decoder then passes each station's task set to `place_station` (`placement.py`), which orders the
tasks and labels each one `front` or `back`. The U-line rule stays only in `placement.py`; the decoder
only uses it.

**Side labels (rule R2, docs/DECISIONS.md; confirmed by the IE team on 2026-11-27, IE doc section 5).**
Inside a station, a task is labelled:
1. `front` if all its predecessors are in earlier stations;
2. else `back` if all its successors are in earlier stations;
3. then, repeatedly, `front` if all its predecessors are in earlier stations or are `front` tasks of this
   station (front closure);
4. every remaining task is `back`.

Steps 1 and 2 follow the reasons the IE document gives in section 8 ("entry side, since A is assigned",
"exit side, since D is assigned"). The labels depend only on the precedence graph and the stations, never
on input order, and every labelling satisfies the IE unfolded-U condition p_h <= p_i (section 6). The
station is ordered front tasks first, each after its predecessors, then back tasks, each after its
successors.

**Why the result is always feasible**

- Each station load is at most C, because a task is added only when it fits.
- Each task was eligible when it was added, so `place_station` can order the station (placing a task only
  makes more tasks eligible; see the `placement.py` docstring). The station passes `check_solution`.
- The loop always ends: an unassigned task with no unassigned predecessor always exists (the precedence
  graph has no cycles), and every task time is at most C (input validation), so a new empty station always
  takes at least one task.

## 3. Fitness

Lower is better (IE doc section 11, MASTER.md section 5, `fitness.py`):

    F = N + SI / (N * C)

N is the number of stations, SI the smoothness index sqrt( sum_j (ST_max - ST_j)^2 ), and C the cycle time.
SI <= sqrt(N - 1) * C, so the second term is below 1: one station fewer always beats any smoothing gain,
and SI only breaks ties between solutions with the same N. `compute_fitness` rounds F to 4 decimals.

## 4. Worked example: the 6-task contract example

Input `contracts/examples/six_task_input.json`: working time 480, no breaks, production 60, so
C = 480 / 60 = 8. Total work content = 4+3+5+2+5+4 = 23, N_min = ceil(23 / 8) = 3.

| Task | Time | Predecessors | Successors |
|---|---|---|---|
| A | 4 | - | B, C |
| B | 3 | A | D |
| C | 5 | A | D, E |
| D | 2 | B, C | F |
| E | 5 | C | F |
| F | 4 | D, E | - |

### 4.1 Chromosome `[A, F, B, C, D, E]` (hand-worked example)

| Step | Station | Assigned before step | Remaining time | Scan (first eligible that fits) | Added |
|---|---|---|---|---|---|
| 1 | 1 | - | 8 | A: no predecessors, eligible, 4 <= 8 | A |
| 2 | 1 | A | 4 | F: no successors, eligible, 4 <= 4 | F |
| 3 | 1 | A, F | 0 | nothing fits | close |
| 4 | 2 | A, F | 8 | B: predecessor A assigned, 3 <= 8 | B |
| 5 | 2 | A, F, B | 5 | C: predecessor A assigned, 5 <= 5 | C |
| 6 | 2 | A, F, B, C | 0 | nothing fits | close |
| 7 | 3 | A, F, B, C | 8 | D: predecessors B, C assigned, 2 <= 8 | D |
| 8 | 3 | ... , D | 6 | E: predecessor C assigned, 5 <= 6 | E |

Result: **A+F, B+C, D+E**. `place_station` labels them A front, F back (F was placed because its
successor set is empty, not because its predecessors were done); B, C, D, E front.

`contracts/examples/six_task_result.json` is the GA's actual output (seed 42): A+F, B+E, C+D, a
different solution with the same loads 8, 8, 7 and the same fitness 3.0417. Its labels are A front,
F back; B front, E back (its successor F is in station 1); C front, D back (its successor F is in
station 1, while its predecessor C is in the same station).

Loads 8, 8, 7. SI = sqrt(0^2 + 0^2 + 1^2) = 1. F = 3 + 1 / (3 * 8) = **3.0417**.
N = N_min, so this is optimal. Every 3-station solution has loads 8, 8, 7 in some order, so all optimal
solutions share this fitness.

### 4.2 Chromosome `[A, B, C, D, E, F]` (same tasks, worse order)

Station 1: A (4), B (3), load 7. C does not fit; D and E are not eligible; F is eligible (no successors)
but 4 > 1. Station 2: C (5), D (2), load 7. Station 3: E (5); F is now eligible (D, E assigned) but
4 > 3. Station 4: F (4).

Result A+B, C+D, E, F: N = 4, loads 7, 7, 5, 4, SI = sqrt(0 + 0 + 4 + 9) = 3.606,
F = 4 + 3.606 / 32 = **4.1127**. The order matters, and that is what the GA searches over.

### 4.3 Check on the IE doc example (section 8, C = 10)

Chromosome `[A, D, C, B, E, F, H, G]` decodes to A+D, B+C, E+F, G+H with loads 10, 10, 10, 9:
N = 4 = N_min, SI = 1, F = 4 + 1 / 40 = 4.025. This matches the IE doc's U-line result
(E = 97.5%, d = 2.5%). It becomes a test in task A.1.6.

Side labels under R2: A front, D back; B front, C back; E front, F front; G front, H back. This matches
the IE doc's table on all 8 tasks. The IE team confirmed R2 on 2026-11-27 and added it to the IE doc
(section 5, "Entry/exit labeling rule"); their corrected section 8 labels G entry side, since F is
assigned. The earlier question about B and G is closed: both are entry because their predecessor is in an
earlier station.

## 5. Operators

**Tournament selection.** Draw `tournament_size` chromosomes at random (with replacement) and return the
one with the lowest fitness. On a tie, the first one drawn wins.

**Order crossover (OX).** From parents P1 and P2, pick two cut points i <= j. The child keeps P1[i..j] in
place. The remaining positions, starting after j and wrapping around, are filled with the tasks of P2 in
P2's order (also starting after j and wrapping around), skipping tasks already in the child. The child is
always a permutation.

Example with P1 = `[A, B, C, D, E, F]`, P2 = `[F, E, D, C, B, A]`, i = 2, j = 3 (0-based):
the child keeps `C, D` at positions 2 and 3. P2 read from position 4 onward and wrapping is
B, A, F, E, D, C; without C and D this is B, A, F, E, which fills positions 4, 5, 0, 1.
Child = `[F, E, C, D, B, A]`.

**Swap mutation.** With probability `mutation_rate`, swap two random different positions of the child
(once per chromosome).

## 6. GA loop and parameters

1. **Seed.** Use the given seed, or draw one at random when it is `null`. All randomness goes through one
   `random.Random(seed)`. The seed used is reported. Same input + same seed = same result.
2. **Generation 0.** `population_size` random permutations. Decode and score each one.
3. **Next generation.** Copy the best `elitism_count` chromosomes unchanged. Fill the rest: select two
   parents by tournament; with probability `crossover_rate` the child is OX(parent1, parent2), otherwise
   a copy of parent1; then apply swap mutation. One child per pair.
4. **Record.** After each generation, record (generation, best fitness, average fitness) and call the
   progress callback.
5. **Stop** (see section 7). Return the best chromosome ever found, decoded and placed.

| Parameter | Default | Range (contract) | Meaning |
|---|---|---|---|
| population_size | 50 | 10 to 500 | chromosomes per generation |
| max_generations | 100 | 10 to 1000 | generations after generation 0 |
| crossover_rate | 0.8 | 0 to 1 | probability that a child comes from OX |
| mutation_rate | 0.1 | 0 to 1 | probability of one swap per child |
| elitism_count | 2 | >= 0 | best chromosomes copied unchanged |
| tournament_size | 3 | >= 2 | chromosomes per tournament |
| stagnation_limit | 30 | >= 1 | generations without improvement before stopping |
| seed | null | >= 0 or null | random seed |

Time limit: `MAX_RUN_SECONDS` (default 60 s), passed to `solve()` as `time_limit_s`.

## 7. Stop rules

Checked after each generation, in this order:

1. **time_limit**: elapsed time >= `time_limit_s`.
2. **stagnation**: the best fitness has not improved for `stagnation_limit` generations in a row.
   "Improved" means strictly lower than the best so far (fitness is rounded to 4 decimals).
3. **max_generations**: `max_generations` generations have run.

`generations_run` is the number of generations after generation 0. `stop_reason` is the rule that fired.
The result is always the best solution found so far, so a time-limit stop still returns a valid solution.

## 8. Choices made in this note

Confirmed by the integration engineer:

- Decoder: first eligible task that fits, scanning the chromosome from the start; close the station when
  none fits.
- Mutation: one swap per chromosome with probability `mutation_rate`.
- Generation 0: all random permutations.
- Convergence: recorded every generation.
- New generation: one child per pair of parents.

Smaller defaults proposed here (change them before A.1.4 / A.1.5 if needed):

- Tournament draws with replacement; ties go to the first drawn.
- OX is the classic version that fills from after the second cut point and wraps around.
- Stop rules are checked in the order time limit, stagnation, max generations.
- If `elitism_count` is not smaller than `population_size` (the contract sets no maximum), it is capped at
  `population_size - 1` so the population can still change.
- No early stop when N = N_min; the run continues so SI can still improve.
