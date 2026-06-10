import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatCards } from "@/components/StatCards";
import { sampleEarthquake, sampleSummary } from "@/test/fixtures";

describe("StatCards", () => {
  it("renders operational metrics from summary and latest event", () => {
    render(<StatCards summary={sampleSummary} latestEvent={sampleEarthquake} isLoading={false} />);

    expect(screen.getByText("Events Today")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("M5.6")).toBeInTheDocument();
    expect(screen.getByText("1 red")).toBeInTheDocument();
    expect(screen.getByText("Metro Manila")).toBeInTheDocument();
  });

  it("renders stable loading placeholders", () => {
    render(<StatCards summary={null} latestEvent={null} isLoading />);

    expect(screen.getAllByText("--")).toHaveLength(4);
  });
});
