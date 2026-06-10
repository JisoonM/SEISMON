import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useEarthquakeSocket } from "@/hooks/useEarthquakeSocket";
import { sampleEarthquake } from "@/test/fixtures";

type Handler = (payload?: unknown) => void;

const handlers = new Map<string, Handler>();
const mockSocket = {
  on: vi.fn((event: string, handler: Handler) => {
    handlers.set(event, handler);
    return mockSocket;
  }),
  off: vi.fn((event: string) => {
    handlers.delete(event);
    return mockSocket;
  }),
  disconnect: vi.fn()
};

vi.mock("@/lib/socket", () => ({
  createEarthquakeSocket: vi.fn(() => mockSocket)
}));

describe("useEarthquakeSocket", () => {
  afterEach(() => {
    handlers.clear();
    vi.clearAllMocks();
  });

  it("tracks connection state and live earthquake events", () => {
    const { result, unmount } = renderHook(() => useEarthquakeSocket());

    act(() => handlers.get("connect")?.());
    expect(result.current.isConnected).toBe(true);

    act(() => handlers.get("earthquake:new")?.(sampleEarthquake));
    expect(result.current.lastEvent?.event_id).toBe(sampleEarthquake.event_id);
    expect(result.current.events).toHaveLength(1);

    act(() => handlers.get("disconnect")?.());
    expect(result.current.isConnected).toBe(false);

    unmount();
    expect(mockSocket.disconnect).toHaveBeenCalled();
  });

  it("ignores malformed realtime payloads", () => {
    const { result } = renderHook(() => useEarthquakeSocket());

    act(() => handlers.get("earthquake:new")?.({ event_id: "" }));

    expect(result.current.events).toHaveLength(0);
    expect(result.current.connectionError).toContain("Invalid realtime event");
  });
});
