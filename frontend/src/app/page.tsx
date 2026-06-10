import { AlertBanner } from "@/components/AlertBanner";
import { LiveEventFeed } from "@/components/LiveEventFeed";
import { MagnitudeGauge } from "@/components/MagnitudeGauge";
import { SeismicMap } from "@/components/SeismicMap";
import { SeismographPanel } from "@/components/SeismographPanel";
import { StatCards } from "@/components/StatCards";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-background px-6 py-5 text-slate-100">
      <header className="mb-6 flex items-center justify-between border-b border-border pb-4">
        <h1 className="text-lg font-semibold tracking-wide">PH SEISMIC MONITOR</h1>
        <span className="text-sm text-muted">Phase 1 scaffold</span>
      </header>
      <div className="grid grid-cols-12 gap-4">
        <section className="col-span-12">
          <AlertBanner />
        </section>
        <section className="col-span-12">
          <StatCards />
        </section>
        <section className="col-span-12 lg:col-span-8">
          <SeismicMap />
        </section>
        <section className="col-span-12 lg:col-span-4">
          <LiveEventFeed />
        </section>
        <section className="col-span-12 lg:col-span-6">
          <SeismographPanel />
        </section>
        <section className="col-span-12 lg:col-span-6">
          <MagnitudeGauge />
        </section>
      </div>
    </main>
  );
}

