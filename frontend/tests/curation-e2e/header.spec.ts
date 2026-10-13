import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
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

test("the chips of the study header keep their whole text where the header line is full", async ({ app, page }) => {
  test.fail(true, "The chips of the header shrink and cut their text (#934); fixed with the header line that wraps.");
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
      const cut = await line
        .locator(".v-chip")
        .evaluateAll((chips) =>
          chips.filter((chip) => chip.scrollWidth > chip.clientWidth).map((chip) => chip.textContent?.trim()),
        );
      expect(cut, `chips cut at ${width} px`).toEqual([]);
      // The title gives way first, but keeps 8rem of its text.
      const title = (await line.locator(".study-title").boundingBox())!;
      expect(title.width, `width of the title at ${width} px`).toBeGreaterThanOrEqual(128);
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
