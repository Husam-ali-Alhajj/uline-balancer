# MASTER: U-Line Balancing App

The single source of truth for this project. Read this file fully before working on anything.
If this file and the code disagree, tell the project lead; do not guess.

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
a neural network that warm-starts the GA, phone layouts, user accounts (for now), special constraints
such as zoning or parallel stations.

## 2. Team and ownership

| Track | Owner | Works in | Notes |
|---|---|---|---|
| Backend, GA, integration, reviews | Project lead | `backend/app/` (all except `ml/`), `contracts/`, `docs/` | Merges every pull request |
| Frontend | Frontend engineer | `frontend/` | Builds against the mock API first |
| ML recommendations | AI engineer | `backend/app/ml/`, `backend/ml_training/` | Rule-based version already exists |
| Data and validation | Industrial engineering students | provide benchmark and real data | Real data is anonymised and never committed |

Ownership means "you change it". Changing a file outside your folder needs the project lead's approval.
Files in `contracts/` can only be changed by the project lead (see section 7).

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

**Inputs** (`contracts/problem_input.schema.json`): tasks (1 to 50), working time per day, production per
day, optional worker count, optional GA settings and seed.

**Validation rules** (backend `app/schemas/problem.py`, mirrored in the frontend):
unique task names, positive times, predecessors must exist, a task cannot precede itself, no cycles in the
precedence graph, every task time <= cycle time, at most 50 tasks, production >= 1.

**The U-line rule.** A task can be placed in the current station when
- all its predecessors are already assigned (it goes on the **front** leg), or
- all its successors are already assigned (it goes on the **back** leg).

Inside a station, tasks are ordered deterministically: repeat "place every task whose predecessors are all
assigned (front); if none, place the first task whose successors are all assigned (back)". A task is labelled
`back` only when it could not be placed as `front`. This is implemented in `backend/app/ga/placement.py`.

## 5. Formulas (single definition; code and docs must match)

Let m = number of stations, load_i = total task time in station i, C = cycle time, T = total work content.

| Name | Formula |
|---|---|
| Cycle time | C = working_time_per_day / production_per_day |
| Minimum stations | ceil(T / C) |
| Idle time of station i | C - load_i |
| Utilisation of station i | load_i / C |
| Efficiency | T / (m x C) |
| Balance delay | 1 - efficiency |
| Total idle time | m x C - T |
| Smoothness index | sqrt( sum over i of (max_load - load_i)^2 ) |
| Bottleneck stations | stations whose load equals the maximum load |
| High-idle stations | stations with idle time above 20% of C |
| Fitness (PROVISIONAL, D7) | m + smoothness_index / (m x C), lower is better |
| Suggested workers (PROVISIONAL, D3) | m (one per station); the user may override |
| Workload per worker | T / worker count |

The fitness tie-breaker is always below 1, so one extra station is always worse than any smoothing gain.

## 6. System architecture

```
 Browser (React)  <--JSON over HTTPS-->  FastAPI backend  <--SQL-->  Supabase Postgres
                                          |-- validation (Pydantic)
                                          |-- run service (start-and-poll)
                                          |-- GA engine   (pure Python)
                                          '-- recommender (pure Python, rule-based first)
```

- A **modular monolith**: one FastAPI app, separated modules, no microservices.
- **Only the backend talks to the database.** The frontend never calls Supabase. The database key stays
  on the server.
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
| `GET /runs` | list past runs (summary) |
| `DELETE /runs/{id}` | delete a finished run |
| `POST /validate` | dry-run validation plus cycle time and minimum stations |
| `GET /health` | liveness |

**Error format (every error):** `{"error": {"code": "...", "message": "...", "details": [{"field": "...", "message": "..."}]}}`

**Data model.** One table so far: `runs` (id, title, status, input JSON, result JSON, error JSON, progress,
model_version, timestamps). New tables only through an Alembic migration.

## 7. Modules and contracts

**GA (`backend/app/ga/`).** `placement.py` (U-line rule and the independent checker), `metrics.py`,
`fitness.py`, `engine.py` (entry point `solve()`), and stubs `decoder.py`, `operators.py`, `baseline.py`.
The current `engine.py` is a walking skeleton (valid but not optimised); the real GA replaces its body.
Planned design: permutation chromosome, decoder using the U-line rule (feasible by construction),
tournament selection, order crossover, swap mutation, elitism, stop on max generations or stagnation,
fixed seed for reproducibility. Written by the project lead step by step; do not replace it with a library.

**ML (`backend/app/ml/`).** `interface.py` defines `RecommendationInput`, `Recommendation` and the
`Recommender` protocol. `rule_based.py` is the fallback and ships first. A trained model implements the same
interface and is loaded in `registry.py`; if it fails, the rule-based recommender is used (a model failure
never blocks a result). Every recommendation names the metric that triggered it. Training code lives in
`backend/ml_training/`, never in `app/`.

**Contracts (`contracts/`).** JSON Schemas and examples are the agreement between all tracks:
- `problem_input.schema.json`, `run_result.schema.json`, `run_status.schema.json`
- `examples/six_task_*.json`: a worked 6-task example (A to F, cycle time 8, 3 stations)

The backend Pydantic models (`app/schemas/`) must match the schemas, and the tests check that the examples
satisfy both. The frontend mock API (MSW) is built from the same examples. **Contract changes** go through
the project lead: a pull request that updates the schema, the Pydantic model, the example and the mock
together, reviewed by all tracks.

## 8. Repository map

```
MASTER.md            this file
AI_RULES.md          rules every AI tool must follow in this repo
CONTRIBUTING.md      branches, pull requests, definition of done
contracts/           JSON schemas and examples (the contract)
docs/                requirements PDF, decision log, ticket template
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
- Branches, pull requests and the Definition of Done: see `CONTRIBUTING.md`.
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
8. Add dependencies only with the project lead's approval; keep versions pinned (lock files committed).

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

- The GA is a walking skeleton. The decoder, operators and baseline are stubs.
- The frontend has a working skeleton (example run, polling, one chart) but no input form and no real U diagram yet.
- The scaffold was assembled without internet access. The pure-Python parts (GA checker, metrics, ML rules, example
  consistency) were executed and pass. The FastAPI, Pydantic, SQLAlchemy, Alembic and frontend parts were written
  but not executed. **Ticket zero** is to run `pytest`, `ruff check .` and `npm run build`, and fix whatever fails.
