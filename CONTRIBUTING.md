# Contributing

Short version: work on a branch, open a pull request into `develop`, get it reviewed, merge.
Read `MASTER.md` first and `AI_RULES.md` if you use any AI tool.

## Branches

| Branch | Purpose | Who writes to it |
|---|---|---|
| `main` | stable releases, tagged at the end of each sprint (`sprint-1`, `sprint-2`, ...) | project lead only, by merging `develop` |
| `develop` | integration branch; always runs and passes tests; **default branch** | via pull requests only |
| `feature/<track>-<name>` | one task, e.g. `feature/frontend-input-form` | the person doing the task |
| `fix/<name>` | a bug fix | the person fixing it |

Starter branches already created from `develop`: `feature/frontend-skeleton`, `feature/ml-recommender`,
`feature/ga-core`. Delete a branch after its pull request is merged.

## Daily workflow

```bash
git clone <repo-url> && cd uline-balancer
git checkout develop && git pull
git checkout -b feature/frontend-input-form      # new branch from develop

# ... work, then check your work (see below) ...
git add <files you changed>
git commit -m "Add task input table"
git push -u origin feature/frontend-input-form
# open a pull request into develop on GitHub
```

Keep your branch up to date: `git checkout develop && git pull && git checkout <your-branch> && git merge develop`.
If you get a merge conflict and are unsure, ask the project lead before resolving it.

## Check your work before a pull request

- Backend: `cd backend && ruff check . && pytest`
- Frontend: `cd frontend && npm run build`, then click through your change in the browser (desktop width).

## Pull requests

- One task per pull request, small enough to review in 15 minutes.
- Target `develop`. Fill in the template. CI must be green.
- The project lead reviews and merges (squash merge). Aim for review within one day.
- Never push straight to `develop` or `main`.

## Definition of Done (every task)

- [ ] Meets the acceptance criteria of the ticket
- [ ] Tests written or updated (backend logic); `ruff check .` and `pytest` pass
- [ ] Frontend: `npm run build` passes and the change was tried in the browser
- [ ] No secrets, no `.env`, no generated files committed
- [ ] Docs updated if behaviour or setup changed (README or MASTER.md, via the project lead)
- [ ] Pull request opened, template filled in, reviewed and merged

## Tickets

Use `docs/TICKET_TEMPLATE.md`. A good ticket has: goal, files you may change, inputs and outputs, and a checklist of
done-criteria. If a ticket is unclear, ask before starting.

## One-time GitHub setup (project lead)

1. Push all branches. In Settings > General set the default branch to `develop`.
2. Settings > Branches: add protection rules for `main` and `develop`: require a pull request, require the
   `backend` status check to pass, block force pushes.
3. Settings > General: allow squash merging, enable "Automatically delete head branches".
4. Add the team as collaborators. Never share the Supabase key in chat or in the repo; share it privately.
