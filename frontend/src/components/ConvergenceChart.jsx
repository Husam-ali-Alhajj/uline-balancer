import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Working example of the chart pattern. TODO FE-F6: add the other charts
// (workload vs cycle time, idle time per station, worker workload).
export default function ConvergenceChart({ convergence }) {
  return (
    <section className="rounded border bg-white p-4">
      <h2 className="mb-2 font-semibold">GA convergence (lower is better)</h2>
      <div style={{ width: "100%", height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={convergence}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="generation" />
            <YAxis domain={["auto", "auto"]} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="best_fitness" name="Best" dot={false} />
            <Line type="monotone" dataKey="avg_fitness" name="Average" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
