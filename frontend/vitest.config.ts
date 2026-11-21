import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  root: fileURLToPath(new URL("..", import.meta.url)),
  cacheDir: fileURLToPath(
    new URL("./node_modules/.vite/vitest", import.meta.url),
  ),
  resolve: {
    alias: { vitest: fileURLToPath(import.meta.resolve("vitest")) },
  },
  server: {
    fs: {
      allow: [
        fileURLToPath(new URL("../tests", import.meta.url)),
        fileURLToPath(new URL(".", import.meta.url)),
      ],
    },
  },
  test: { include: ["tests/frontend/unit/**/*.test.ts"] },
});
