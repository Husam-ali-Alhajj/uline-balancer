# MASTER: U-Line Balancing App

The single source of truth for this project. Read this file fully before working on anything.
If this file and the code disagree, tell the integration engineer; do not guess.

Status: scaffold v0.1 (October 2026). Open decisions are listed in `docs/DECISIONS.md`.

---

## 1. What we are building

A web application for the ILE 401 capstone (Cyprus International University). A user enters the tasks
of an assembly process (name, time in minutes, which tasks must come first), the working time per day
and the daily production. The system computes the cycle time, then uses a **Genetic Algorithm (GA)** to
assign tasks to stations of a **U-shaped assembly line**, and shows the result as a U diagram with
metrics, charts and short recommendations. Every run is stored so it can be reopened later.

**Goals**
- A correct GA: every returned solution respects precedence, the U-line rule and the cycle time.
- A clean, secure web app that is easy to run, understand and demo.
- A small ML layer that turns result metrics into written recommendations.

**Not goals** (out of scope, do not build): simulation, real-time line control, reinforcement learning,
a neural network that warm-starts the GA, phone layouts, special constraints such as zoning or parallel
stations.

User accounts with saved calculations (Supabase Auth): the backend part is built (A.2.9); the frontend sign-in
is not built yet.

## 2. Team and ownership

| Track | Owner | Works in | Notes |
|---|---|---|---|
| Backend, GA, integration, reviews | Integration engineer | `backend/app/` (all except `ml/`), `contracts/`, `docs/` | Merges every pull request |
| Frontend | Frontend engineer | `frontend/` | Builds against the mock API first |
| ML recommendations | AI engineer | `backend/app/ml/`, `backend/ml_training/` | Rule-based version already exists |
| Data and validation | Industrial engineering students | provide benchmark and real data | Real data is anonymised and never committed |

Ownership means "you change it". Changing a file outside your folder needs the integration engineer's approval.

Branches: `Frontend` (frontend engineer), `AI` (AI engineer), `main` (integration engineer, Track A, as an exception). The integration engineer merges
everything; see CONTRIBUTING.md.

Files in `contracts/` can only be changed by the integration engineer (see section 7).

## 3. Glossary

- **Task**: one unit of work with a time in minutes.
- **Precedence**: "task B needs task A done first". Written as B has predecessor A.
- **Station**: a work position on the line. All tasks of one station together must fit in the cycle time.
- **Cycle time (C)**: working time per day / production per day. The time budget of every station.
- **U-line**: a line bent into a U so that the first and last stations are close together. Workers can
  therefore handle tasks from both ends of the process in one station.
- **Front / back**: the two legs of the U. See the U-line rule below.
- **Chromosome**: in the GA, one candidate solution encoded as an ordered list (permutation) of task names.
- **Decoder**: turns a chromosome into stations. **Fitness**: a number scoring a solution (lower is better).
- **Run**: one execution of the solver on one input. Has a status and, when done, a result.
- **Walking skeleton**: a thin end-to-end version of the whole system, built first and improved piece by piece.

## 4. The problem (Type 1)

Given tasks, precedence and a cycle time C: use as **few stations as possible** so that no station's
total task time exceeds C and the U-line rule holds. Secondary goal: workloads as even as possible.

**Inputs** (`contracts/problem_input.schema.json`): tasks (1 to 50), working time per day, break and down
time per day (zero or more, below the working time), production per day, optional worker count, optional
GA settings and seed.

**Validation rules** (backend `app/schemas/problem.py`, mirrored in the frontend):
unique task names, positive times, predecessors must exist, a task cannot precede itself, no cycles in the
precedence graph, every task time <= cycle time, cycle time <= total work content (max(tᵢ) <= C <= Σt,
IE formulas document section 2), at most 50 tasks, production >= 1, break and down time per day smaller
than the working time per day.

**The U-line rule.** A task can be placed in the current station when
- all its predecessors are already assigned (it goes on the **front** leg), or
- all its successors are already assigned (it goes on the **back** leg).

**Side labels (rule R2).** Inside a station, a task is labelled:
1. `front` if all its predecessors are in earlier stations;
2. else `back` if all its successors are in earlier stations;
3. then, repeatedly, `front` if all its predecessors are in earlier stations or are `front` tasks of this
   station (front closure);
4. every remaining task is `back`.

The labels depend only on the precedence graph and the stations, never on input order, and steps 1 and 2 follow
the IE document's reasoning (section 8). A station is ordered front tasks first, each after its predecessors, then
back tasks, each after its successors. This is implemented in `backend/app/ga/placement.py`.

## 5. Formulas (single definition; code and docs must match)

Source: the IE team's *U-Shaped Assembly Line Balancing: Formulas and Worked Example*
(`U-Shaped_Assembly_Line_Balancing_Formulas_updated.docx`, the latest version), sections 1 to 3 and 11.
The notation follows that document.

Notation: n = number of tasks, tᵢ = time of task i, C = cycle time, N = number of stations used,
STⱼ = station time of station j (sum of its task times), STmax = the largest STⱼ, Σt = total work content.

| Name | Formula |
|---|---|
| Available time per day | working_time_per_day - break_time_per_day |
| Cycle time | C = (working_time_per_day - break_time_per_day) / production_per_day |
| Cycle time bounds | max(tᵢ) <= C <= Σt (both checked by input validation) |
| Minimum stations | N_min = ceil(Σt / C) |
| Idle time of station j | Iⱼ = C - STⱼ |
| Utilisation of station j | Uⱼ = STⱼ / C |
| Efficiency | E = Σt / (N x C) |
| Balance delay | d = 1 - E = (N x C - Σt) / (N x C) |
| Total idle time | TIT = N x C - Σt |
| Smoothness index | SI = sqrt( sum over j of (STmax - STⱼ)^2 ) |
| Idle-time variation | LV = sqrt( sum over j of (C - STⱼ)^2 / N ) |
| Gap to the minimum | Gap = (N - N_min) / N_min |
| Throughput rate (reference only, not computed) | 1 / C |
| Bottleneck stations | stations whose STⱼ equals STmax |
| High-idle stations | stations with Iⱼ above 20% of C |
| Fitness (PROVISIONAL, D7) | F = N + SI / (N x C), lower is better |
| Suggested workers (PROVISIONAL, D3) | N (one per station); the user may override |
| Workload per worker | Σt / worker count |

E, d, Gap and Uⱼ are stored as fractions (0.975) in the API and shown as percentages (97.5%) in the UI.
Lower SI and LV mean a smoother balance. SI <= sqrt(N - 1) x C, so the fitness tie-breaker is always
below 1 and one extra station is always worse than any smoothing gain.

## 6. System architecture

```
 Browser (React)  <--JSON over HTTPS-->  FastAPI backend  <--SQL-->  Supabase Postgres
   |  (sign-in only)                      |-- sign-in token check (app/auth.py)
   '---> Supabase Auth                    |-- validation (Pydantic)
                                          |-- run service (start-and-poll)
                                          |-- GA engine   (pure Python)
                                          '-- recommender (pure Python, rule-based first)
```

- A **modular monolith**: one FastAPI app, separated modules, no microservices.
- **Only the backend talks to the database.** The frontend never reads or writes Supabase tables. Its only
  Supabase call is sign-in (Supabase Auth, with the public publishable key); it then sends the user's access
  token to our backend. The database key stays on the server.
- The GA and the recommender are **pure modules**: no web, no database. Plain data in, plain data out.
- The GA is CPU-bound, so runs execute in a **separate process** (`ProcessPoolExecutor`, `spawn`).

**Run lifecycle (start and poll).**
1. `POST /runs` validates the input, creates a run (`queued`), starts the solver, returns `202` and the run id.
2. The worker sets `running`, runs the GA, and stores the result: `succeeded`, or `failed` with a safe message.
3. The frontend polls `GET /runs/{id}` every 1.5 s until `succeeded` or `failed`. It can reload the page and keep polling.
4. On server start, any run still `queued` or `running` is marked `failed` (`server_restarted`).

**Endpoints**

| Method and path | Purpose |
|---|---|
| `POST /runs` | validate, create and start a run; returns `{run_id, status}` |
| `GET /runs/{id}` | status, progress, and the result once `succeeded` |
| `GET /runs` | list the caller's past runs (summary); a guest gets `[]` |
| `DELETE /runs/{id}` | delete a finished run (owner only) |
| `POST /validate` | dry-run validation plus cycle time and minimum stations |
| `GET /health` | liveness |

**Users and guests** (`docs/DECISIONS.md`, "User accounts design"). Every `/runs` endpoint takes an optional
`Authorization: Bearer <Supabase access token>` header. No header: a guest. A signed-in user's runs get
`owner_id` = their user id; `GET /runs` lists only their runs, and someone else's run answers 404. A guest run
(`owner_id` NULL) is never listed, is readable by anyone with its id, and cannot be deleted through the API.
Tokens are checked in the backend (`app/auth.py`): ES256 signature with the project's public keys (cached
10 minutes), expiry with 30 s leeway, issuer and audience. Errors: 401 `invalid_token` or `expired_token`,
503 `auth_unavailable` when the keys cannot be fetched. Sign-in is off when `SUPABASE_URL` is not set.

**Error format (every error):** `{"error": {"code": "...", "message": "...", "details": [{"field": "...", "message": "..."}]}}`

**Data model.** One table so far: `runs` (id, owner_id, title, status, input JSON, result JSON, error JSON,
progress, model_version, timestamps). New tables only through an Alembic migration. A saved result is loaded
with loose settings (`StoredGASettings`): today's `GASettings` limits apply to new requests only.

## 7. Modules and contracts

**GA (`backend/app/ga/`).** `placement.py` (U-line rule and the independent checker), `metrics.py`,
`fitness.py`, `decoder.py`, `operators.py`, `engine.py` (entry point `solve()`, the GA loop), and the
stub `baseline.py` (Track C). The design is set in `docs/GA_DESIGN.md` (with a hand-worked 6-task example): permutation chromosome; a
decoder that fills each station with the first eligible task (IE formulas document section 5) that fits,
so every solution is feasible by construction; tournament selection, order crossover, swap mutation,
elitism; stop on time limit, stagnation or max generations; fixed seed for reproducibility. Written by the
integration engineer step by step; do not replace it with a library.

**ML (`backend/app/ml/`).** `interface.py` defines `RecommendationInput`, `Recommendation` and the
`Recommender` protocol. `rule_based.py` is the fallback and ships first. A trained model implements the same
interface and is loaded in `registry.py`; if it fails, the rule-based recommender is used (a model failure
never blocks a result). Every recommendation names the metric that triggered it. Training code lives in
`backend/ml_training/`, never in `app/`.

**Contracts (`contracts/`).** JSON Schemas and examples are the agreement between all tracks:
- `problem_input.schema.json`, `run_result.schema.json`, `run_status.schema.json`
- `examples/six_task_*.json`: a worked 6-task example (A to F, cycle time 8, 3 stations)
- `examples/eight_task_input.json`: the IE formulas document example, section 8 (cycle time 10, 4 stations)

The backend Pydantic models (`app/schemas/`) must match the schemas, and the tests check that the examples
satisfy both. The frontend mock API (MSW) is built from the same examples. **Contract changes** go through
the integration engineer: a pull request that updates the schema, the Pydantic model, the example and the mock
together, reviewed by all tracks.

## 8. Repository map

```
MASTER.md            this file
AI_RULES.md          rules every AI tool must follow in this repo
CONTRIBUTING.md      branches, pull requests, definition of done
contracts/           JSON schemas and examples (the contract)
docs/                requirements PDF, decision log, GA design note, ticket template
backend/             FastAPI app, GA, ML, database, tests (see backend/README.md)
frontend/            React app and mock API (see frontend/README.md)
.github/             CI workflow and pull request template
```

## 9. Technology and why

| Choice | Why |
|---|---|
| Python 3.12 | one language for API, GA and ML |
| FastAPI + Pydantic | validation built in, automatic API docs, little boilerplate |
| Own GA (no DEAP) | the decoder and fitness are custom anyway; small enough to understand and explain fully |
| SQLAlchemy 2 + Alembic | standard tools, versioned migrations so the schema never drifts |
| Supabase (Postgres) | hosted database with a free tier; plain Postgres underneath |
| scikit-learn | a small tabular model is enough; deep learning would be far too heavy |
| React + Vite | decided; fast to start; no server-side rendering needed |
| TanStack Query | built-in polling for the start-and-poll design |
| Tailwind, Recharts, custom SVG | styling, standard charts, and a hand-made U diagram |
| MSW | frontend works against fake responses from day one |
| pytest, Ruff, GitHub Actions | tests and lint run automatically on every pull request |

Deliberately NOT used: Docker, Celery/Redis, microservices, Next.js, Prisma, TypeScript (for now).

## 10. How we work

- Two-week sprints. Sprint 0 is week 1 (setup, contracts, walking skeleton). Every sprint ends with an
  end-to-end demo, not "70% of the backend".
- Work comes as small tickets (`docs/TICKET_TEMPLATE.md`) with a clear done-criteria list.
- Branch model, the integration routine and the Definition of Done: see `CONTRIBUTING.md`.
- AI tools are allowed and expected, under the rules in `AI_RULES.md`. You are responsible for every line you commit.
- Feature freeze at the start of week 7; weeks 7 and 8 are testing, polish, documentation and the demo.
- Cut list if time runs short (first to last): run comparison, exports, precedence preview, ML polish.
  The core (GA, API, U diagram) is never cut.

## 11. Security rules (always apply)

1. All input from the browser is untrusted. The backend validates everything (Pydantic) even if the frontend did.
2. Limits: at most 50 tasks, request body limit, run time limit, cap on concurrent runs.
3. Secrets only in environment variables or `.env` files. `.env` is never committed. The database key is never in the frontend.
4. Only the backend talks to the database. Use the ORM; never build SQL from strings.
5. CORS allows only the frontend origin. HTTPS in deployment.
6. Errors shown to users are short and safe, never stack traces.
7. Real factory data is anonymised and never committed. Benchmark datasets are credited to their source.
8. Add dependencies only with the integration engineer's approval; keep versions pinned (lock files committed).
9. Sign-in tokens are verified in the backend on every request that sends one, and never logged. Only ES256 is
   accepted. A bad or expired token is rejected (401), never treated as a guest.
10. The frontend uses only the publishable (anon) key, for sign-in. The secret (service_role) key is never in the
   frontend. RLS stays on with no policies (migration 0002), so that key cannot reach any table.
11. Someone else's run answers 404, the same as a run that does not exist, so ids of other users' runs are not
   confirmed.

## 12. Roadmap

| Sprint | Weeks | Goal |
|---|---|---|
| 0 | 1 | Everyone runs the scaffold. Ticket zero: run the tests and the build, fix what breaks. Freeze contracts. Deploy a first version. |
| 1 | 2-3 | Real GA validated on benchmark instances; input form and U diagram on the mock API, then the real API |
| 2 | 4-5 | Metrics and charts, run history, ML recommendations integrated |
| 3 | 6-7 | Hardening: edge cases, security pass, performance, UX polish, documentation |
| Final | 8 | Feature freeze, bug fixes, demo rehearsal, report |

## 13. Running everything

Backend: `backend/README.md`. Frontend: `frontend/README.md`. Quick version:
`cd backend && pip install -r requirements-dev.txt && alembic upgrade head && uvicorn app.main:app --reload`
and in another terminal `cd frontend && npm install && npm run dev`.

## 14. Known gaps in this scaffold (be honest about them)

**Ticket zero is done.** `ruff check .`, `pytest` and `npm run build` run and pass.

Known gaps:

- GA: the real GA runs behind the API (Sprint 1, Track A). The baseline is still a stub (task C.1.2).
- GA performance (Sprint 1 measurement, 50 tasks, 3 seeds per graph shape): the defaults finish in under
  1 s. With the largest population and generation settings (500 and 1000) and the default
  stagnation limit (30), a run takes 4 to 21 s and stops on stagnation. It reaches the 60 s time limit
  only when `stagnation_limit` is raised as well (tested with 1000).
- GA quality: with the default settings, 50-task chains end 2 to 3 stations above N_min (mixed graphs 1,
  wide graphs 0). The largest settings bring chains to 1 above N_min.
- GA memory: the fitness cache keeps at most 20,000 chromosomes (least recently used dropped first,
  `FITNESS_CACHE_SIZE` in `ga/engine.py`); results are the same with any size (A.2.7). Worst case measured
  (50 tasks, population 500, 1000 generations, stagnation limit 1000, 60 s limit): the run adds about
  14 MB at its peak instead of about 42 MB unbounded (peak process 31 MB instead of 60 MB), with the
  same runtime, generations and result. Unbounded, the cache would keep growing with run length.
- Validation: the backend rejects a cycle time longer than the total work content; the frontend does not
  check this yet.
- Comparison with a straight-line baseline (IE formulas document section 10) is an open decision.
- Frontend: no input form and no real U diagram yet.
- Supabase: connected and tested (A.2.4, see `backend/README.md`, "Using Supabase"). About 300 ms per round
  trip from the development machine; one `GET /runs/{id}` takes about 1.1 s.
- User accounts: backend done (A.2.9); the frontend sign-in (Track B) is not built yet. Guest runs are never
  cleaned up yet (a later job). Not done yet: deployment.
