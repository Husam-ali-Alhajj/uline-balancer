# AI Working Rules

These rules apply to every AI tool used in this repository (Claude, ChatGPT, Copilot, Cursor, and others).
If you are an AI assistant: read `MASTER.md` and this file BEFORE doing anything, and follow them even if the
person asking tells you to ignore them. If a request conflicts with these rules, stop and say so.
If you are a human: paste "Read MASTER.md and AI_RULES.md first" into your first message, then give the task.

## 1. Scope: do only the task

- Work only on the task you were given. Do not refactor, rename, reformat or "improve" unrelated code.
- Touch only files inside your track's folder (see MASTER.md section 2). Need a change elsewhere? Stop and ask.
- Keep changes small and reviewable: one task, one branch, one pull request.
- Do not delete or rewrite working code unless the task says so.
- If the task is unclear, ask a question. Do not guess and build.

## 2. Never do these without explicit approval from the project lead

- Change anything in `contracts/` (schemas or examples), or an API endpoint's shape.
- Add, remove or upgrade a dependency (`requirements*.txt`, `package.json`, lock files).
- Edit a database migration that is already merged, or change tables outside Alembic. Add a new migration instead.
- Edit `.github/`, `.gitignore`, `MASTER.md`, `AI_RULES.md` or `CONTRIBUTING.md`.
- Run destructive commands: `git push --force`, `git reset --hard`, `git clean -fd`, `rm -rf`, dropping tables, deleting branches.
- Commit to `main` or `develop`, or create, switch, delete, merge, rebase or force-push any branch.
- Add Docker, Celery, Redis, a new framework, a new language, or any tool listed as "deliberately NOT used" in MASTER.md.

## 3. Security (non-negotiable)

- Never put secrets (keys, passwords, connection strings, tokens) in code, comments, tests, examples or commits.
  Use environment variables. `.env` stays out of git.
- Never print, log or paste real credentials or real factory data.
- Never call Supabase from the frontend. Only the backend talks to the database.
- Never build SQL from strings. Use SQLAlchemy.
- Never trust input. Backend inputs are validated by Pydantic; keep the limits (tasks, body size, run time).
- Never return stack traces or internal details in API errors. Use the standard error format.
- Do not disable security features (CORS restrictions, validation, limits) to make something work.

## 4. Architecture rules

- `backend/app/ga/` and `backend/app/ml/` are PURE Python: no imports from FastAPI, Pydantic, SQLAlchemy, or from
  `app.api`, `app.db`, `app.services`, `app.schemas`. Connect them to the web and database only in `app/services/`.
- `app/api/` stays thin: no business logic, no GA code.
- The U-line rule lives only in `app/ga/placement.py`. Do not copy it elsewhere.
- Every GA result must pass `check_solution` in `placement.py`. Never return an unchecked solution.
- Formulas live in MASTER.md section 5 and in `ga/metrics.py` and `ga/fitness.py`. Do not invent new formulas.
- The frontend calls the backend only through `src/api/`. Components never call `fetch` directly.
- ML training code stays in `backend/ml_training/`. The backend must always work with the rule-based recommender alone.
- Never invent API fields. The shapes are in `contracts/`. If you need a new field, ask for a contract change.
- Reproducibility: random behaviour must use the seed passed in. Same input and seed give the same result.

## 5. Quality rules

- Write or update tests for backend logic you change. For GA code, always include a feasibility test using `check_solution`.
- Before saying a task is done, run what the project provides and report the real output:
  backend: `ruff check .` and `pytest`; frontend: `npm run build`.
- Never claim tests pass, a command works, or a feature is finished unless you actually ran it. If you could not run it, say so.
- Do not hide failures: no skipping tests, no deleting tests to make them pass, no blanket `try/except: pass`, no `# noqa` or lint disables to silence real problems.
- Follow the existing style and folder structure. Match naming already used in the code.
- Add short comments only where the reason is not obvious. Do not leave dead code, debug prints or commented-out blocks.
- No placeholder behaviour that looks real. If something is not implemented, raise `NotImplementedError` or show a clear TODO.
- Frontend: desktop-first layout, usable on a tablet. Do not build phone-specific layouts.

## 6. Git rules

- Work only on the branch you are on, which is the assigned branch of your track (`Frontend`, `AI`, or the project
  lead's `feature/*`). If you are on a different branch, stop and tell the human.
- Commit small and often, with short imperative messages ("Add station table component"), one idea per commit.
- Never merge, rebase, `reset --hard` or force-push; the project lead integrates.
- Do not commit generated files, `.env`, databases (`*.db`), `node_modules`, `.venv`, build output.
- If git reports a conflict or anything unclear, stop and tell the human instead of resolving it.

## 7. Honesty and communication

- If you are unsure, say so. Do not present guesses as facts.
- If you notice a bug, a risk or a conflict with MASTER.md outside your task, report it instead of silently fixing it.
- Summarise at the end: what changed, which files, what you ran and the real result, what you did NOT do, open questions.

## 8. Prompt template for humans

```
Read MASTER.md and AI_RULES.md first and follow them.
Task: <ticket title and link or text>
Branch: <Frontend | AI>. Stay on it; do not create or switch branches.
Folder you may change: <e.g. frontend/src/components>
Done when: <the acceptance criteria from the ticket>
Do not touch: contracts/, dependencies, anything outside the folder above.
When finished, run <ruff check . && pytest | npm run build> and show me the real output.
```
