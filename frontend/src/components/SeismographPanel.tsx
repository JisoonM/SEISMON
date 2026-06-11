import type { Earthquake } from "@/types/earthquake";

interface SeismographPanelProps {
  latestEvent: Earthquake | null;
}

export function SeismographPanel({ latestEvent }: SeismographPanelProps) {
  const amplitude = latestEvent ? Math.min(88, Math.max(18, latestEvent.magnitude * 12)) : 24;
  const waveform = Array.from({ length: 42 }, (_, index) => ({
    height: Math.round(10 + Math.abs(Math.sin(index * 0.8)) * amplitude),
    key: `wave-${index}`
  }));

  return (
    <div className="min-h-[180px] rounded-md border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Seismograph</h2>
        <span className="text-xs text-muted">{latestEvent ? latestEvent.event_id : "standby"}</span>
      </div>
      <div className="mt-6 h-24 overflow-hidden rounded-md border border-slate-700 bg-slate-950">
        <div className="flex h-full items-center gap-1 px-2">
          {waveform.map((bar) => (
            <span
              key={bar.key}
              className="w-1 rounded-full bg-cyan-300/70"
              style={{
                height: `${bar.height}px`
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
