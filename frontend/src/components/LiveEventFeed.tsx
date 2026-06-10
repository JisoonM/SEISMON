import type { Earthquake } from "@/types/earthquake";
import { formatDepth, formatMagnitude, formatPhtDateTime } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboardStore";

interface LiveEventFeedProps {
  events: Earthquake[];
}

const levelClasses: Record<string, string> = {
  green: "bg-emerald-400",
  yellow: "bg-yellow-300",
  orange: "bg-orange-400",
  red: "bg-red-400"
};

export function LiveEventFeed({ events }: LiveEventFeedProps) {
  const focusEvent = useDashboardStore((state) => state.focusEvent);

  return (
    <div className="min-h-[500px] rounded-md border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Live Event Feed</h2>
        <span className="text-xs text-muted">{events.length} tracked</span>
      </div>
      <div className="mt-4 space-y-3">
        {events.length === 0 ? (
          <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted">Waiting for seismic events</div>
        ) : (
          events.slice(0, 8).map((event) => (
            <button
              key={event.id}
              type="button"
              onClick={() => focusEvent(event)}
              className="w-full rounded-md border border-border bg-slate-950/45 p-3 text-left transition hover:border-cyan-300/60"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold text-slate-50">{formatMagnitude(event.magnitude)}</span>
                <span className="text-xs text-muted">{formatPhtDateTime(event.occurred_at)} PHT</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${levelClasses[event.alert_level]}`} />
                <p className="truncate text-sm text-slate-300">{event.place}</p>
              </div>
              <p className="mt-1 text-xs text-muted">
                {formatDepth(event.depth_km)} - {event.source}
              </p>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
