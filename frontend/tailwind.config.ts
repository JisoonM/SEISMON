import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0a0f1e",
        surface: "#111827",
        border: "#1f2937",
        muted: "#94a3b8",
        accent: "#3b82f6",
        alertGreen: "#22c55e",
        alertYellow: "#eab308",
        alertOrange: "#f97316",
        alertRed: "#ef4444"
      },
      boxShadow: {
        panel: "0 16px 40px rgba(0, 0, 0, 0.22)"
      }
    }
  },
  plugins: [animate]
};

export default config;
