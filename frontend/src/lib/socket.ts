import { io } from "socket.io-client";

export const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL ?? "http://localhost:8000";

export function createEarthquakeSocket() {
  return io(SOCKET_URL, {
    path: "/socket.io",
    transports: ["websocket"],
    reconnectionAttempts: 5,
    reconnectionDelay: 1200
  });
}
