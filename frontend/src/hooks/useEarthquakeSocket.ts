import type { Earthquake } from "@/types/earthquake";

export interface EarthquakeSocketState {
  isConnected: boolean;
  events: Earthquake[];
  lastEvent: Earthquake | null;
  connectionError: string | null;
}

export function useEarthquakeSocket(): EarthquakeSocketState {
  return {
    isConnected: false,
    events: [],
    lastEvent: null,
    connectionError: null
  };
}

