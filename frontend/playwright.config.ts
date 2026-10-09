// End-to-end tests in a real browser (HANDOFF "Frontend (Vue)").
// `pnpm test:e2e` runs the smoke test against a running stack (`pnpm dev` or the e2e
// Compose profile); `pnpm exec playwright test screens` captures every screen for the
// visual check against the design export (not part of CI).
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3110",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
