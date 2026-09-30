/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // GitHub-dark inspired palette
        canvas: "#0d1117",
        surface: "#161b22",
        raised: "#1c2129",
        edge: {
          DEFAULT: "#30363d",
          bright: "#3d444d",
        },
        ink: {
          DEFAULT: "#e6edf3",
          muted: "#9198a1",
          subtle: "#6e7681",
        },
        algoA: "#58a6ff",
        algoB: "#bc8cff",
        ok: "#3fb950",
        warn: "#d29922",
        bad: "#f85149",
        accent: "#2ea043",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "JetBrains Mono",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(1,4,9,0.6)",
        glow: "0 0 0 1px rgba(56,139,253,0.35), 0 8px 32px rgba(56,139,253,0.15)",
      },
      animation: {
        "pulse-soft": "pulse 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
