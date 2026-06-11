import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SeismicMap } from "@/components/SeismicMap";
import { useDashboardStore } from "@/store/dashboardStore";
import { sampleEarthquake } from "@/test/fixtures";
import type { Earthquake } from "@/types/earthquake";

const { mapInstances, MockMap } = vi.hoisted(() => {
  const instances: unknown[] = [];

  class MockMap {
    addControl = vi.fn();
    addLayer = vi.fn();
    addSource = vi.fn();
    flyTo = vi.fn();
    getLayer = vi.fn(() => true);
    getSource = vi.fn(() => ({ setData: vi.fn() }));
    off = vi.fn();
    on = vi.fn((event: string, _layerOrHandler: unknown, maybeHandler?: unknown) => {
      if (event === "load") {
        const handler = typeof _layerOrHandler === "function" ? _layerOrHandler : maybeHandler;
        window.setTimeout(() => (handler as () => void)(), 0);
      }
      return this;
    });
    remove = vi.fn();
    setFilter = vi.fn();
    setLayoutProperty = vi.fn();

    constructor() {
      instances.push(this);
    }
  }

  return { mapInstances: instances, MockMap };
});

vi.mock("mapbox-gl", () => ({
  default: {
    accessToken: "",
    Map: MockMap,
    NavigationControl: vi.fn()
  }
}));

const quietQuake: Earthquake = {
  ...sampleEarthquake,
  id: "f4eae4d9-f10d-4f5b-a0ec-690fa07d55bb",
  event_id: "usgs-low-001",
  source: "USGS",
  magnitude: 3.2,
  alert_level: "green",
  place: "Offshore Zambales",
  province: "Zambales",
  occurred_at: "2026-06-10T01:30:00Z"
};

function currentMap() {
  return mapInstances[0] as InstanceType<typeof MockMap> | undefined;
}

describe("SeismicMap", () => {
  beforeEach(() => {
    mapInstances.length = 0;
    process.env.NEXT_PUBLIC_MAPBOX_TOKEN = "test-token";
    useDashboardStore.setState({
      filters: { minMagnitude: 0, source: "ALL", islandGroup: "ALL" },
      focusedEventId: null,
      historicalMode: false,
      selectedEvent: null
    });
  });

  it("renders Phase 7 map controls, legend, and filtered feed count", async () => {
    render(<SeismicMap events={[sampleEarthquake, quietQuake]} />);

    expect(screen.getByRole("button", { name: /toggle heatmap/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /toggle province borders/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset map view/i })).toBeInTheDocument();
    expect(screen.getByText("Magnitude legend")).toBeInTheDocument();
    expect(screen.getByText("2 plotted events")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Minimum magnitude"), { target: { value: "5" } });

    expect(screen.getByText("1 plotted event")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /toggle heatmap/i }));
    fireEvent.click(screen.getByRole("button", { name: /toggle province borders/i }));

    await waitFor(() => {
      expect(currentMap()?.setLayoutProperty).toHaveBeenCalledWith("earthquake-heat", "visibility", "visible");
      expect(currentMap()?.setLayoutProperty).toHaveBeenCalledWith("province-lines", "visibility", "visible");
    });
  });

  it("flies to the newest significant event", async () => {
    render(<SeismicMap events={[sampleEarthquake, quietQuake]} />);

    await waitFor(() => {
      expect(currentMap()?.flyTo).toHaveBeenCalledWith(
        expect.objectContaining({
          center: [sampleEarthquake.longitude, sampleEarthquake.latitude],
          zoom: 7
        })
      );
    });
  });
});
