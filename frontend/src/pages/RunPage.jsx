import { useParams } from "react-router-dom";
import { useRun } from "../hooks/useRun.js";
import MetricCards from "../components/MetricCards.jsx";
import UDiagram from "../components/UDiagram.jsx";
import ConvergenceChart from "../components/ConvergenceChart.jsx";
import Recommendations from "../components/Recommendations.jsx";

export default function RunPage() {
  const { runId } = useParams();
  const { data: run, isPending, isError, error } = useRun(runId);

  if (isPending) return <p>Loading...</p>;
  if (isError) return <p className="text-red-700">{error.message}</p>;

  if (run.status === "failed") {
    return <p className="text-red-700">The run failed: {run.error?.message}</p>;
  }
  if (run.status !== "succeeded") {
    const p = run.progress;
    return (
      <p>
        Run {run.status}
        {p ? ` (generation ${p.generation} of ${p.max_generations})` : ""}...
      </p>
    );
  }

  const { result } = run;
  return (
    <main className="space-y-6">
      <h1 className="text-2xl font-semibold">{run.title ?? "Result"}</h1>
      <MetricCards instance={result.instance} metrics={result.metrics} solution={result.solution} />
      <UDiagram solution={result.solution} cycleTime={result.instance.cycle_time} />
      <ConvergenceChart convergence={result.ga.convergence} />
      <Recommendations items={result.recommendations} />
    </main>
  );
}
