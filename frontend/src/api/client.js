// The ONLY place that calls fetch. Everything else goes through src/api/runs.js.
// The frontend never talks to Supabase directly (see MASTER.md).
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, code, message, details = []) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details; // [{ field, message }]
  }
}

export async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    throw new ApiError(res.status, e?.code ?? "unknown_error", e?.message ?? res.statusText, e?.details ?? []);
  }
  return body;
}
