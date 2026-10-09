// API functions. Shapes are defined in ../../../contracts (JSON schemas + examples).
import { request } from "./client.js";

export const validateProblem = (problem) =>
  request("/validate", { method: "POST", body: JSON.stringify(problem) });

export const createRun = (problem) =>
  request("/runs", { method: "POST", body: JSON.stringify(problem) }); // -> { run_id, status }

export const getRun = (runId) => request(`/runs/${runId}`); // -> RunStatus

export const listRuns = () => request("/runs");

export const deleteRun = (runId) => request(`/runs/${runId}`, { method: "DELETE" });
