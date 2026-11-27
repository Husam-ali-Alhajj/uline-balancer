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

`contracts/examples/six_task_result.json` is the GA's actual output (seed 42) and is this same solution,
A+F, B+C, D+E, with the same labels.

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
2. **Generation 0.** `population_size` random permutations, except that the first one is replaced by the
   greedy chromosome: all tasks, largest time first (ties: input order). Decoded, that is the classic greedy
   that fills each station with the largest eligible task that fits. Decode and score each one.
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
- Generation 0: random permutations plus one greedy chromosome (largest task first); see "Quality".
- Convergence: recorded every generation.
- New generation: one child per pair of parents.

Smaller defaults proposed here (change them before A.1.4 / A.1.5 if needed):

- Tournament draws with replacement; ties go to the first drawn.
- OX is the classic version that fills from after the second cut point and wraps around.
- Stop rules are checked in the order time limit, stagnation, max generations.
- If `elitism_count` is not smaller than `population_size` (the contract sets no maximum), it is capped at
  `population_size - 1` so the population can still change.
- No early stop when N = N_min; the run continues so SI can still improve.

## 9. Quality

Measured with `backend/scripts/ga_quality.py` against exact optima (`app/ga/exact.py`): branch-and-bound
for up to 12 tasks, and dynamic programming for pure chains of any length. Instances: cycle time 20, task
times 1 to 20; chain = one line; wide = each task has one predecessor with probability 0.5; mixed = 1 or 2
predecessors among the 5 tasks before it. All seeds are fixed. Max settings = population 500, 1000
generations, stagnation limit 1000, 60 s limit.

**Main finding: N_min is often not reachable.** On 50-task chains the exact optimum is on average 3.0 stations
above N_min and never equal to it; on 8 to 12 tasks it equals N_min in only 33% to 90% of instances. A gap to
N_min is therefore not a GA error; quality is measured against the exact optimum where one is known.

### Before (30 instances x 3 seeds per row; runtimes measured with 14 runs in parallel)

| shape | size | exact = N_min | default = exact | default gap to exact | default gap to N_min | default runtime (s) | max = exact | max gap to exact | max gap to N_min | max runtime (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| chain | 8 | 57% | 100% | 0.00 | 0.47 | 0.15 | 100% | 0.00 | 0.47 | 28.85 |
| wide | 8 | 90% | 100% | 0.00 | 0.10 | 0.16 | 100% | 0.00 | 0.10 | 11.50 |
| mixed | 8 | 80% | 100% | 0.00 | 0.23 | 0.20 | 100% | 0.00 | 0.23 | 15.95 |
| chain | 10 | 40% | 100% | 0.00 | 0.67 | 0.33 | 100% | 0.00 | 0.67 | 52.00 |
| wide | 10 | 53% | 100% | 0.00 | 0.63 | 0.23 | 100% | 0.00 | 0.63 | 41.59 |
| mixed | 10 | 47% | 100% | 0.00 | 0.57 | 0.28 | 100% | 0.00 | 0.57 | 39.62 |
| chain | 12 | 33% | 100% | 0.00 | 0.83 | 0.40 | 100% | 0.00 | 0.83 | 57.46 |
| wide | 12 | 60% | 100% | 0.00 | 0.53 | 0.25 | 100% | 0.00 | 0.53 | 45.94 |
| mixed | 12 | 67% | 98% | 0.02 | 0.39 | 0.32 | 100% | 0.00 | 0.37 | 43.07 |
| chain | 50 | 0% | 64% | 0.38 | 3.41 | 4.54 | 96% | 0.04 | 3.08 | 60.43 |
| wide | 50 | n/a | n/a | n/a | 1.26 | 2.28 | n/a | n/a | 1.04 | 60.42 |
| mixed | 50 | n/a | n/a | n/a | 2.39 | 4.69 | n/a | n/a | 1.94 | 60.63 |

Gaps are in stations, averaged over runs. Up to 12 tasks the defaults find the optimum in 808 of 810 runs.
The weak spot is 50 tasks, where max settings do clearly better than the defaults.

### Improvements tried (default settings, 50 tasks)

Tuned on one set of instances (set A: 20 per shape x 3 seeds); the final numbers below come from a fresh set
(set B) never used while tuning. Chains are scored against the exact optimum; wide and mixed against the best
result max settings found on the same instance (best known), since no exact solver reaches them.

| change | result on set A | kept |
|---|---|---|
| (a) one greedy chromosome (largest task first) in generation 0 | wide 0.25 -> 0.00, mixed 0.40 -> 0.20, chain 0.33 -> 0.38 (3 more runs one station worse, out of 60); same runtime | yes |
| (b) insertion and inversion mutation next to swap (one of the three at random) | no gain (chain 0.35, wide 0.25, mixed 0.45) | no |
| (c) population and stagnation limit scaled with the task count | population 2n: better (chain 0.22, wide 0.13, mixed 0.30) but 3 to 4 times slower; n or 0.6n: no gain and slower | no |
| (a) + (b) | same as (a) alone within noise | (a) only |

### After (set B; gap to exact for chains, to best known for wide and mixed)

Reproduce with `python scripts/ga_tune.py --set B --size 50 --count 20` and `--size 12 --count 30`.

| shape | size | runs | greedy alone: gap | greedy alone: = ref | before: gap | before: = ref | after: gap | after: = ref | before runtime (s) | after runtime (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| chain | 50 | 20 x 3 | 0.95 | 25% | 0.30 | 70% | 0.18 | 82% | 0.89 | 0.80 |
| wide | 50 | 20 x 3 | 0.00 | 100% | 0.27 | 73% | 0.00 | 100% | 0.38 | 0.37 |
| mixed | 50 | 20 x 3 | 0.60 | 45% | 0.68 | 33% | 0.35 | 62% | 0.70 | 0.68 |
| chain | 12 | 30 x 3 | 0.03 | 97% | 0.00 | 100% | 0.00 | 100% | | |
| wide | 12 | 30 x 3 | 0.03 | 97% | 0.00 | 100% | 0.00 | 100% | | |
| mixed | 12 | 30 x 3 | 0.13 | 87% | 0.04 | 96% | 0.03 | 97% | | |

- "Greedy alone" is the greedy chromosome decoded once, with no GA (one result per instance).
- The wide and mixed references at 50 tasks come from max-settings runs that stop on the 60 s time limit, so
  they can differ slightly between machines and runs (mixed moved by 0.05 between two runs; chain and wide
  did not move).
- Runtimes: mean of 10 instances, 1 seed, one process on an idle machine (the 2 s budget for 50 tasks).
- Greedy seeding halves the gap on 50 tasks, keeps the 12-task rate and costs no time. It replaces one random
  chromosome, so all other random draws and the determinism guarantee stay the same.

**The greedy start and the baseline.** Generation 0 includes the largest-task-first chromosome, which is the same
idea as the planned baseline heuristic (largest task first with the U-line rule). Elitism keeps the best
chromosome, so the GA result is never worse than that starting point, by construction. Any GA-vs-baseline
comparison must say this: the GA cannot lose to a largest-task-first baseline, and the fair measure of the GA
itself is its improvement over the greedy start (the "greedy alone" columns). That improvement is large on
chains (0.95 to 0.18 stations) and mixed graphs (0.60 to 0.35), and zero on 50-task wide graphs, where the
greedy alone already matches the best known result. Before this change the GA's defaults did worse than the
greedy alone on wide and mixed graphs (0.27 and 0.68 against 0.00 and 0.60).
