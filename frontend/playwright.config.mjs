import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: process.env.CI ? 1 : undefined,
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  globalTimeout: 5 * 60 * 1000,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://127.0.0.1:3000",
    channel: "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
