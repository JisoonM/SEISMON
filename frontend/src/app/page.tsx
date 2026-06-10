"use client";

import { Clock3, Radio, Wifi, WifiOff } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AlertBanner } from "@/components/AlertBanner";
import { LiveEventFeed } from "@/components/LiveEventFeed";
import { MagnitudeGauge } from "@/components/MagnitudeGauge";
import { SeismicMap } from "@/components/SeismicMap";
import { SeismographPanel } from "@/components/SeismographPanel";
import { StatCards } from "@/components/StatCards";
import { useEarthquakeData } from "@/hooks/useEarthquakeData";
import { useEarthquakeSocket } from "@/hooks/useEarthquakeSocket";
import { formatPhtTime } from "@/lib/utils";
import { useDashboardStore } from "@/store/dashboardStore";

export default function DashboardPage() {
  const { earthquakes, summary, isLoading, error } = useEarthquakeData();
  const { isConnected, events: socketEvents, lastEvent, connectionError } = useEarthquakeSocket();
  const [now, setNow] = useState(new Date());
  const historicalMode = useDashboardStore((state) => state.historicalMode);
  const setHistoricalMode = useDashboardStore((state) => state.setHistoricalMode);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const events = useMemo(() => {
    const byId = new Map(earthquakes.items.map((event) => [event.id, event]));
    socketEvents.forEach((event) => byId.set(event.id, event));
    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime()
    );
  }, [earthquakes.items, socketEvents]);

  const latestEvent = lastEvent ?? events[0] ?? null;

  return (
    <main className="min-h-screen bg-background px-4 py-4 text-slate-100 sm:px-6">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4" role="banner">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-md border border-cyan-300/30 bg-cyan-300/10">
            <Radio aria-hidden className="h-5 w-5 text-cyan-200" />
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-wide">SEISMON</h1>
            <p className="text-xs text-muted">Philippines seismic operations</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-surface px-3">
            <Clock3 aria-hidden className="h-4 w-4 text-cyan-300" />
            <span>{formatPhtTime(now)}</span>
            <span className="text-xs text-muted">PHT</span>
          </span>
          <span className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-surface px-3">
            {isConnected ? <Wifi aria-hidden className="h-4 w-4 text-emerald-300" /> : <WifiOff aria-hidden className="h-4 w-4 text-red-300" />}
            <span>{isConnected ? "Live" : "Offline"}</span>
          </span>
          <label className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-surface px-3 text-xs text-muted">
            <input
              type="checkbox"
              checked={historicalMode}
              onChange={(event) => setHistoricalMode(event.target.checked)}
              className="accent-cyan-300"
            />
            Historical
          </label>
        </div>
      </header>

      {(error || connectionError) && (
        <div className="mb-4 rounded-md border border-yellow-300/25 bg-yellow-950/20 px-4 py-3 text-sm text-yellow-100">
          {error ?? connectionError}
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        <section className="col-span-12">
          <AlertBanner event={latestEvent} />
        </section>
        <section className="col-span-12">
          <StatCards summary={summary} latestEvent={latestEvent} isLoading={isLoading} />
        </section>
        <section className="col-span-12 lg:col-span-8">
          <SeismicMap events={events} />
        </section>
        <section className="col-span-12 lg:col-span-4">
          <LiveEventFeed events={events} />
        </section>
        <section className="col-span-12 lg:col-span-6">
          <SeismographPanel latestEvent={latestEvent} />
        </section>
        <section className="col-span-12 lg:col-span-6">
          <MagnitudeGauge summary={summary} />
        </section>
      </div>
    </main>
  );
}
