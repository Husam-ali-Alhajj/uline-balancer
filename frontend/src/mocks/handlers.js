// Mock API (MSW). Same endpoints and shapes as the real backend, built from
// contracts/examples so the frontend can be developed without the backend.
// A run goes queued -> running -> succeeded over successive polls.
import { http, HttpResponse } from "msw";
import exampleInput from "../../../contracts/examples/six_task_input.json";
import exampleResult from "../../../contracts/examples/six_task_result.json";

const runs = new Map(); // run_id -> { title, createdAt, polls }

function errorResponse(status, code, message, details = []) {
  return HttpResponse.json({ error: { code, message, details } }, { status });
}

function summarize(problem) {
  const total = problem.tasks.reduce((sum, t) => sum + t.time, 0);
  const cycle = problem.working_time_per_day / problem.production_per_day;
  return {
    task_count: problem.tasks.length,
    total_work_content: total,
    cycle_time: cycle,
    min_stations: Math.max(1, Math.ceil(total / cycle - 1e-9)),
  };
}

function checkMinimal(problem) {
  if (!problem?.tasks?.length) {
    return errorResponse(422, "validation_error", "The input is not valid.", [
      { field: "tasks", message: "at least one task is required" },
    ]);
  }
  return null;
}

export const handlers = [
  http.get("*/health", () => HttpResponse.json({ status: "ok" })),

  http.post("*/validate", async ({ request }) => {
    const problem = await request.json();
    return checkMinimal(problem) ?? HttpResponse.json({ valid: true, instance: summarize(problem) });
  }),

  http.post("*/runs", async ({ request }) => {
    const problem = await request.json();
    const bad = checkMinimal(problem);
    if (bad) return bad;
    const runId = crypto.randomUUID();
    runs.set(runId, { title: problem.title ?? null, createdAt: new Date().toISOString(), polls: 0 });
    return HttpResponse.json({ run_id: runId, status: "queued" }, { status: 202 });
  }),

  http.get("*/runs", () =>
    HttpResponse.json(
      [...runs.entries()].map(([runId, run]) => ({
        run_id: runId,
        title: run.title,
        status: "succeeded",
        created_at: run.createdAt,
        task_count: exampleInput.tasks.length,
        num_stations: exampleResult.solution.num_stations,
        efficiency: exampleResult.metrics.efficiency,
      })),
    ),
  ),

  http.get("*/runs/:runId", ({ params }) => {
    const run = runs.get(params.runId);
    if (!run) return errorResponse(404, "not_found", "Run not found.");
    run.polls += 1;
    const base = {
      run_id: params.runId,
      title: run.title,
      created_at: run.createdAt,
      started_at: null,
      finished_at: null,
      progress: null,
      error: null,
      result: null,
    };
    if (run.polls === 1) return HttpResponse.json({ ...base, status: "queued" });
    if (run.polls === 2) {
      return HttpResponse.json({
        ...base,
        status: "running",
        started_at: run.createdAt,
        progress: { generation: 40, max_generations: 100 },
      });
    }
    return HttpResponse.json({
      ...base,
      status: "succeeded",
      started_at: run.createdAt,
      finished_at: new Date().toISOString(),
      progress: { generation: 100, max_generations: 100 },
      result: exampleResult,
    });
  }),

  http.delete("*/runs/:runId", ({ params }) => {
    if (!runs.delete(params.runId)) return errorResponse(404, "not_found", "Run not found.");
    return new HttpResponse(null, { status: 204 });
  }),
];
