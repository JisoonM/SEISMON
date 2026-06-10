import type { EarthquakeListResponse } from "@/types/earthquake";

export interface EarthquakeDataState {
  data: EarthquakeListResponse;
  isLoading: boolean;
  error: string | null;
}

export function useEarthquakeData(): EarthquakeDataState {
  return {
    data: { items: [], total: 0, page: 1, page_size: 100 },
    isLoading: false,
    error: null
  };
}

