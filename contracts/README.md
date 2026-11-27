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
| `examples/eight_task_input.json` | IE formulas document example, section 8 (8 tasks, cycle time 10; expected 4 stations, efficiency 97.5%) |

**Do not edit these files on your own.** Only the integration engineer changes contracts, together with the Pydantic models
(`backend/app/schemas/`), the example files and the frontend mocks (`frontend/src/mocks/`), in one reviewed pull request.

Cross-field validation rules that JSON Schema cannot express are listed in `MASTER.md` section 4 and implemented in
`backend/app/schemas/problem.py`. Fitness, workers and the max task count are provisional (see `docs/DECISIONS.md`).

## Authentication (designed in A.2.8, not built yet)

See `docs/DECISIONS.md`, "User accounts design". The JSON schemas do not change.

- Every `/runs` endpoint accepts an optional `Authorization: Bearer <Supabase access token>` header. No header: a guest.
- `GET /runs` lists only the caller's runs; a guest gets `[]`.
- `GET /runs/{id}` and `DELETE /runs/{id}` on another user's run: 404 `not_found`. Guests cannot delete runs.
- New errors, in the standard format `{"error": {"code", "message", "details": []}}`:
  - 401 `expired_token`: the token has expired; refresh it and retry.
  - 401 `invalid_token`: any other failed check (signature, unknown key, issuer, audience, malformed).
  - 503 `auth_unavailable`: the backend could not fetch Supabase's public keys, so it could not check the
    token. Retry later. Requests without a token are not affected.
