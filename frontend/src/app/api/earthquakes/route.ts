import { NextResponse } from "next/server";

import { API_BASE_URL } from "@/lib/api";

export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/earthquakes?page_size=100`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ items: [], total: 0, page: 1, page_size: 100 });
  }
}
