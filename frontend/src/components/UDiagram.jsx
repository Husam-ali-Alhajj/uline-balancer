// TODO FE-F5: replace this list with the real U-shaped SVG diagram.
// Data: solution.stations[].tasks[] with side "front" (entry leg) or "back" (exit leg).
export default function UDiagram({ solution, cycleTime }) {
  return (
    <section className="rounded border bg-white p-4">
      <h2 className="mb-2 font-semibold">Stations (placeholder for the U diagram)</h2>
      <ul className="space-y-1 text-sm">
        {solution.stations.map((s) => (
          <li key={s.index}>
            Station {s.index}: {s.tasks.map((t) => `${t.name} (${t.side})`).join(", ")} - load{" "}
            {s.load} of {cycleTime} min
          </li>
        ))}
      </ul>
    </section>
  );
}
