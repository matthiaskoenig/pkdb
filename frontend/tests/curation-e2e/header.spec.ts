import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

/**
 * Draft2021 of the fixture has no workbook. Released, with an issue and curated by an AI, its
 * header shows every chip: the release, the issue, the provenance, No workbook and the problems.
 */
const RELEASED = {
  issue: 1580,
  release: { pkdb_id: "PKDB01211", date: "2019-10-14" },
  provenance: {
    kind: "automatic_curation",
    source_key: "pkdb.ai",
    method: "claude-opus-5-5",
    version: "1",
    run_id: "run-1",
    assets: [],
  },
};

/** Wait until the page has laid out at `width`: the viewport resizes asynchronously. */
async function layoutSettled(page: Page, width: number): Promise<void> {
  await expect
    .poll(() => page.evaluate(() => new Promise<number>((done) => requestAnimationFrame(() => done(document.documentElement.clientWidth)))))
    .toBe(width);
}

test("the chips of the study header keep their whole text where the header line is full", async ({ app, page }) => {
  const path = join(app.server.workspace, "caffeine/Draft2021/study.json");
  const original = readFileSync(path, "utf8");
  try {
    writeFileSync(path, `${JSON.stringify({ ...JSON.parse(original), ...RELEASED }, null, 2)}\n`);
    await app.open("#/studies/caffeine/Draft2021/metadata");
    const line = page.locator(".study-header-line");
    await expect(line.getByText("PKDB01211 · released 2019-10-14")).toBeVisible();
    await expect(line.getByText("No workbook")).toBeVisible();
    for (const width of [1280, 1440, 1920]) {
      await page.setViewportSize({ width, height: 900 });
      await layoutSettled(page, width);
      const cut = await line
        .locator(".v-chip")
        .evaluateAll((chips) =>
          chips.filter((chip) => chip.scrollWidth > chip.clientWidth).map((chip) => chip.textContent?.trim()),
        );
      expect(cut, `chips cut at ${width} px`).toEqual([]);
      // The title gives way first, but keeps 8rem of its text (the app sets the root font size to 87.5 %).
      const title = (await line.locator(".study-title").boundingBox())!;
      const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
      expect(title.width, `width of the title at ${width} px`).toBeGreaterThanOrEqual(8 * rem - 0.5);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
    }
  } finally {
    writeFileSync(path, original);
  }
});

test("the header of a study whose parts fit stays one line", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const line = page.locator(".study-header-line");
  await expect(line.getByRole("button", { name: "Validate", exact: true })).toBeVisible();
  expect((await line.boundingBox())!.height).toBeLessThanOrEqual(40);
});

test("nothing in the study header overlaps another part from 900 to 1100 px, also not its Upload tooltip", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const line = page.locator(".study-header-line");
  await expect(line.getByRole("button", { name: "Validate", exact: true })).toBeVisible();
  for (const width of [900, 1000, 1100]) {
    await page.setViewportSize({ width, height: 900 });
    await layoutSettled(page, width);
    // The leaf parts of the line: its own children, and the parts of the actions.
    const boxes = await line.evaluate((element) => {
      const leaves = [...element.children].flatMap((child) =>
        child.classList.contains("study-actions") ? [...child.querySelectorAll(":scope > .fact-status, :scope > .study-buttons > *")] : [child],
      );
      return leaves.map((leaf) => {
        const { left, right, top, bottom } = leaf.getBoundingClientRect();
        return { name: leaf.className, left, right, top, bottom };
      });
    });
    // The selector must find the parts of the line, or the loop below checks nothing.
    expect(boxes.length, `parts of the study header at ${width} px`).toBeGreaterThan(5);
    for (const [index, a] of boxes.entries())
      for (const b of boxes.slice(index + 1)) {
        const overlap = a.left < b.right - 0.5 && b.left < a.right - 0.5 && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
        expect(overlap, `${a.name} and ${b.name} overlap at ${width} px`).toBe(false);
      }
    // The tooltip of the disabled Upload says why; it must not cover the Review select.
    await line.locator(".upload-action").hover();
    const tooltip = page.locator(".v-tooltip > .v-overlay__content");
    await expect(tooltip).toHaveText(/Work offline is on/);
    const tip = (await tooltip.boundingBox())!;
    const select = (await line.locator(".review-select").boundingBox())!;
    const covers = tip.x < select.x + select.width && select.x < tip.x + tip.width && tip.y < select.y + select.height && select.y < tip.y + tip.height;
    expect(covers, `the tooltip covers the Review select at ${width} px`).toBe(false);
    await page.mouse.move(0, 400);
    await expect(tooltip).toBeHidden();
  }
});
