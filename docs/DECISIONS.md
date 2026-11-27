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
| Cycle time accounts for break and down time (`break_time_per_day`) | `C = (working_time_per_day - break_time_per_day) / production_per_day` | Raw working time overstates available capacity |
| Cycle time upper bound | Input is rejected when C > Σt (total work content) | IE formulas document section 2: max(tᵢ) <= C <= Σt |
| Formulas and notation | MASTER.md section 5 follows the IE formulas document (latest version); LV and gap to N_min added (code in A.1.7) | One definition for code, report and IE team |
| Side labels (R2) | Front if all predecessors are in earlier stations; else back if all successors are in earlier stations; then front closure inside the station; the rest back (`ga/placement.py`, `docs/GA_DESIGN.md` section 2) | Follows the IE document's own reasons in section 8. The previous rule (front closure first, R0) was already independent of input order; the change is to match the IE reasoning. Decided in Sprint 2 task A.2.3. **Confirmed by the IE team on 2026-11-27**: they added the rule to the IE formulas document (section 5, "Entry/exit labeling rule") and corrected section 8 to G entry, so all 8 labels match. The B/G question is closed |
| GA design | `docs/GA_DESIGN.md`: first-eligible-that-fits decoder, one swap per chromosome with probability `mutation_rate`, random generation 0, convergence every generation, one child per parent pair | Decided in Sprint 1 task A.1.2 |
| Branch model | The integration engineer (Track A) works directly on `main`; `develop` is retired; Tracks B and C keep their `Frontend` and `AI` branches, merged by the integration engineer | One integration point that is always green; fewer branches for a team new to git |
| Database | Supabase Postgres in Frankfurt (eu-central-1), via the session pooler with `sslmode=require`; RLS on for every table with no policies (migration 0002) | Closest region to the team and the planned hosts; RLS blocks Supabase's public roles, and only the backend (table owner) reaches the data |
| D12 Deployment | Postponed. Plan: frontend on Vercel, backend on Koyeb (it can run the background GA worker; Vercel cannot). Ready: `backend/Procfile` and `backend/.python-version`. Not written yet: the deployment guide. Development and the demo run locally | Finish the features first; local runs are enough for the demo |
| Versions and connections | Direct dependencies pinned with `==`; CI on Python 3.12. Database connections per process: server 3 + 2 overflow, each GA worker 1 + 0, so 7 in total with 2 workers | Reproducible installs; stays well under the Supabase free-plan pooler limit (15) |
| User accounts (D4) | Built in the backend as designed in "User accounts design" below: optional Supabase sign-in token, runs scoped to their owner, guest runs by id only. Frontend sign-in not built yet | Users can reopen their own past runs; guests can still use the app |
| Fitness cache bound | At most 20,000 chromosomes, least recently used dropped first (`FITNESS_CACHE_SIZE` in `ga/engine.py`); not a GA setting | Memory stays bounded on long runs; results are identical with any cache size |

## User accounts design (D4, task A.2.8)

Decided by the integration engineer on 2026-11-27. The backend part is built; the frontend sign-in is not.
Sources: the Supabase Auth docs (`guides/auth/signing-keys`, `guides/auth/jwts`, `guides/auth/jwt-fields`,
`guides/auth/sessions`, `guides/api/api-keys`), read on 2026-11-27.

**1. Guest runs (no token).** Allowed. `owner_id` is NULL. The run is reachable only by its id (a random UUID4,
so it cannot be guessed) and is never listed: `GET /runs` without a token returns `[]`. Anyone who has the id
can view the run, guest or signed in. **Guests cannot delete** a run, and since a guest run has no owner, no one
can delete it through the API. Trade-off: guest runs stay in the database until a cleanup job removes them
(not designed yet). The alternative, a delete token returned once by `POST /runs`, was rejected: it needs a new
response field and a new column (a contract change), and the frontend would have to keep a secret the user can lose.

**2. Signed-in users.** `owner_id` = the Supabase user id (the token's `sub` claim, a UUID). `GET /runs` lists
only the caller's runs. `GET` or `DELETE` on a run owned by someone else returns **404 `not_found`**, not 403,
so the API does not reveal that the run exists. Only the owner can delete their run (409 `run_in_progress` still
applies). Schema change: a new Alembic migration adds a nullable, indexed `owner_id` column to `runs`.

**3. Token verification: local, with Supabase's public keys.**
- *Our project:* the Frankfurt project signs user tokens with an **asymmetric ES256 key** (P-256 curve).
  Checked on 2026-11-27 by reading its public key set (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`):
  one key, `alg` ES256, `kty` EC, `crv` P-256, served with `Cache-Control: max-age=600`.
  In the dashboard: the JWT signing keys page, `supabase.com/dashboard/project/_/settings/jwt`
  (open it from your project); the "⋮" menu next to a key → "View key details" shows its public key set.
- *Choice:* verify each token **in the backend** with PyJWT. Rejected: calling Supabase's `/auth/v1/user` on every
  request. That call does notice sign-out at once, but it adds a network round trip to every request, makes our
  API fail when Supabase Auth is down, and the Supabase docs advise against it on servers ("can be slow").
  Trade-off of the local check: a token stays valid until it expires even after the user signs out (Supabase's
  default and recommended expiry is 1 hour). That is acceptable here: a stolen token could at most read or delete
  that user's runs for the rest of the hour.
- *Checks on every token:*
  - signature, with algorithm **ES256 only** (fixed allow-list; the token header can never choose the algorithm,
    which blocks forged `none` or HS256 tokens);
  - `exp` (expiry) and `iat`, with **30 s leeway** for clock differences between our server and Supabase (the
    Supabase docs give no number; 30 s is common practice);
  - `iss` must equal `<SUPABASE_URL>/auth/v1`;
  - `aud` must equal `authenticated`, and `is_anonymous` must not be true: Supabase's anonymous sign-ins are not
    accepted (keep them off in the dashboard), because our guest mode already covers users without an account;
  - `sub` must be present.
- *Public keys:* fetched and cached by PyJWT's own `PyJWKClient`, not by code of ours:
  `PyJWKClient("<SUPABASE_URL>/auth/v1/.well-known/jwks.json", lifespan=600, timeout=5)`.
  - `lifespan=600`: the key set is kept in memory for **10 minutes**, the same as Supabase's own cache (the docs
    say not to cache longer). PyJWT's default is 5 minutes.
  - Unknown key id (`kid`): `PyJWKClient` refetches the key set once and retries, so a key rotation keeps
    working. It refetches at most once every 30 s (its `cooldown_duration` default), so a flood of tokens with
    made-up key ids cannot make us hammer Supabase. Still unknown after that: 401 `invalid_token`.
  - `timeout=5`: a short network timeout (PyJWT's default is 30 s), so a slow key page cannot hold requests
    for long.
- *Key page unreachable:* if the key set cannot be fetched (`PyJWKClientConnectionError`: network error or
  timeout), a request **with** a token gets **503 `auth_unavailable`** in the standard error format; the token is
  neither accepted nor called invalid, because we could not check it. Requests **without** a token still work as
  guests. While the cached key set is less than 10 minutes old, no fetch is needed, so a short outage is not
  noticed.
- *Configuration:* a new env var `SUPABASE_URL` (`https://<project-ref>.supabase.co`). It is a public address,
  not a secret, but it lives in `backend/.env` so no project id is committed. If it is not set (tests, local
  without auth), every request is a guest and any token is rejected with `invalid_token`.
- *Dependencies* (**approved by the integration engineer on 2026-11-27**, not installed yet): `PyJWT==2.15.1`
  (reads and checks tokens, and fetches the keys) and `cryptography==50.0.2` (the ES256 signature math), pinned on
  two separate lines; the `PyJWT[crypto]` extra would leave `cryptography` unpinned. Checked with a dry-run
  download for Linux x86_64, CPython 3.12 (binary wheels only): `pyjwt-2.15.1-py3-none-any.whl` and
  `cryptography-50.0.2-cp311-abi3-manylinux_2_28_x86_64.whl` both exist; `cryptography` also pulls `cffi` (2.1.1)
  and `pycparser` (3.12) as its own dependencies, unpinned like all indirect dependencies. No Supabase Python
  client is needed.

**4. API.** An optional `Authorization: Bearer <access token>` header on every `/runs` endpoint; no header means
a guest. A header that is present but fails a check gives **401** in the standard error format:
`expired_token` (only `exp` failed) or `invalid_token` (anything else: bad signature, unknown key, wrong issuer or
audience, malformed, auth not configured). It is never treated as a guest, so a signed-in user cannot create an
ownerless run by mistake. If the keys cannot be fetched: **503 `auth_unavailable`** (point 3). No new fields in `run_status` or `run_result`; the JSON schemas do not change.

**5. Frontend (note for Track B, to build later).** Sign-in uses the Supabase JS client with the project URL and
the **publishable (anon) key**. That key is meant to be public ("safe to expose online", Supabase docs) and is
harmless here because RLS blocks it from every table (point 6). The frontend sends only the user's access token
to our backend, in the `Authorization` header; it never calls Supabase tables. supabase-js refreshes the token
automatically; on a 401 `expired_token` the frontend refreshes and retries once. The secret (service_role) key is
never used in the frontend.

**6. RLS.** Stays on with no policies (migration 0002). The public roles (`anon`, `authenticated`) cannot read or
write `runs`; our backend connects as the table owner, which bypasses RLS. Ownership is enforced in the backend
(point 2), not by RLS policies.

**Later** (not part of this design):
- A cleanup job that deletes old guest runs (they have no owner, so nobody can delete them through the API).

**Could not verify** (the docs read do not say it): what new projects use by default and since when (our project
was checked directly instead); the exact place in the dashboard that names the algorithm; any Supabase guidance on
clock-skew leeway; rate limits on `/auth/v1/user`; an explicit statement that a signed-out access token keeps
working until it expires (the sessions page implies it: it says an extra check against `auth.sessions` is needed
to block it).

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
| D8 | Baseline heuristic and the GA success target (set the number after the baseline exists). **Proposed target, not decided** (from the exact-optimum measurement, `backend/scripts/ga_quality.py`): with the default settings, (a) the GA finds the exact optimum in at least 95% of runs on 8- to 12-task instances of every shape (measured: 99.8%, 808 of 810 runs), and (b) on 50-task chains its mean gap to the exact optimum is at most 0.5 stations (measured: 0.38 before greedy seeding, 0.18 after, on a fresh set; `docs/GA_DESIGN.md` section 9). The margin covers seed noise. Automatic check: (a) a pytest test runs the GA with a fixed seed on 30 fixed 12-task instances (10 per shape) and compares with `solve_exact`, about 10 s; (b) is too slow for every test run (about 1 minute), so `ga_quality.py` checks it before each release. The baseline part stays open |
| Straight-line baseline | IE formulas document section 10 asks to also compare against a straight-line baseline. Add it (needs a contract change), or keep only the U-line baseline? |
| D9 | What exactly does the ML module predict or recommend? |
| D10 | ML training data: how it is generated and how much |
| D13 to D18 | Repository rules, sprint rhythm, contract freeze date, cut list, benchmark instances, ownership: proposed in the PDF and in CONTRIBUTING.md and MASTER.md |
