# Team guide (VS Code, no git experience needed)

A one-page guide for teammates who are new to git. Everything here is done through VS Code, not the command line.

## First time (do this once)

1. Install Git, VS Code, Python 3.12 and Node.
2. Clone the repo: open VS Code, go to the Source Control panel (left sidebar) and click "Clone Repository" (or
   press `Ctrl+Shift+P` and run "Git: Clone"), then paste the repo URL.
3. Open the cloned folder in VS Code.
4. Switch to your branch: click the branch name in the bottom-left corner of the window and pick `Frontend` or `AI`
   (whichever is yours).
5. Follow the quick start in `README.md` to get the app running.

Stay on your branch forever. You should never need to switch again.

## Every working session

1. Open VS Code and click **Sync Changes** (the arrows in the bottom status bar) to get the project lead's latest
   updates.
2. Work only in your own folders (`frontend/` for Frontend, `backend/app/ml/` and `backend/ml_training/` for AI).
3. Run the checks before you commit:
   - Backend: `ruff check .` and `pytest`
   - Frontend: `npm run build`
4. In the Source Control panel: review the list of changed files, type a short message describing what you did,
   and click **Commit**.
5. Click **Sync Changes** again to upload your commit.

Do step 5 at the end of every session, so your work is never only on your own machine.

## Using AI tools

- Start every session by telling the AI: "Read MASTER.md and AI_RULES.md first, I am on branch `<name>`."
- Always read what the AI changed before you commit it.

## Never do this

- Switch or create branches
- Merge or rebase
- Click "Force Push"
- Click "Reset" (on a commit, a branch, or anything else)
- Delete files you did not create
- Commit `.env` files
- Share keys in chat

## If something goes wrong

A conflict message, a red error, or just feeling unsure: **stop**. Do not try to fix git yourself. Send the project
lead a screenshot. Nothing is lost — your work is saved in your commits.

## When the project lead says "sync"

Click **Sync Changes**.
