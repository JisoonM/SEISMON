import { AlertTriangle, ShieldCheck } from "lucide-react";

import { formatDepth, formatMagnitude, formatPhtDateTime } from "@/lib/utils";
import type { Earthquake } from "@/types/earthquake";

interface AlertBannerProps {
  event: Earthquake | null;
}

export function AlertBanner({ event }: AlertBannerProps) {
  const significant = event && event.magnitude >= 5;

  if (!significant) {
    return (
      <div className="flex min-h-16 items-center gap-3 rounded-md border border-emerald-400/20 bg-emerald-950/25 px-4 py-3 text-sm text-emerald-100">
        <ShieldCheck aria-hidden className="h-5 w-5 text-emerald-300" />
        <div>
          <p className="font-medium">No significant active alert</p>
          <p className="text-xs text-emerald-200/70">Monitoring live feeds and backend alert rules.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-16 items-center gap-3 rounded-md border border-red-400/35 bg-red-950/40 px-4 py-3 text-sm text-red-50">
      <AlertTriangle aria-hidden className="h-5 w-5 text-red-300" />
      <div className="min-w-0">
        <p className="font-semibold">
          {formatMagnitude(event.magnitude)} earthquake near {event.province ?? event.place}
        </p>
        <p className="truncate text-xs text-red-100/75">
          {formatDepth(event.depth_km)} deep - {formatPhtDateTime(event.occurred_at)} PHT - {event.source}
        </p>
      </div>
    </div>
  );
}
