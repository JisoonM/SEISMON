import { useQuery } from "@tanstack/react-query";

import { fetchJson } from "@/lib/api";
import {
  earthquakeListResponseSchema,
  earthquakeSummarySchema,
  type EarthquakeListResponse,
  type EarthquakeSummary
} from "@/types/earthquake";

const EMPTY_LIST: EarthquakeListResponse = { items: [], total: 0, page: 1, page_size: 100 };

export interface EarthquakeDataState {
  earthquakes: EarthquakeListResponse;
  summary: EarthquakeSummary | null;
  isLoading: boolean;
  error: string | null;
}

export function useEarthquakeData(): EarthquakeDataState {
  const listQuery = useQuery({
    queryKey: ["earthquakes", "latest"],
    queryFn: async ({ signal }) => earthquakeListResponseSchema.parse(await fetchJson("/api/earthquakes", signal)),
    staleTime: 15_000
  });

  const summaryQuery = useQuery({
    queryKey: ["earthquakes", "summary"],
    queryFn: async ({ signal }) => earthquakeSummarySchema.parse(await fetchJson("/api/earthquakes/summary", signal)),
    staleTime: 30_000
  });

  const error = listQuery.error ?? summaryQuery.error;

  return {
    earthquakes: listQuery.data ?? EMPTY_LIST,
    summary: summaryQuery.data ?? null,
    isLoading: listQuery.isLoading || summaryQuery.isLoading,
    error: error instanceof Error ? error.message : null
  };
}
