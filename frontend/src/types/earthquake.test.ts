import { describe, expect, it } from "vitest";

import { earthquakeListResponseSchema, earthquakeSummarySchema, realtimeEventSchema } from "@/types/earthquake";
import { sampleEarthquake, sampleSummary } from "@/test/fixtures";

describe("earthquake schemas", () => {
  it("validates backend list, summary, and realtime payloads", () => {
    expect(earthquakeListResponseSchema.parse({ items: [sampleEarthquake], total: 1, page: 1, page_size: 100 }).items[0].source).toBe("PHIVOLCS");
    expect(earthquakeSummarySchema.parse(sampleSummary).max_magnitude_today).toBe(5.6);
    expect(realtimeEventSchema.parse(sampleEarthquake).event_id).toBe("phivolcs-20260610-001");
  });
});
