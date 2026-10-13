import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
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

/** The height that the layout keeps for the app bar (AppHeader), below which the banner sticks. */
async function appBarBottom(page: Page): Promise<number> {
  const top = await page.locator(".v-main").evaluate((main) => getComputedStyle(main).getPropertyValue("--v-layout-top"));
  expect(top).toMatch(/^\d+px$/);
  return Number.parseFloat(top);
}

/** The left and the right edge of `part`, in whole pixels. */
async function edges(part: Locator): Promise<number[]> {
  const box = (await part.boundingBox())!;
  return [Math.round(box.x), Math.round(box.x + box.width)];
}

/** Edits the source key in Metadata, which shows the banner of unsaved changes. */
async function editSourceKey(page: Page): Promise<Locator> {
  await page.getByRole("textbox", { name: "Source key" }).fill(EDITED_KEY);
  const banner = page.locator(".unsaved-banner");
  await expect(banner).toContainText("Unsaved changes to study.json: Source key");
  return banner;
}

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

test("Ctrl+S saves a collaborator that is typed but not yet added, and the field keeps the focus", async ({
  app,
  page,
}) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    await app.open(`${STUDY}/metadata`);
    const collaborators = page.getByRole("combobox", { name: "Collaborators" });
    await collaborators.focus();
    await collaborators.pressSequentially("Jane Doe");
    // The typed name is the only change: the field adds it to the list on Enter or blur.
    await collaborators.press("Control+s");
    await expect.poll(() => onDisk(path).collaborators).toContain("Jane Doe");
    await expect(page.locator(".unsaved-banner")).toContainText("study.json saved.");
    await expect(collaborators).toBeFocused();
    await expect(collaborators).toHaveValue("");
    await expect(page.locator(".collaborators-field .v-chip")).toContainText(["Jane Doe"]);
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
    expect(await edges(banner)).toEqual(await edges(page.locator(".metadata-form")));
    await expect(banner).toHaveCSS("border-top-left-radius", "8px");

    // It sticks below the app bar while the form scrolls under it, with square top corners, so
    // that nothing shows through there.
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    const appBar = await appBarBottom(page);
    await expect.poll(async () => Math.round((await banner.boundingBox())!.y)).toBe(appBar);
    await expect(banner).toHaveCSS("border-top-left-radius", "0px");
    await expect(banner).toHaveCSS("border-top-right-radius", "0px");
    await expect(banner).toHaveCSS("border-bottom-left-radius", "8px");
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(banner).toHaveCSS("border-top-left-radius", "8px");

    await page.keyboard.press("Control+s");
    await expect(banner).toContainText("study.json saved.");
    await expect(banner).not.toHaveClass(/unsaved-banner--dirty/);
    await expect.poll(() => onDisk(path).provenance?.source_key).toBe(EDITED_KEY);
    // The notice ends after a few seconds; Metadata keeps the row of the banner.
    await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
  } finally {
    writeFileSync(path, original);
  }
});

test("nothing moves when the first edit turns the banner amber or the notice of a save ends", async ({ app, page }) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await app.open(`${STUDY}/metadata`);
    const banner = page.locator(".unsaved-banner");
    await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
    const sourceKey = page.getByRole("textbox", { name: "Source key" });
    const top = async () => (await sourceKey.boundingBox())!.y;
    const start = await top();
    await sourceKey.press("End");
    await sourceKey.press(".");
    await expect(banner).toHaveClass(/unsaved-banner--dirty/);
    expect(await top()).toBe(start);
    await sourceKey.press("Control+s");
    await expect(banner).toContainText("study.json saved.");
    expect(await top()).toBe(start);
    await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
    expect(await top()).toBe(start);

    // In Data, the panes keep their place and their height when an edit of the notes starts.
    await page.evaluate(() => (window.location.hash = "#/studies/caffeine/Demo2020/data?file=subjects.tsv"));
    const pane = page.getByRole("region", { name: "Table subjects.tsv", exact: true });
    await pane.getByRole("button", { name: /^Notes of the subjects/ }).click();
    const description = pane.getByRole("textbox", { name: "Description 1" });
    await expect(description).toBeVisible();
    const before = (await pane.boundingBox())!;
    await description.press("End");
    await description.press("!");
    await expect(banner).toHaveClass(/unsaved-banner--dirty/);
    expect(await pane.boundingBox()).toEqual(before);
  } finally {
    writeFileSync(path, original);
  }
});

test("the banner keeps its height with and without unsaved changes and with a notice, in wide and narrow windows", async ({
  app,
  page,
}) => {
  await app.open(`${STUDY}/metadata`);
  const banner = page.locator(".unsaved-banner");
  const undo = page.getByRole("button", { name: "Undo", exact: true });
  const height = async () => (await banner.boundingBox())!.height;
  for (const [width, height_] of [
    [1440, 900],
    [1280, 520],
    [1000, 400],
    [390, 700],
  ] as const) {
    await page.setViewportSize({ width, height: height_ });
    await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
    const neutral = await height();
    // Four changed fields: the text wraps to two lines in a narrow window.
    await page.getByRole("textbox", { name: "PMID" }).fill("1");
    await page.getByRole("textbox", { name: "DOI" }).fill("10.1000/xyz");
    await page.getByRole("textbox", { name: "Source key" }).fill(EDITED_KEY);
    await page.getByRole("textbox", { name: "Description 1" }).fill("Edited.");
    await expect(banner).toContainText("Unsaved changes to study.json: PMID, DOI, Source key and 1 more");
    expect(await height(), `with unsaved changes at ${width} px`).toBe(neutral);
    // The notice of the discard, with Undo beside Discard and Save.
    await page.getByRole("button", { name: "Discard", exact: true }).click();
    await expect(undo).toBeVisible();
    await expect(banner).toContainText("Changes discarded.");
    expect(await height(), `with the notice at ${width} px`).toBe(neutral);
    await undo.click();
    await expect(banner).toHaveClass(/unsaved-banner--dirty/);
    expect(await height(), `after Undo at ${width} px`).toBe(neutral);
    await page.getByRole("button", { name: "Discard", exact: true }).click();
    await expect(undo).toBeHidden();
  }
});

test("a region of rows that scrolls into view stops 8 px below the banner, as the selected review item does", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 700, height: 700 });
  await app.open(`${STUDY}/data?file=outputs_Tab2.tsv&source=Tab2`);
  const banner = page.locator(".unsaved-banner");
  await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
  // The raw table of Tab2 in the source pane, above the rows of the table.
  const grid = page.locator(".rows-scroll").first();
  await expect(grid.getByRole("row").nth(1)).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await grid.evaluate((region) => region.scrollIntoView({ block: "start" }));
  await expect
    .poll(async () => {
      const [stuck, region] = [(await banner.boundingBox())!, (await grid.boundingBox())!];
      expect(Math.round(stuck.y)).toBe(await appBarBottom(page));
      return Math.round(region.y - (stuck.y + stuck.height));
    })
    .toBe(8);
});

test("Ctrl+S in Review keeps the banner there, with its notice and then neutral, and nothing below it moves", async ({
  app,
  page,
}) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    await app.open(`${STUDY}/metadata`);
    const banner = await editSourceKey(page);
    const sections = page.getByRole("navigation", { name: "Study sections" });
    await sections.getByRole("link", { name: /^Review\b/ }).click();
    await expect(banner).toHaveClass(/unsaved-banner--dirty/);
    const content = page.locator(".study-section .review");
    await expect(page.getByRole("article", { name: "Question" })).toBeVisible();
    const top = async () => (await content.boundingBox())!.y;
    const start = await top();

    await page.keyboard.press("Control+s");
    await expect(banner).toContainText("study.json saved.");
    await expect(banner).not.toHaveClass(/unsaved-banner--dirty/);
    await expect.poll(() => onDisk(path).provenance?.source_key).toBe(EDITED_KEY);
    expect(await top()).toBe(start);
    // The notice ends; the banner stays, neutral, until the curator leaves the section.
    await expect(banner).toHaveText(/^No unsaved changes to study\.json/);
    expect(await top()).toBe(start);

    // Without changes and notices, a section opens without the banner.
    await sections.getByRole("link", { name: /^Problems\b/ }).click();
    await expect(page.getByText("digitized_mismatch", { exact: true })).toBeVisible();
    await expect(banner).toBeHidden();
  } finally {
    writeFileSync(path, original);
  }
});

test("a discard in Problems keeps the banner there and offers Undo", async ({ app, page }) => {
  await app.open(`${STUDY}/metadata`);
  const banner = await editSourceKey(page);
  const sections = page.getByRole("navigation", { name: "Study sections" });
  await sections.getByRole("link", { name: /^Problems\b/ }).click();
  await expect(banner).toHaveClass(/unsaved-banner--dirty/);
  await page.getByRole("button", { name: "Discard", exact: true }).click();
  await expect(banner).toContainText("Changes discarded.");
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(banner).toContainText("Unsaved changes to study.json: Source key");
  await sections.getByRole("link", { name: /^Metadata\b/ }).click();
  await expect(page.getByRole("textbox", { name: "Source key" })).toHaveValue(EDITED_KEY);
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
  const appBar = await appBarBottom(page);
  /** How far the top of the outline of DOI is below the stuck banner. */
  const clearance = async () => {
    const [stuck, field] = [(await banner.boundingBox())!, (await outline.boundingBox())!];
    expect(Math.round(stuck.y)).toBe(appBar);
    return field.y - (stuck.y + stuck.height);
  };

  // Tab from PMID to DOI, whose top is 10 px under the stuck banner, whatever its height.
  await page.getByRole("textbox", { name: "PMID" }).evaluate((field: HTMLElement) => field.focus({ preventScroll: true }));
  const top = await outline.evaluate((field) => field.getBoundingClientRect().top + window.scrollY);
  const { height } = (await banner.boundingBox())!;
  await page.evaluate((y) => window.scrollTo(0, y), top - (appBar + height - 10));
  await expect.poll(clearance).toBeLessThan(0);
  await page.keyboard.press("Tab");
  await expect(doi).toBeFocused();
  await expect.poll(clearance).toBeGreaterThanOrEqual(0);

  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  await outline.evaluate((field) => field.scrollIntoView({ block: "start" }));
  await expect.poll(clearance).toBeGreaterThanOrEqual(0);
});

test("the banner is as wide as the content of each section in windows of 1280, 1440 and 1920 px", async ({ app, page }) => {
  await app.open(`${STUDY}/metadata`);
  const banner = await editSourceKey(page);
  const sections = page.getByRole("navigation", { name: "Study sections" });
  // The cards of Metadata end at 100rem; Review and Data take the whole width.
  for (const [section, content] of [
    ["Metadata", ".metadata-form"],
    ["Review", ".review"],
    ["Data", ".data-section"],
  ] as const) {
    await sections.getByRole("link", { name: new RegExp(`^${section}\\b`) }).click();
    for (const width of [1280, 1440, 1920]) {
      await page.setViewportSize({ width, height: 900 });
      const offsets = async () => {
        const [outer, inner] = [await edges(banner), await edges(page.locator(content))];
        return [outer[0]! - inner[0]!, outer[1]! - inner[1]!];
      };
      await expect.poll(offsets, `${section} at ${width} px`).toEqual([0, 0]);
    }
  }
});

test("a review item chosen below the cards scrolls to just below the banner", async ({ app, page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  // A short window, so that the page can scroll the item up while its target still loads.
  await page.setViewportSize({ width: 700, height: 450 });
  await app.open(`${STUDY}/metadata`);
  const banner = await editSourceKey(page);
  await page.getByRole("navigation", { name: "Study sections" }).getByRole("link", { name: /^Review\b/ }).click();
  const uncertainty = page.getByRole("list", { name: "Review items" }).getByRole("button", { name: /^Uncertainty/ });
  await uncertainty.click();
  const detail = page.locator(".review-selected");
  await expect(detail).toContainText("Table 2 gives the AUC from zero to infinity");
  // The detail stands below the cards in a narrow section, and the page scrolls to its start.
  expect((await detail.boundingBox())!.x).toBe((await uncertainty.boundingBox())!.x);
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
  await expect
    .poll(async () => {
      const [stuck, item] = [(await banner.boundingBox())!, (await detail.boundingBox())!];
      return Math.round(item.y - (stuck.y + stuck.height));
    })
    .toBe(8);
});

test("the banner stays above the sticky parts of the rows while stacked panes scroll under it", async ({ app, page }) => {
  await page.setViewportSize({ width: 700, height: 700 });
  await app.open(`${STUDY}/metadata`);
  const banner = await editSourceKey(page);
  await page.evaluate(() => (window.location.hash = "#/studies/caffeine/Demo2020/data?file=outputs_Tab2.tsv&source=Tab2"));
  await expect(page.getByRole("region", { name: "Rows of outputs_Tab2.tsv", exact: true }).getByRole("row").nth(1)).toBeVisible();
  // The source pane above the rows shows the raw table of Tab2: its header row, with the sticky
  // line number and the fade of the columns that follow, goes under the stuck banner.
  const grid = page.locator(".rows-scroll--sticky-line").first();
  await expect(grid.getByRole("row").nth(1)).toBeVisible();
  const appBar = await appBarBottom(page);
  const top = await grid.evaluate((region) => region.getBoundingClientRect().top + window.scrollY);
  await page.evaluate((y) => window.scrollTo(0, y), top - appBar - 10);
  await expect.poll(async () => Math.round((await banner.boundingBox())!.y)).toBe(appBar);
  const box = (await banner.boundingBox())!;
  expect((await grid.boundingBox())!.y).toBeLessThan(box.y + box.height);
  const covered = await page.evaluate(({ x, y, width, height }) => {
    const points: string[] = [];
    for (let left = x + 2; left < x + width - 2; left += 8)
      for (const top of [y + 2, y + height / 2, y + height - 2]) {
        const hit = document.elementFromPoint(left, top);
        if (!hit?.closest(".unsaved-banner")) points.push(`${left},${top}: ${hit?.tagName}.${hit?.className}`);
      }
    return points;
  }, box);
  expect(covered).toEqual([]);
});
