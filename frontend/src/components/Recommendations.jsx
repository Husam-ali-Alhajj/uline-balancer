// TODO FE-F7: polish. Each item: { code, severity, station, message, triggered_by }.
export default function Recommendations({ items }) {
  return (
    <section className="rounded border bg-white p-4">
      <h2 className="mb-2 font-semibold">Recommendations</h2>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No recommendations.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {items.map((r) => (
            <li key={`${r.code}-${r.station ?? "all"}`}>
              <span className={r.severity === "warning" ? "text-amber-700" : "text-slate-700"}>
                {r.message}
              </span>
              <span className="block text-xs text-slate-400">{r.triggered_by}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
