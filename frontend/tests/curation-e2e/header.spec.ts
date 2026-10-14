import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";
import { pixelStats } from "./pixels.ts";

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
    assets: [{ url: "https://example.org/run-1.json", sha256: "0".repeat(64) }],
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
      // The title gives way first, but keeps 8rem (the app sets the root font size to 87.5 %), with
      // what the study is doing beside it, if anything.
      const title = (await line.locator(".study-title-box").boundingBox())!;
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

test("what the study does for a moment after a save moves nothing on the page, at 1000, 1280 and 390 px", async ({
  app,
  page,
}) => {
  const path = join(app.server.workspace, "caffeine/Demo2020/study.json");
  const original = readFileSync(path, "utf8");
  try {
    await app.open("#/studies/caffeine/Demo2020/metadata");
    const sourceKey = page.getByRole("textbox", { name: "Source key" });
    const banner = page.locator(".unsaved-banner");
    for (const width of [1000, 1280, 390]) {
      await page.setViewportSize({ width, height: 800 });
      await layoutSettled(page, width);
      // Every change of the header: what the study does, the height of the header and where the form starts in the page.
      await page.evaluate(() => {
        const header = document.querySelector(".study-header")!;
        const form = document.querySelector(".metadata-form")!;
        const seen: string[] = [];
        const note = () =>
          seen.push(
            [
              header.querySelector(".fact-activity")?.textContent?.trim() ?? "",
              header.getBoundingClientRect().height,
              form.getBoundingClientRect().top + window.scrollY,
            ].join(" | "),
          );
        note();
        Object.assign(window, { __header: seen });
        new MutationObserver(note).observe(header, { subtree: true, childList: true, characterData: true });
      });
      const seen = () => page.evaluate(() => (window as unknown as { __header: string[] }).__header);
      await sourceKey.fill(`pkdb.manual.${width}`);
      await sourceKey.press("Control+s");
      await expect(banner).toContainText("study.json saved.");
      // The check after the save shows what it does, then its result.
      await expect.poll(async () => (await seen()).some((entry) => !entry.startsWith(" |"))).toBe(true);
      await expect(page.locator(".study-header .fact-activity")).toHaveCount(0);
      const parts = (await seen()).map((entry) => entry.split(" | ").slice(1).join(" | "));
      expect(new Set(parts), `the header and the form at ${width} px: ${(await seen()).join("; ")}`).toEqual(new Set([parts[0]]));
    }
  } finally {
    writeFileSync(path, original);
  }
});

/** The study band and a white card of the section in each theme (themes.ts, plugins/vuetify.ts). */
const BAND_COLORS = {
  light: { band: [236, 243, 244], card: [255, 255, 255] },
  dark: { band: [33, 57, 62], card: [25, 43, 49] },
} as const;

function expectColor(actual: readonly number[], expected: readonly number[], what: string): void {
  for (const [index, value] of actual.entries())
    expect(Math.abs(value - expected[index]!), `${what}: ${actual.join(",")} is near ${expected.join(",")}`).toBeLessThanOrEqual(2);
}

for (const theme of ["light", "dark"] as const) {
  test(`the study band sets the header and the tabs apart from the white cards, with every chip readable, in the ${theme} theme at 1280 and 1440 px`, async ({
    app,
    page,
  }, testInfo) => {
    const path = join(app.server.workspace, "caffeine/Draft2021/study.json");
    const original = readFileSync(path, "utf8");
    try {
      // Released, with an issue and curated by an AI: every chip of the header stands on the band.
      writeFileSync(path, `${JSON.stringify({ ...JSON.parse(original), ...RELEASED }, null, 2)}\n`);
      await page.emulateMedia({ colorScheme: theme });
      await app.open("#/studies/caffeine/Draft2021/metadata");
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      const band = page.locator(".study-band");
      await expect(band.getByText("PKDB01211 · released 2019-10-14")).toBeVisible();
      await expect(band.getByRole("navigation", { name: "Study sections" })).toBeVisible();
      // One rule below the band; the line of the tabs has none of its own.
      await expect(band).toHaveCSS("border-bottom-width", "1px");
      await expect(band.locator(".section-tabs-line")).toHaveCSS("border-bottom-width", "0px");
      const card = page.locator(".study-section .v-card").first();
      for (const width of [1280, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await layoutSettled(page, width);
        expectColor((await pixelStats(band)).dominant, BAND_COLORS[theme].band, `study band at ${width} px`);
        expectColor((await pixelStats(card)).dominant, BAND_COLORS[theme].card, `card at ${width} px`);
        // From edge to edge of the window, directly below the app bar.
        const bar = (await page.locator(".app-header").boundingBox())!;
        const placed = (await band.boundingBox())!;
        expect(placed.x).toBe(0);
        expect(placed.width).toBe(width);
        expect(Math.abs(placed.y - (bar.y + bar.height))).toBeLessThanOrEqual(0.5);
        await expectAccessible(page);
        const name = `study-band-${theme}-${width}.png`;
        await testInfo.attach(name, { body: await page.screenshot({ path: testInfo.outputPath(name) }), contentType: "image/png" });
      }
    } finally {
      writeFileSync(path, original);
    }
  });
}

test("in a narrow window the select of the sections stands in the study band, 8 px above its rule", async ({ app, page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await app.open("#/studies/caffeine/Demo2020/metadata");
  const band = page.locator(".study-band");
  await expect(band.getByRole("combobox", { name: "Section" })).toBeVisible();
  await expect(band).toHaveCSS("border-bottom-width", "1px");
  const box = (await band.boundingBox())!;
  const content = await band
    .locator(".section-tabs-line > *")
    .evaluateAll((parts) => Math.max(...parts.map((part) => part.getBoundingClientRect().bottom)));
  // 8 px between the last line of the band and its rule of 1 px.
  expect(box.y + box.height - 1 - content).toBeGreaterThanOrEqual(7.5);
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
    .toBe(0);
});
