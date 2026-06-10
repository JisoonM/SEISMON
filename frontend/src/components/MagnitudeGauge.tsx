import type { EarthquakeSummary } from "@/types/earthquake";
import { formatMagnitude } from "@/lib/utils";

interface MagnitudeGaugeProps {
  summary: EarthquakeSummary | null;
}

export function MagnitudeGauge({ summary }: MagnitudeGaugeProps) {
  const magnitude = summary?.max_magnitude_today ?? 0;
  const width = Math.min(100, (magnitude / 8) * 100);

  return (
    <div className="min-h-[180px] rounded-md border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Magnitude Gauge</h2>
        <span className="text-xs text-muted">24h peak</span>
      </div>
      <div className="mt-8">
        <div className="flex items-end justify-between">
          <span className="text-4xl font-semibold">{formatMagnitude(summary?.max_magnitude_today)}</span>
          <span className="text-sm text-muted">{summary?.most_affected_province ?? "No province focus"}</span>
        </div>
        <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-800">
          <div className="h-full rounded-full bg-gradient-to-r from-emerald-300 via-yellow-300 to-red-400" style={{ width: `${width}%` }} />
        </div>
        <div className="mt-2 flex justify-between text-[11px] text-muted">
          <span>M0</span>
          <span>M4</span>
          <span>M8</span>
        </div>
      </div>
    </div>
  );
}
