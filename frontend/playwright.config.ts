import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "../tests/frontend/e2e",
  outputDir: "../tests/artifacts/playwright",
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: process.env.MJ_BASE_URL || "http://127.0.0.1:38000",
    channel: "chrome",
    ignoreHTTPSErrors: process.env.MJ_HTTPS_TEST === "1",
    headless: true,
    trace: "off",
    viewport: { width: 1440, height: 1000 },
  },
  reporter: [["list"]],
});
