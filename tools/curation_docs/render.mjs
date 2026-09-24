// Capture the running, authenticated local curation app. Never log the launch URL.
// PKDB_CURATION_URL='http://127.0.0.1:PORT/#token=...' node tools/curation_docs/render.mjs
import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
import { fileURLToPath } from "node:url";
import { mkdir } from "node:fs/promises";
const launchUrl = process.env.PKDB_CURATION_URL;
if (!launchUrl) throw new Error("Set PKDB_CURATION_URL to a running local curation launch URL.");
const parsed = new URL(launchUrl);
if (!["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) throw new Error("Use a loopback curation service.");
const destination = new URL("../../docs/images/curation/", import.meta.url);
await mkdir(destination, { recursive: true });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  await page.goto(launchUrl);
  await page.waitForFunction(() => document.querySelector("#connection").textContent !== "Connecting…");
  await page.locator("#study-search").fill(process.env.PKDB_CURATION_SCREENSHOT_FILTER || "Frost2013");
  await page.getByRole("checkbox", { name: "Select all visible studies", exact: true }).check();
  await page.getByRole("button", { name: "Validate now", exact: true }).click();
  await page.waitForFunction(async () => {
    const state = await (await fetch("/local/state")).json();
    return state.jobs.length && state.jobs.every(job => !["queued", "running"].includes(job.status));
  }, {}, { timeout: 120000 });
  await page.locator("#studies tr").filter({ hasText: "invalid" }).first().waitFor({ timeout: 120000 });
  await page.screenshot({ path: fileURLToPath(new URL("workspace.png", destination)), fullPage: false });
  await page.locator("#studies tr").filter({ hasText: "invalid" }).first().locator(".study-link").click({ timeout: 120000 });
  await page.getByRole("button", { name: "Problems", exact: true }).click();
  await page.locator(".problem").first().waitFor();
  await page.locator("#study-detail").scrollIntoViewIfNeeded();
  await page.locator("#study-detail").screenshot({ path: fileURLToPath(new URL("problems.png", destination)) });
} finally { await browser.close(); }
