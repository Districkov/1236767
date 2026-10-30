import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// сборка кладётся прямо в ../static, откуда её отдаёт server.py
export default defineConfig({
  base: "/static/",
  plugins: [react()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8017",
    },
  },
});
