import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:15173",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
  },
  webServer: [
    {
      command:
        "cd .. && SEGMENTATION_LABELER_WORKSPACE=/tmp/segmentation-labeler-e2e-registry uv run uvicorn seglabeler.api:app --host 127.0.0.1 --port 18000",
      url: "http://127.0.0.1:18000/api/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        "VITE_API_TARGET=http://127.0.0.1:18000 npm run dev -- --port 15173",
      url: "http://127.0.0.1:15173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
