import { Link, Route, Routes } from "react-router-dom";
import InputPage from "./pages/InputPage.jsx";
import RunPage from "./pages/RunPage.jsx";

export default function App() {
  return (
    <div className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-baseline justify-between">
        <Link to="/" className="text-xl font-semibold">
          U-Line Balancer
        </Link>
        <span className="text-sm text-slate-500">
          {import.meta.env.VITE_USE_MOCKS === "true" ? "mock API" : "live API"}
        </span>
      </header>
      <Routes>
        <Route path="/" element={<InputPage />} />
        <Route path="/runs/:runId" element={<RunPage />} />
      </Routes>
    </div>
  );
}
