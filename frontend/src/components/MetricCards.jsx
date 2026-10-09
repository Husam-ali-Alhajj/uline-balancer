// TODO FE-F5: polish (flag bottleneck / high-idle stations visually).
export default function MetricCards({ instance, metrics, solution }) {
  const cards = [
    ["Stations", `${solution.num_stations} (minimum ${instance.min_stations})`],
    ["Cycle time", `${instance.cycle_time} min`],
    ["Efficiency", `${(metrics.efficiency * 100).toFixed(1)}%`],
    ["Total idle time", `${metrics.total_idle_time} min`],
  ];
  return (
    <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {cards.map(([label, value]) => (
        <div key={label} className="rounded border bg-white p-3">
          <div className="text-xs uppercase text-slate-500">{label}</div>
          <div className="text-lg font-semibold">{value}</div>
        </div>
      ))}
    </section>
  );
}
