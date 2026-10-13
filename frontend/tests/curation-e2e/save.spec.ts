import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";

interface StudyJson {
  provenance?: { kind?: string; source_key?: string };
  [key: string]: unknown;
}

/** The path of study.json of Demo2020 in the workspace of the server. */
function studyJsonPath(workspace: string): string {
  return join(workspace, "caffeine/Demo2020/study.json");
}

/** study.json as it is on disk. */
function onDisk(path: string): StudyJson {
  return JSON.parse(readFileSync(path, "utf8")) as StudyJson;
}

const EDITED_KEY = "pkdb.manual.edited";

/** The height of the app bar (AppHeader), below which the banner sticks. */
const APP_BAR = 36;

/** The bodies of the writes of study.json that the page sends from now on. */
function metadataWrites(page: Page): string[] {
  const writes: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname === "/local/studies/metadata")
      writes.push(request.postData() ?? "");
  });
  return writes;
}

/** Records for each S pressed whether the app prevented the default; a listener after the app's sees it. */
async function recordSaveKeys(page: Page): Promise<() => Promise<boolean[]>> {
  await page.evaluate(() => {
    const seen: boolean[] = [];
    Object.assign(window, { __saveKeys: seen });
    window.addEventListener("keydown", (event) => {
      if (event.key.toLowerCase() === "s") seen.push(event.defaultPrevented);
    });
  });
  return () => page.evaluate(() => (window as unknown as { __saveKeys: boolean[] }).__saveKeys);
}

test("Ctrl+S saves study.json from the field just edited, and without changes writes nothing", async ({ app, page }) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  const writes = metadataWrites(page);
  try {
    await app.open(`${STUDY}/metadata`);
    const sourceKey = page.getByRole("textbox", { name: "Source key" });
    await expect(sourceKey).toHaveValue("pkdb.manual");
    const prevented = await recordSaveKeys(page);

    // Without changes: nothing to save, and no save dialog of the browser either.
    await page.keyboard.press("Control+s");
    await expect.poll(prevented).toEqual([true]);
    expect(writes).toEqual([]);

    await sourceKey.fill(EDITED_KEY);
    await sourceKey.press("Control+s");
    await expect.poll(prevented).toEqual([true, true]);
    await expect.poll(() => onDisk(path).provenance?.source_key).toBe(EDITED_KEY);
    expect(writes).toHaveLength(1);
  } finally {
    writeFileSync(path, original);
  }
});

test("the banner under the tabs names the change, stays in view while the form scrolls, and Ctrl+S saves", async ({
  app,
  page,
}) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    await app.open(`${STUDY}/metadata`);
    await page.getByRole("textbox", { name: "Source key" }).fill(EDITED_KEY);
    const banner = page.locator(".unsaved-banner");
    await expect(banner).toContainText("Unsaved changes to study.json: Source key");
    await expect(banner).toHaveClass(/unsaved-banner--dirty/);
    // Directly under the tabs, as wide as the cards below it.
    const tabs = (await page.locator(".section-tabs-line").boundingBox())!;
    const placed = (await banner.boundingBox())!;
    const below = placed.y - (tabs.y + tabs.height);
    expect(below).toBeGreaterThanOrEqual(0);
    expect(below).toBeLessThanOrEqual(12);
    const cards = (await page.locator(".metadata-form").boundingBox())!;
    expect([placed.x, placed.x + placed.width]).toEqual([cards.x, cards.x + cards.width]);

    // It sticks below the app bar while the form scrolls under it.
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    await expect.poll(async () => Math.round((await banner.boundingBox())!.y)).toBe(APP_BAR);

    await page.keyboard.press("Control+s");
    await expect(banner).toContainText("study.json saved.");
    await expect(banner).not.toHaveClass(/unsaved-banner--dirty/);
    await expect.poll(() => onDisk(path).provenance?.source_key).toBe(EDITED_KEY);
    // The notice ends after a few seconds, and the banner with it.
    await expect(banner).toBeHidden();
  } finally {
    writeFileSync(path, original);
  }
});

test("the selected review item sticks below the banner while Review scrolls", async ({ app, page }) => {
  await page.setViewportSize({ width: 1440, height: 500 });
  await app.open(`${STUDY}/metadata`);
  await page.getByRole("textbox", { name: "Source key" }).fill(EDITED_KEY);
  await page.getByRole("navigation", { name: "Study sections" }).getByRole("link", { name: /^Review\b/ }).click();
  const banner = page.locator(".unsaved-banner");
  await expect(banner).toContainText("Unsaved changes to study.json: Source key");
  await expect(page.getByRole("article", { name: "Question" })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
  const stuck = (await banner.boundingBox())!;
  const selected = (await page.locator(".review-selected").boundingBox())!;
  expect(selected.y).toBeGreaterThanOrEqual(stuck.y + stuck.height);
});

test("a field that the keyboard focuses or that scrolls into view stops below the banner", async ({ app, page }) => {
  await page.setViewportSize({ width: 1440, height: 600 });
  await app.open(`${STUDY}/metadata`);
  await page.getByRole("textbox", { name: "Source key" }).fill(EDITED_KEY);
  const banner = page.locator(".unsaved-banner");
  await expect(banner).toContainText("Unsaved changes to study.json: Source key");
  const doi = page.getByRole("textbox", { name: "DOI" });
  const outline = page.locator(".v-field").filter({ has: doi });
  /** How far the top of the outline of DOI is below the stuck banner. */
  const clearance = async () => {
    const [stuck, field] = [(await banner.boundingBox())!, (await outline.boundingBox())!];
    expect(Math.round(stuck.y)).toBe(APP_BAR);
    return field.y - (stuck.y + stuck.height);
  };

  // Tab from PMID to DOI, which is under the banner.
  await page.getByRole("textbox", { name: "PMID" }).evaluate((field: HTMLElement) => field.focus({ preventScroll: true }));
  const top = await outline.evaluate((field) => field.getBoundingClientRect().top + window.scrollY);
  await page.evaluate((y) => window.scrollTo(0, y - 60), top);
  await page.keyboard.press("Tab");
  await expect(doi).toBeFocused();
  await expect.poll(clearance).toBeGreaterThanOrEqual(0);

  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await outline.evaluate((field) => field.scrollIntoView({ block: "start" }));
  await expect.poll(clearance).toBeGreaterThanOrEqual(0);
});
