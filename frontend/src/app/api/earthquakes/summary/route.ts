import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api";

const EMPTY_SUMMARY = {
  total_today: 0,
  total_this_week: 0,
  max_magnitude_today: null,
  avg_depth_today: null,
  most_affected_province: null,
  counts_by_alert_level: {},
  counts_by_island_group: {},
  hourly_counts: []
};

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/earthquakes/stats/summary`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json(EMPTY_SUMMARY);
  }
}
