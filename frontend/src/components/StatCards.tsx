import { Activity, Bell, MapPin, RadioTower } from "lucide-react";

import { formatMagnitude } from "@/lib/utils";
import type { Earthquake, EarthquakeSummary } from "@/types/earthquake";

interface StatCardsProps {
  summary: EarthquakeSummary | null;
  latestEvent: Earthquake | null;
  isLoading: boolean;
}

export function StatCards({ summary, latestEvent, isLoading }: StatCardsProps) {
  const redCount = summary?.counts_by_alert_level.red ?? 0;
  const cards = [
    {
      label: "Events Today",
      value: isLoading ? "--" : String(summary?.total_today ?? 0),
      detail: `${summary?.total_this_week ?? 0} this week`,
      icon: Activity
    },
    {
      label: "Strongest Today",
      value: isLoading ? "--" : formatMagnitude(summary?.max_magnitude_today),
      detail: summary?.avg_depth_today ? `${summary.avg_depth_today.toFixed(1)} km avg depth` : "No peak yet",
      icon: RadioTower
    },
    {
      label: "Active Alerts",
      value: isLoading ? "--" : `${redCount} red`,
      detail: `${summary?.counts_by_alert_level.orange ?? 0} orange`,
      icon: Bell
    },
    {
      label: "Last Event",
      value: isLoading ? "--" : latestEvent?.province ?? "--",
      detail: latestEvent ? `${formatMagnitude(latestEvent.magnitude)} - ${latestEvent.source}` : summary?.most_affected_province ?? "No events",
      icon: MapPin
    }
  ];

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
      {cards.map(({ label, value, detail, icon: Icon }) => (
        <article key={label} className="rounded-md border border-border bg-surface p-4 shadow-panel">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase text-muted">{label}</p>
            <Icon aria-hidden className="h-4 w-4 text-cyan-300" />
          </div>
          <p className="mt-3 text-2xl font-semibold text-slate-50">{value}</p>
          <p className="mt-1 truncate text-xs text-muted">{detail}</p>
        </article>
      ))}
    </div>
  );
}
