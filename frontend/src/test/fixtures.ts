import type { Earthquake, EarthquakeSummary } from "@/types/earthquake";

export const sampleEarthquake: Earthquake = {
  id: "6f11f26c-d684-4f2c-a83c-b77245b5429d",
  event_id: "phivolcs-20260610-001",
  source: "PHIVOLCS",
  magnitude: 5.6,
  magnitude_type: "Mw",
  depth_km: 18,
  latitude: 14.5,
  longitude: 121,
  place: "Metro Manila",
  province: "Metro Manila",
  region: "NCR",
  island_group: "Luzon",
  felt: true,
  tsunami_warning: false,
  alert_level: "red",
  occurred_at: "2026-06-10T02:30:00Z",
  ingested_at: "2026-06-10T02:31:00Z",
  raw_data: {}
};

export const sampleSummary: EarthquakeSummary = {
  total_today: 8,
  total_this_week: 31,
  max_magnitude_today: 5.6,
  avg_depth_today: 24.2,
  most_affected_province: "Metro Manila",
  counts_by_alert_level: { red: 1, orange: 2, yellow: 3, green: 2 },
  counts_by_island_group: { Luzon: 5, Visayas: 2, Mindanao: 1 },
  hourly_counts: [{ hour: "2026-06-10T02:00:00Z", count: 3 }]
};
