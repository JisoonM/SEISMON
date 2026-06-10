import { create } from "zustand";

import type { Earthquake, IslandGroup, Source } from "@/types/earthquake";

export interface DashboardFilters {
  minMagnitude: number;
  source: Source | "ALL";
  islandGroup: IslandGroup | "ALL";
}

interface DashboardState {
  filters: DashboardFilters;
  selectedEvent: Earthquake | null;
  focusedEventId: string | null;
  historicalMode: boolean;
  setMinMagnitude: (value: number) => void;
  setSource: (value: Source | "ALL") => void;
  setIslandGroup: (value: IslandGroup | "ALL") => void;
  selectEvent: (event: Earthquake | null) => void;
  focusEvent: (event: Earthquake | null) => void;
  setHistoricalMode: (value: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  filters: {
    minMagnitude: 0,
    source: "ALL",
    islandGroup: "ALL"
  },
  selectedEvent: null,
  focusedEventId: null,
  historicalMode: false,
  setMinMagnitude: (value) =>
    set((state) => ({
      filters: { ...state.filters, minMagnitude: value }
    })),
  setSource: (value) =>
    set((state) => ({
      filters: { ...state.filters, source: value }
    })),
  setIslandGroup: (value) =>
    set((state) => ({
      filters: { ...state.filters, islandGroup: value }
    })),
  selectEvent: (event) => set({ selectedEvent: event }),
  focusEvent: (event) => set({ focusedEventId: event?.id ?? null, selectedEvent: event }),
  setHistoricalMode: (value) => set({ historicalMode: value })
}));
