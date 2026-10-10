# Contributing

Short version: teammates work on their own long-lived branch; the project lead reviews and merges everything into
`develop`. Read `MASTER.md` first and `AI_RULES.md` if you use any AI tool.

## Branches

| Branch | Purpose | Who writes to it |
|---|---|---|
| `main` | stable releases, tagged at the end of each sprint (`sprint-1`, `sprint-2`, ...) | project lead only, by merging `develop` |
| `develop` | integration branch; **default branch on GitHub** | the project lead only |
| `Frontend` | long-lived branch for the frontend engineer | the frontend engineer only |
| `AI` | long-lived branch for the AI engineer | the AI engineer only |
| `feature/<name>` | the project lead's own task branches, e.g. `feature/ga-core` | the project lead only |

Teammates work only on their own branch, and only in their own folders (see MASTER.md section 2). They never create,
switch, delete, merge or rebase branches — if you're unsure which branch you're on, or git shows a conflict or
anything unclear, stop and ask the project lead instead of resolving it yourself. The project lead does all merging.

## Integration routine (project lead)

At least once a week, and whenever a ticket is done:

1. Check the branch: tests pass, the diff is clean. A pull request from the track branch into `develop`, opened by
   the project lead, is the preferred way to review it and run CI.
2. Merge it into `develop`.
3. Merge `develop` back into the track branch, so the teammate gets the latest contracts and code.
4. Tell the teammate to press "Sync Changes".

A track branch must never go more than 7 days without this routine. Merge conflicts are resolved by the project
lead only.

## Check your work before an integration

- Backend: `cd backend && ruff check . && pytest`
- Frontend: `cd frontend && npm run build`, then click through your change in the browser (desktop width).

## Definition of Done (every task)

- [ ] Meets the acceptance criteria of the ticket
- [ ] Tests written or updated (backend logic); `ruff check .` and `pytest` pass
- [ ] Frontend: `npm run build` passes and the change was tried in the browser
- [ ] No secrets, no `.env`, no generated files committed
- [ ] Docs updated if behaviour or setup changed (README or MASTER.md, via the project lead)
- [ ] Integration: a pull request was opened into `develop`, the template filled in, reviewed and merged by the
  project lead

## Tickets

Use `docs/TICKET_TEMPLATE.md`. A good ticket has: goal, files you may change, inputs and outputs, and a checklist of
done-criteria. If a ticket is unclear, ask before starting.

## One-time GitHub setup (project lead)

1. Push all branches. In Settings > General set the default branch to `develop`.
2. Settings > Branches: add protection rules for `main` and `develop` only: require a pull request, require the
   `backend` status check to pass, block force pushes. Do not add protection rules for `Frontend` or `AI`.
3. Settings > General: allow squash merging, enable "Automatically delete head branches".
4. Add the team as collaborators. Never share the Supabase key in chat or in the repo; share it privately.
