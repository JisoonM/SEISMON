import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({ items: [], total: 0, page: 1, page_size: 100 });
}

