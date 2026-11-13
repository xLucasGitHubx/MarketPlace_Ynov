import { defineConfig, devices } from "@playwright/test";

/**
 * QA visuelle optionnelle (desktop 1440 + mobile 390).
 *
 * Prérequis :
 *   cd web && npm install && npx playwright install chromium
 *
 * Contre mocks (recommandé, sans Azure live) :
 *   npm run qa:screenshots
 *
 * Contre l’API locale : démarrer uvicorn + `npm run dev`, puis pointer
 * baseURL sur http://127.0.0.1:5173 (proxy Vite).
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: "desktop-1440",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "mobile-390",
      use: {
        ...devices["iPhone 12"],
        viewport: { width: 390, height: 844 },
      },
    },
  ],
});
