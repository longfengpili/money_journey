import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  base: command === "serve" ? "/app/" : "/static/app/",
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    emptyOutDir: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (
            id.includes("node_modules/chart.js") ||
            id.includes("node_modules/@kurkle")
          )
            return "charts";
          if (
            id.includes("node_modules/react") ||
            id.includes("node_modules/scheduler")
          )
            return "react";
        },
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: process.env.MJ_BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
}));
