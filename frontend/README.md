# Frontend

React 18 + Vite, TanStack Query (polling), Tailwind CSS, Recharts, MSW (mock API).
Language: plain JavaScript (JSX). Read `../MASTER.md` first.

## Run it locally

```bash
cd frontend
cp .env.example .env        # Windows: copy .env.example .env
npm install                 # also creates public/mockServiceWorker.js (postinstall)
npm run dev                 # http://localhost:5173
```

With `VITE_USE_MOCKS=true` (default) the app runs against the mock API, no backend needed.
Set it to `false` to use the real backend at `VITE_API_URL`.

If `public/mockServiceWorker.js` is missing after install, run `npx msw init public/ --save`.

## Check your work (before every pull request)

```bash
npm run build
```
Then click through the pages in the browser. Layout target: desktop, usable on a tablet.

## Layout

| Path | Purpose |
|---|---|
| `src/api/` | the only place that calls the backend (`client.js`, `runs.js`) |
| `src/mocks/` | MSW handlers built from `../contracts/examples` |
| `src/hooks/` | data hooks (`useRun` polls until the run is finished) |
| `src/pages/` | one file per screen |
| `src/components/` | reusable pieces (diagram, charts, cards) |

The API shapes are defined in `../contracts/` (JSON schemas and examples). Do not invent fields.
