import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { createRun } from "../api/runs.js";
import exampleInput from "../../../contracts/examples/six_task_input.json";

// TODO FE-F1..F3: the real input form (task table, working time, production, live cycle time).
export default function InputPage() {
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: createRun,
    onSuccess: ({ run_id }) => navigate(`/runs/${run_id}`),
  });

  return (
    <main className="space-y-4">
      <h1 className="text-2xl font-semibold">New balancing run</h1>
      <p className="text-slate-600">The task input form is not built yet (ticket FE-F1).</p>

      {/* FE-F8: the quick demo path - load the example and run in one click */}
      <button
        className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(exampleInput)}
      >
        {mutation.isPending ? "Starting..." : "Load example and run"}
      </button>

      {mutation.isError && (
        <p className="text-red-700">{mutation.error.message}</p>
      )}
    </main>
  );
}
