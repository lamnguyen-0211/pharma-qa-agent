import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { delimiter, join } from "node:path";

const cachedSystemLibraries = join(
  homedir(),
  ".cache",
  "ms-playwright",
  "system-libs",
  "usr",
  "lib",
  "x86_64-linux-gnu",
);

if (existsSync(cachedSystemLibraries)) {
  process.env.LD_LIBRARY_PATH = [cachedSystemLibraries, process.env.LD_LIBRARY_PATH]
    .filter(Boolean)
    .join(delimiter);
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
