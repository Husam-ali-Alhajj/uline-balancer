import { useQuery } from "@tanstack/react-query";
import { getRun } from "../api/runs.js";

const DONE = ["succeeded", "failed"];

// Polls GET /runs/{id} every 1.5 s until the run is finished (start-and-poll design).
export function useRun(runId) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    refetchInterval: (query) => (DONE.includes(query.state.data?.status) ? false : 1500),
  });
}
