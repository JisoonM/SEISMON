import { z } from "zod";

export const alertLevelSchema = z.enum(["green", "yellow", "orange", "red"]);
export const sourceSchema = z.enum(["PHIVOLCS", "USGS", "EMSC"]);
export const islandGroupSchema = z.enum(["Luzon", "Visayas", "Mindanao", "Outside PH"]);

export const earthquakeSchema = z.object({
  id: z.string(),
  event_id: z.string(),
  source: sourceSchema,
  magnitude: z.number(),
  magnitude_type: z.string(),
  depth_km: z.number(),
  latitude: z.number(),
  longitude: z.number(),
  place: z.string(),
  province: z.string().nullable(),
  region: z.string().nullable(),
  island_group: islandGroupSchema.nullable(),
  felt: z.boolean(),
  tsunami_warning: z.boolean(),
  alert_level: alertLevelSchema,
  occurred_at: z.string(),
  ingested_at: z.string().optional(),
  raw_data: z.record(z.unknown()).optional()
});

export const earthquakeListResponseSchema = z.object({
  items: z.array(earthquakeSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number()
});

export const earthquakeSummarySchema = z.object({
  total_today: z.number(),
  total_this_week: z.number(),
  max_magnitude_today: z.number().nullable(),
  avg_depth_today: z.number().nullable(),
  most_affected_province: z.string().nullable(),
  counts_by_alert_level: z.record(z.number()),
  counts_by_island_group: z.record(z.number()),
  hourly_counts: z.array(
    z.object({
      hour: z.string(),
      count: z.number()
    })
  )
});

export const realtimeEventSchema = earthquakeSchema.omit({ ingested_at: true, raw_data: true }).extend({
  ingested_at: z.string().optional(),
  raw_data: z.record(z.unknown()).optional()
});

export type AlertLevel = z.infer<typeof alertLevelSchema>;
export type Source = z.infer<typeof sourceSchema>;
export type IslandGroup = z.infer<typeof islandGroupSchema>;
export type Earthquake = z.infer<typeof earthquakeSchema>;
export type EarthquakeListResponse = z.infer<typeof earthquakeListResponseSchema>;
export type EarthquakeSummary = z.infer<typeof earthquakeSummarySchema>;
export type RealtimeEvent = z.infer<typeof realtimeEventSchema>;
