import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

/** The study.json of Draft2021, which has one error. */
const DRAFT = "caffeine/Draft2021/study.json";
/** Why the servers of these tests offer no upload. */
const OFFLINE = "Work offline is on. Turn it off in the settings to upload.";

function studyRow(page: Page, id: string): Locator {
  return page
    .getByRole("table", { name: "Studies of the workspace" })
    .getByRole("row", { name: new RegExp(`^Select ${id} `) });
}

/** Wait until the page has laid out at `width`: the viewport resizes asynchronously. */
async function layoutSettled(page: Page, width: number): Promise<void> {
  await expect
    .poll(() => page.evaluate(() => new Promise<number>((done) => requestAnimationFrame(() => done(document.documentElement.clientWidth)))))
    .toBe(width);
}

/** Open the On save menu from its button, which shows `shown`: the group of its actions. */
async function openOnSave(page: Page, shown: string): Promise<Locator> {
  await page.getByRole("button", { name: `On save: ${shown}` }).click();
  const actions = page.getByRole("group", { name: "On save action" });
  await expect(actions).toBeVisible();
  return actions;
}

/** Choose `to` in the On save menu, which shows `from`, and close the menu. */
async function setOnSave(page: Page, from: string, to: "Validate" | "Off"): Promise<void> {
  const actions = await openOnSave(page, from);
  await actions.getByRole("button", { name: to, exact: true }).click();
  await expect(actions.getByRole("button", { name: to, exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape");
  await expect(actions).toBeHidden();
  await expect(page.getByRole("button", { name: `On save: ${to}` })).toBeVisible();
}

/** The number of jobs of the local server, the finished ones included. */
async function jobCount(page: Page): Promise<number> {
  const state = (await page.evaluate(async () => (await fetch("/local/state")).json())) as { jobs: unknown[] };
  return state.jobs.length;
}

test("On save in the top bar sets what a save does for every study", async ({ app, page }) => {
  const path = join(app.server.workspace, DRAFT);
  const original = readFileSync(path, "utf8");
  await app.open();
  const draft = studyRow(page, "caffeine/Draft2021");
  // The first validation of every study ran.
  await expect(studyRow(page, "caffeine/Demo2020").getByRole("cell", { name: "2 warnings" })).toBeVisible();
  await expect(draft.getByRole("cell", { name: "1 error", exact: true })).toBeVisible();
  try {
    // Offline, Upload cannot be chosen, and the menu says why.
    const actions = await openOnSave(page, "Validate");
    await expect(actions.getByRole("button", { name: "Validate", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(actions.getByRole("button", { name: "Upload", exact: true })).toBeDisabled();
    await expect(actions).toContainText(OFFLINE);
    await page.keyboard.press("Escape");
    await expect(actions).toBeHidden();

    // Off: a save marks the study as changed and starts no job.
    await setOnSave(page, "Validate", "Off");
    const jobs = await jobCount(page);
    const study = JSON.parse(original) as { descriptions?: string[] };
    const descriptions = [...(study.descriptions ?? []), "Saved while On save is Off."];
    writeFileSync(path, `${JSON.stringify({ ...study, descriptions }, null, 2)}\n`);
    await expect(draft).toContainText("Changed since the last check");
    // The watcher queues the job of a save one second after the last change.
    await page.waitForTimeout(2_500);
    await expect(draft).toContainText("Changed since the last check");
    expect(await jobCount(page)).toBe(jobs);

    // The local server keeps the choice: a new page shows it.
    await page.reload();
    await expect(page.getByRole("button", { name: "On save: Off" })).toBeVisible();

    // Validate: the next save validates the study.
    await setOnSave(page, "Off", "Validate");
    writeFileSync(path, original);
    await expect(draft.getByRole("cell", { name: "1 error", exact: true })).toBeVisible();
    expect(await jobCount(page)).toBeGreaterThan(jobs);
  } finally {
    writeFileSync(path, original);
    if (await page.getByRole("button", { name: "On save: Off" }).isVisible()) await setOnSave(page, "Off", "Validate");
  }
});

test("On save sits beside File watching, and its menu reads well in both themes from 960 to 1440 px", async ({
  app,
  page,
}, testInfo) => {
  await app.open();
  const onSave = page.getByRole("button", { name: "On save: Validate" });
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme });
    await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
    for (const width of [960, 1280, 1440]) {
      await page.setViewportSize({ width, height: 800 });
      await layoutSettled(page, width);
      await expect(onSave).toBeVisible();
      // In the order of the header and without overlaps: the app name, File watching, On save, Connection.
      const parts = [
        page.locator(".app-header .brand"),
        page.getByRole("button", { name: /^File watching: / }),
        onSave,
        page.getByRole("button", { name: /^Connection: / }),
      ];
      const boxes = await Promise.all(parts.map(async (part) => (await part.boundingBox())!));
      for (const [index, box] of boxes.slice(0, -1).entries())
        expect(box.x + box.width, `part ${index} of the header at ${width} px`).toBeLessThanOrEqual(boxes[index + 1]!.x + 0.5);
      // The label shows from 1280 px, as the other labels of the header.
      await expect(onSave.getByText("On save", { exact: true })).toBeVisible({ visible: width >= 1280 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
      if (width === 960) continue;
      await onSave.click();
      const panel = page.locator(".on-save-panel");
      await expect(panel).toBeVisible();
      await expect(panel).toContainText(OFFLINE);
      await expectAccessible(page);
      const name = `on-save-${theme}-${width}.png`;
      await testInfo.attach(name, { body: await page.screenshot({ path: testInfo.outputPath(name) }), contentType: "image/png" });
      await page.keyboard.press("Escape");
      await expect(panel).toBeHidden();
    }
  }
});

test("the collapsed header has On save as one more entry", async ({ app, page }, testInfo) => {
  await app.open();
  await page.setViewportSize({ width: 900, height: 800 });
  await layoutSettled(page, 900);
  await page.getByRole("button", { name: "Header menu" }).click();
  const actions = await openOnSave(page, "Validate");
  await expect(actions.getByRole("button", { name: "Off", exact: true })).toBeVisible();
  await expect(actions).toContainText(OFFLINE);
  await expectAccessible(page);
  const name = "on-save-collapsed.png";
  await testInfo.attach(name, { body: await page.screenshot({ path: testInfo.outputPath(name) }), contentType: "image/png" });
});

test("the study page leaves On save to the top bar", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  await expect(page.getByRole("navigation", { name: "Study sections" })).toBeVisible();
  await expect(page.getByRole("button", { name: "On save: Validate" })).toBeVisible();
  await expect(page.locator(".section-tabs-line")).not.toContainText("On save");
});
