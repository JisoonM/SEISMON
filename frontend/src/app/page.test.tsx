import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/page";
import { sampleEarthquake, sampleSummary } from "@/test/fixtures";

vi.mock("@/hooks/useEarthquakeData", () => ({
  useEarthquakeData: () => ({
    earthquakes: { items: [sampleEarthquake], total: 1, page: 1, page_size: 100 },
    summary: sampleSummary,
    isLoading: false,
    error: null
  })
}));

vi.mock("@/hooks/useEarthquakeSocket", () => ({
  useEarthquakeSocket: () => ({
    isConnected: true,
    events: [sampleEarthquake],
    lastEvent: sampleEarthquake,
    connectionError: null
  })
}));

describe("DashboardPage", () => {
  it("renders the Phase 6 operations dashboard shell", () => {
    render(<DashboardPage />);

    expect(screen.getByRole("banner")).toHaveTextContent("SEISMON");
    expect(screen.getByText("Live")).toBeInTheDocument();
    expect(screen.getByText("PHT")).toBeInTheDocument();
    expect(screen.getByText("Events Today")).toBeInTheDocument();
    expect(screen.getByText("Philippines seismic operations")).toBeInTheDocument();
  });
});
