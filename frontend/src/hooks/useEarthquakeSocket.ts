import { useEffect, useState } from "react";

import { createEarthquakeSocket } from "@/lib/socket";
import type { Earthquake } from "@/types/earthquake";
import { realtimeEventSchema } from "@/types/earthquake";

export interface EarthquakeSocketState {
  isConnected: boolean;
  events: Earthquake[];
  lastEvent: Earthquake | null;
  connectionError: string | null;
}

export function useEarthquakeSocket(): EarthquakeSocketState {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<Earthquake[]>([]);
  const [lastEvent, setLastEvent] = useState<Earthquake | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  useEffect(() => {
    const socket = createEarthquakeSocket();

    function handleRealtimeEvent(payload: unknown) {
      const parsed = realtimeEventSchema.safeParse(payload);
      if (!parsed.success) {
        setConnectionError("Invalid realtime event payload");
        return;
      }

      const event = parsed.data;
      setLastEvent(event);
      setEvents((current) => [event, ...current.filter((item) => item.id !== event.id)].slice(0, 50));
      setConnectionError(null);
    }

    socket.on("connect", () => {
      setIsConnected(true);
      setConnectionError(null);
    });
    socket.on("disconnect", () => setIsConnected(false));
    socket.on("connect_error", (error: Error) => {
      setIsConnected(false);
      setConnectionError(error.message);
    });
    socket.on("earthquake:new", handleRealtimeEvent);
    socket.on("earthquake:hydrate", (payload: unknown) => {
      if (!Array.isArray(payload)) {
        return;
      }
      const parsed = payload.map((item) => realtimeEventSchema.safeParse(item)).filter((item) => item.success);
      setEvents(parsed.map((item) => item.data));
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("connect_error");
      socket.off("earthquake:new");
      socket.off("earthquake:hydrate");
      socket.disconnect();
    };
  }, []);

  return { isConnected, events, lastEvent, connectionError };
}
