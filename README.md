# U-Line Balancer

Web app that balances U-shaped assembly lines with a Genetic Algorithm (ILE 401 capstone).

**Start here:** read [`MASTER.md`](MASTER.md). Using an AI tool? Also read [`AI_RULES.md`](AI_RULES.md).
Workflow and branches: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick start

```bash
# terminal 1: backend  (details in backend/README.md)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # Windows: copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload                          # http://localhost:8000/docs

# terminal 2: frontend  (details in frontend/README.md)
cd frontend
cp .env.example .env                                   # Windows: copy .env.example .env
npm install
npm run dev                                            # http://localhost:5173
```

The frontend starts in mock mode (no backend needed). Set `VITE_USE_MOCKS=false` in `frontend/.env` to use the backend.

## Folders

`backend/` API, GA, ML, database | `frontend/` React app | `contracts/` JSON schemas and examples |
`docs/` requirements, decisions, ticket template
