import { defineConfig, devices } from "@playwright/test";

// The curation app against the real local server `pkdb curate`: each spec file starts its own
// server on a fresh copy of tools/curation_testing/fixture (see tests/curation-e2e/fixtures.ts).
export default defineConfig({
  testDir: "./tests/curation-e2e",
  outputDir: "./test-results/curation",
  globalSetup: "./tests/curation-e2e/global-setup.ts",
  globalTeardown: "./tests/curation-e2e/global-teardown.ts",
  fullyParallel: false,
  // Spec files run in parallel, each against its own server; the tests of one file in order.
  workers: "50%",
  forbidOnly: Boolean(process.env.CI),
  // The suite runs against a local server without shared state, so a retry would only hide flakiness.
  retries: 0,
  timeout: 60_000,
  // The file watcher settles a save for a second, and the app polls every 1.5 seconds.
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report/curation" }]],
  use: {
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
});
