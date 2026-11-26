# Decision log

Update this file when a decision is made. IDs D1 to D18 refer to `ULine_Requirements_and_Decisions_v0.1.pdf`.
Status: **Decided**, **Provisional** (the scaffold uses this value until the meeting decides), **Open**.

## Decided

| Decision | Choice | Reason |
|---|---|---|
| D5 Run execution | Start and poll (`POST /runs` returns an id, `GET /runs/{id}` polls) | Robust against long runs and page reloads; hard to retrofit later |
| Architecture | Modular FastAPI monolith; only the backend talks to Supabase; GA and ML are pure modules; GA runs in a separate process | Simple, secure, testable |
| GA implementation | Write our own small GA (no DEAP) | Custom decoder and fitness anyway; must be fully understood and explainable |
| Database access | SQLAlchemy 2 + Alembic migrations | Standard, versioned schema changes |
| Frontend mocks | MSW kept | Frontend can build every screen before the backend exists |
| Docker | Not used | Time constraints; venv and plain hosting are enough |
| Phones | Out of scope; desktop-first, usable on a tablet | Scope and time |
| Removed from stack | pydantic-settings, uv, slowapi (rate limiting is a Should), frontend unit tests | Time constraints |
| Branching | Long-lived track branches `Frontend` and `AI`, controlled and merged by the integration engineer at least weekly | Teammates are new to git and work in separate folders; teammates never merge or create branches |
| D4 | User accounts with saved previous calculations are required (planned: Supabase Auth, owner on each run, implemented later) | Needed so a user can reopen past runs |
| Cycle time accounts for break and down time (`break_time_per_day`) | `C = (working_time_per_day - break_time_per_day) / production_per_day` | Raw working time overstates available capacity |
| Cycle time upper bound | Input is rejected when C > Σt (total work content) | IE formulas document section 2: max(tᵢ) <= C <= Σt |
| Formulas and notation | MASTER.md section 5 follows the IE formulas document (latest version); LV and gap to N_min added (code in A.1.7) | One definition for code, report and IE team |
| Side labels (R2) | Front if all predecessors are in earlier stations; else back if all successors are in earlier stations; then front closure inside the station; the rest back (`ga/placement.py`, `docs/GA_DESIGN.md` section 2) | Follows the IE document's own reasons in section 8. The previous rule (front closure first, R0) was already independent of input order; the change is to match the IE reasoning. Decided in Sprint 2 task A.2.3. **Confirmed by the IE team on 2026-11-27**: they added the rule to the IE formulas document (section 5, "Entry/exit labeling rule") and corrected section 8 to G entry, so all 8 labels match. The B/G question is closed |
| GA design | `docs/GA_DESIGN.md`: first-eligible-that-fits decoder, one swap per chromosome with probability `mutation_rate`, random generation 0, convergence every generation, one child per parent pair | Decided in Sprint 1 task A.1.2 |

## Provisional (implemented in the scaffold, to be confirmed)

| ID | Value used | Where |
|---|---|---|
| D1 | Type 1 only (minimise stations for a given cycle time) | whole project |
| D2 | Max 50 tasks | `schemas/problem.py`, `problem_input.schema.json` |
| D3 | Suggested workers = number of stations; user may override; used for reporting only | `services/solver.py` |
| D7 | Fitness = stations + smoothness_index / (stations x cycle_time) | `ga/fitness.py`, MASTER.md section 5 |
| D11 | Frontend in plain JavaScript (JSX), Tailwind only, no component library | `frontend/` |

## Open

| ID | Question |
|---|---|
| D6 | Special constraints (zoning, fixed tasks, parallel stations): none for the MVP? |
| D8 | Baseline heuristic and the GA success target (set the number after the baseline exists) |
| Straight-line baseline | IE formulas document section 10 asks to also compare against a straight-line baseline. Add it (needs a contract change), or keep only the U-line baseline? |
| D9 | What exactly does the ML module predict or recommend? |
| D10 | ML training data: how it is generated and how much |
| D12 | Where the app is deployed and who keeps it running |
| D13 to D18 | Repository rules, sprint rhythm, contract freeze date, cut list, benchmark instances, ownership: proposed in the PDF and in CONTRIBUTING.md and MASTER.md |
