# Contracts

The agreement between the backend, the frontend and the ML module.

| File | What it describes |
|---|---|
| `problem_input.schema.json` | body of `POST /runs` and `POST /validate` |
| `run_result.schema.json` | the `result` of a succeeded run |
| `run_status.schema.json` | response of `GET /runs/{id}` |
| `examples/six_task_input.json` | worked example input (6 tasks, cycle time 8) |
| `examples/six_task_result.json` | the matching result (3 stations, efficiency 95.8%) |
| `examples/six_task_run_status_succeeded.json` | a full `GET /runs/{id}` response |

**Do not edit these files on your own.** Only the project lead changes contracts, together with the Pydantic models
(`backend/app/schemas/`), the example files and the frontend mocks (`frontend/src/mocks/`), in one reviewed pull request.

Cross-field validation rules that JSON Schema cannot express are listed in `MASTER.md` section 4 and implemented in
`backend/app/schemas/problem.py`. Fitness, workers and the max task count are provisional (see `docs/DECISIONS.md`).
