const labels = ["Events Today", "Strongest Today", "Active Alerts", "Last Event"];

export function StatCards() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
      {labels.map((label) => (
        <article key={label} className="rounded border border-border bg-surface p-4">
          <p className="text-xs uppercase text-muted">{label}</p>
          <p className="mt-2 text-2xl font-semibold">--</p>
        </article>
      ))}
    </div>
  );
}

