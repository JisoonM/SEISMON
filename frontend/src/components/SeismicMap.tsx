import { Crosshair, MapPinned } from "lucide-react";

import { formatDepth, formatMagnitude } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboardStore";
import type { Earthquake } from "@/types/earthquake";

interface SeismicMapProps {
  events: Earthquake[];
}

export function SeismicMap({ events }: SeismicMapProps) {
  const selectedEvent = useDashboardStore((state) => state.selectedEvent);
  const minMagnitude = useDashboardStore((state) => state.filters.minMagnitude);
  const setMinMagnitude = useDashboardStore((state) => state.setMinMagnitude);

  return (
    <div className="min-h-[500px] rounded-md border border-border bg-surface p-4 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <MapPinned aria-hidden className="h-4 w-4 text-cyan-300" />
          <h2 className="text-sm font-semibold">Operations map</h2>
        </div>
        <label className="flex items-center gap-2 text-xs text-muted">
          M{minMagnitude.toFixed(1)}+
          <input
            aria-label="Minimum magnitude"
            type="range"
            min="0"
            max="7"
            step="0.5"
            value={minMagnitude}
            onChange={(event) => setMinMagnitude(Number(event.target.value))}
            className="h-1 w-28 accent-cyan-300"
          />
        </label>
      </div>
      <div className="mt-4 grid min-h-[400px] place-items-center rounded-md border border-slate-700/70 bg-[radial-gradient(circle_at_50%_35%,rgba(14,165,233,0.16),rgba(15,23,42,0.9)_55%)]">
        <div className="text-center">
          <Crosshair aria-hidden className="mx-auto h-10 w-10 text-cyan-200" />
          <p className="mt-3 text-sm font-medium text-slate-100">{events.length} events in current feed</p>
          <p className="mt-1 text-xs text-muted">
            {selectedEvent
              ? `${formatMagnitude(selectedEvent.magnitude)} - ${selectedEvent.province ?? selectedEvent.place} - ${formatDepth(selectedEvent.depth_km)}`
              : "Mapbox layer activates in Phase 7"}
          </p>
        </div>
      </div>
    </div>
  );
}
