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
  ingested_at: z.string()
});

export const earthquakeListResponseSchema = z.object({
  items: z.array(earthquakeSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number()
});

export type AlertLevel = z.infer<typeof alertLevelSchema>;
export type Source = z.infer<typeof sourceSchema>;
export type IslandGroup = z.infer<typeof islandGroupSchema>;
export type Earthquake = z.infer<typeof earthquakeSchema>;
export type EarthquakeListResponse = z.infer<typeof earthquakeListResponseSchema>;

