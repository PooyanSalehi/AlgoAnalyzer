import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Accept any host header so remote preview/sandbox domains work.
    allowedHosts: true,
    // The dev server proxies API calls to the FastAPI backend, so the
    // browser only ever talks to one origin (no CORS in development).
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
} as never);
