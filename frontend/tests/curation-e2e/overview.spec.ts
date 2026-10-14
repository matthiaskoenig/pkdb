import type { Locator, Page } from "@playwright/test";
import { expect, setAutomaticActions, test } from "./fixtures.ts";

function studies(page: Page) {
  return page.getByRole("table", { name: "Studies of the workspace" });
}

/** The rows of the studies below the header row. */
function studyRows(page: Page) {
  return studies(page).getByRole("rowgroup").nth(1).getByRole("row");
}

function studyRow(page: Page, id: string) {
  return studies(page).getByRole("row", { name: new RegExp(`^Select ${id} `) });
}

function chip(page: Page, label: string) {
  return page.getByRole("group", { name: "Filter by status" }).getByRole("button", { name: new RegExp(`^${label} \\d+$`) });
}

/** Wait until the first validation of both studies has finished. */
async function validated(page: Page): Promise<void> {
  await expect(studyRow(page, "caffeine/Demo2020").getByRole("cell", { name: "2 warnings" })).toBeVisible();
  await expect(studyRow(page, "caffeine/Draft2021").getByRole("cell", { name: "1 error" })).toBeVisible();
}

/** Wait until the page has laid out at `width`: the viewport resizes asynchronously. */
async function layoutSettled(page: Page, width: number): Promise<void> {
  await expect
    .poll(() => page.evaluate(() => new Promise<number>((done) => requestAnimationFrame(() => done(document.documentElement.clientWidth)))))
    .toBe(width);
}

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

const FIELDS = ["search", "substance", "curator"] as const;
type HeaderPart = "heading" | "count" | (typeof FIELDS)[number] | "chips" | "lastChip";

/** The boxes of the parts of the header of the overview: the outlines of the fields, the first and the last status chip. */
async function headerBoxes(page: Page): Promise<Record<HeaderPart, Box>> {
  const chips = page.getByRole("group", { name: "Filter by status" }).getByRole("button");
  const parts: Record<HeaderPart, Locator> = {
    heading: page.getByRole("heading", { name: "Studies", level: 1 }),
    count: page.locator(".overview-count"),
    search: page.locator(".overview-search .v-field"),
    substance: page.locator(".overview-substance .v-field"),
    curator: page.locator(".overview-curator .v-field"),
    chips: chips.first(),
    lastChip: chips.last(),
  };
  const boxes = await Promise.all(
    Object.entries(parts).map(async ([name, locator]) => [name, (await locator.boundingBox())!] as const),
  );
  return Object.fromEntries(boxes) as Record<HeaderPart, Box>;
}

function middle(box: Box): number {
  return box.y + box.height / 2;
}

/** How far the page scrolls sideways. */
function sideScroll(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
}

test.beforeEach(async ({ app }) => {
  await app.open();
});

test("lists the format 2 studies of the workspace and counts the format 1 folder", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Studies", level: 1 })).toBeVisible();
  await expect(studyRows(page)).toHaveCount(2);
  await expect(studyRow(page, "caffeine/Demo2020")).toContainText(
    "Caffeine in plasma after two oral doses in a synthetic test study",
  );
  await expect(studyRow(page, "caffeine/Draft2021")).toContainText("A synthetic draft study of caffeine tablets");
  await expect(page.getByText("1 study format 1 folder is not listed.")).toHaveText(
    "1 study format 1 folder is not listed. It stays on the released app version until it is converted.",
  );
  await expect(page.getByRole("banner").getByText("curator", { exact: true })).toBeVisible();
  await validated(page);
});

test("the table fits a window of 1280 px without horizontal scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await validated(page);
  const wrapper = page.locator(".study-table .v-table__wrapper");
  const [scrollWidth, clientWidth] = await wrapper.evaluate((element) => [element.scrollWidth, element.clientWidth]);
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
});

test("the labels of the column headers share one baseline", async ({ page }) => {
  await expect(studyRows(page)).toHaveCount(2);
  // The box of the text of each label: with one font, equal bottoms mean one baseline.
  const labels = await studies(page)
    .getByRole("columnheader")
    .evaluateAll((headers) =>
      headers.flatMap((header) => {
        const text = document.createTreeWalker(header, NodeFilter.SHOW_TEXT, {
          acceptNode: (node) => (node.textContent?.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
        }).nextNode();
        if (!text) return [];
        const range = document.createRange();
        range.selectNodeContents(text);
        return [{ label: text.textContent?.trim() ?? "", bottom: range.getBoundingClientRect().bottom }];
      }),
    );
  expect(labels.map((entry) => entry.label)).toEqual([
    "Study",
    "Release",
    "Issue",
    "Curators",
    "Review",
    "Open items",
    "Problems",
    "Sync",
    "Last upload",
  ]);
  const bottoms = labels.map((entry) => entry.bottom);
  expect(Math.max(...bottoms) - Math.min(...bottoms), JSON.stringify(labels)).toBeLessThanOrEqual(1);
});

test("filters the studies by search and status", async ({ page }) => {
  await validated(page);
  const search = page.getByRole("textbox", { name: "Search studies" });
  await search.fill("draft2021");
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await expect(page.getByText("1 of 2 studies")).toBeVisible();
  // The title matches too.
  await search.fill("two oral doses");
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Demo2020")).toBeVisible();
  await page.getByRole("button", { name: "Clear Search studies" }).click();
  await expect(studyRows(page)).toHaveCount(2);

  // Draft2021 has an error; Demo2020 is in review with open items.
  await chip(page, "Needs attention").click();
  await expect(chip(page, "Needs attention")).toHaveAttribute("aria-pressed", "true");
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await expect(studyRows(page)).toHaveCount(2);
  await chip(page, "Draft").click();
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await chip(page, "In review").click();
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Demo2020")).toBeVisible();
  await chip(page, "Approved").click();
  await expect(page.getByText("No studies match these filters.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(chip(page, "All")).toHaveAttribute("aria-pressed", "true");
  await expect(studyRows(page)).toHaveCount(2);
});

test("filters the studies by curator and keeps the filters when a study is opened", async ({ page }) => {
  await validated(page);
  const curator = page.getByRole("combobox", { name: "Curator" });
  await curator.focus();
  await curator.press("ArrowDown");
  // The user of the app, curator, curates both studies.
  await page.getByRole("option", { name: "Me: curator (2)", exact: true }).click();
  await expect(studyRows(page)).toHaveCount(2);
  await page.getByRole("textbox", { name: "Search studies" }).fill("draft2021");
  await expect(studyRows(page)).toHaveCount(1);

  await studyRow(page, "caffeine/Draft2021").getByRole("link", { name: "caffeine/Draft2021" }).click();
  await expect(page.getByRole("heading", { name: "caffeine/Draft2021", level: 1 })).toBeVisible();
  await page.getByRole("link", { name: "PK-DB Local curation" }).click();
  await expect(page.getByRole("heading", { name: "Studies", level: 1 })).toBeVisible();
  await expect(studyRows(page)).toHaveCount(1);
  await expect(page.getByRole("textbox", { name: "Search studies" })).toHaveValue("draft2021");
  await expect(page.getByRole("combobox", { name: "Curator" })).toHaveValue("Me: curator (2)");
  await expect(page.getByText("1 of 2 studies")).toBeVisible();
});

test("the heading, the count, the search, the selects and the status chips share one line at 1440 px", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await layoutSettled(page, 1440);
  await validated(page);
  const boxes = await headerBoxes(page);
  const line = middle(boxes.heading);
  for (const name of [...FIELDS, "chips", "lastChip"] as const) {
    expect(Math.abs(middle(boxes[name]) - line), `middle of ${name}`).toBeLessThanOrEqual(2);
  }
  // The count stands on the baseline of the heading, inside its line.
  expect(middle(boxes.count)).toBeGreaterThan(boxes.heading.y);
  expect(middle(boxes.count)).toBeLessThan(boxes.heading.y + boxes.heading.height);
  // From left to right in this order, none over another.
  const order = (["heading", "count", ...FIELDS, "chips"] as const).map((name) => boxes[name]);
  for (let index = 1; index < order.length; index++) {
    expect(order[index]!.x).toBeGreaterThanOrEqual(order[index - 1]!.x + order[index - 1]!.width);
  }

  // The header and the table in both themes, for the manual look at 1280 and 1440 px.
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme });
    await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
    for (const width of [1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await layoutSettled(page, width);
      const name = `overview-${theme}-${width}.png`;
      const shot = await page.screenshot({ path: testInfo.outputPath(name) });
      await testInfo.attach(name, { body: shot, contentType: "image/png" });
    }
  }
  await page.emulateMedia({ colorScheme: "light" });
});

test("the header of a workspace of 1,503 studies stays one line in a 1440 px window with a scrollbar", async ({
  page,
}) => {
  // 1440 px less a scrollbar of 15 px. pkdb_data has about 1,500 studies: the counts have four digits.
  await page.setViewportSize({ width: 1425, height: 900 });
  await layoutSettled(page, 1425);
  await validated(page);
  const middles = await page.evaluate(() => {
    document.querySelector(".overview-count")!.textContent = "1,503 studies";
    document.querySelector(".overview-count-sizer")!.textContent = "1,503 of 1,503 studies";
    const counts = ["1,503", "312", "1,380", "73", "50"];
    document.querySelectorAll(".overview-chips .chip-count").forEach((count, index) => {
      count.textContent = counts[index]!;
    });
    const chips = [...document.querySelectorAll(".overview-chips .v-chip")];
    const parts = [
      document.querySelector(".overview-heading h1")!,
      document.querySelector(".overview-search .v-field")!,
      document.querySelector(".overview-substance .v-field")!,
      document.querySelector(".overview-curator .v-field")!,
      chips[0]!,
      chips.at(-1)!,
    ];
    return parts.map((part) => {
      const box = part.getBoundingClientRect();
      return box.top + box.height / 2;
    });
  });
  for (const value of middles) expect(Math.abs(value - middles[0]!), JSON.stringify(middles)).toBeLessThanOrEqual(2);
});

test("in a narrower window the status chips move below the fields first, and on a phone each field takes the whole width", async ({
  page,
}) => {
  await validated(page);
  for (const width of [1280, 960]) {
    await page.setViewportSize({ width, height: 900 });
    await layoutSettled(page, width);
    const boxes = await headerBoxes(page);
    const line = middle(boxes.heading);
    for (const name of FIELDS) {
      expect(Math.abs(middle(boxes[name]) - line), `middle of ${name} at ${width} px`).toBeLessThanOrEqual(2);
    }
    // The chips share the line, or stand below the fields: never above them or between them.
    const below = Math.max(...FIELDS.map((name) => boxes[name].y + boxes[name].height));
    const onLine = Math.abs(middle(boxes.chips) - line) <= 2 && Math.abs(middle(boxes.lastChip) - line) <= 2;
    expect(onLine || boxes.chips.y >= below, `chips at ${width} px`).toBe(true);
    if (width === 960) expect(boxes.chips.y).toBeGreaterThanOrEqual(below);
    expect(await sideScroll(page)).toBe(0);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await layoutSettled(page, 390);
  const content = await page.locator(".overview").evaluate((element) => {
    const style = getComputedStyle(element);
    const box = element.getBoundingClientRect();
    return { left: box.left + parseFloat(style.paddingLeft), right: box.right - parseFloat(style.paddingRight) };
  });
  const boxes = await headerBoxes(page);
  let top = boxes.heading.y + boxes.heading.height;
  for (const name of FIELDS) {
    const box = boxes[name];
    expect(Math.abs(box.x - content.left), `left of ${name}`).toBeLessThanOrEqual(1);
    expect(Math.abs(box.x + box.width - content.right), `right of ${name}`).toBeLessThanOrEqual(1);
    expect(box.y, `${name} below the part above it`).toBeGreaterThanOrEqual(top);
    top = box.y + box.height;
  }
  expect(boxes.chips.y).toBeGreaterThanOrEqual(top);
  expect(await sideScroll(page)).toBe(0);
});

test("the filter fields keep their place when the number of shown studies or the counts of the status chips change", async ({
  page,
}) => {
  // Wide enough for the header in one line.
  await page.setViewportSize({ width: 1440, height: 900 });
  await validated(page);
  const fields = FIELDS.map((name) => page.locator(`.overview-${name} .v-field`));
  const boxes = () => Promise.all(fields.map((field) => field.boundingBox()));
  const before = await boxes();
  // A search changes the count beside the heading, which stands before the fields.
  const count = page.locator(".overview-count");
  const search = page.getByRole("textbox", { name: "Search studies" });
  await expect(count).toHaveText("2 studies");
  await search.fill("draft2021");
  await expect(count).toHaveText("1 of 2 studies");
  expect(await boxes()).toEqual(before);
  await search.fill("no such study");
  await expect(count).toHaveText("0 of 2 studies");
  expect(await boxes()).toEqual(before);
  await search.fill("");
  await expect(count).toHaveText("2 studies");
  // Counts of more digits, as in a workspace of hundreds of studies, make the chips wider.
  await page.locator(".overview-chips .chip-count").evaluateAll((counts) => {
    for (const chipCount of counts) chipCount.textContent = "1234";
  });
  expect(await boxes()).toEqual(before);
});

test("Validate queues a job, and the study shows it until it ran", async ({ page }) => {
  await validated(page);
  // While automatic actions are paused, the job waits in the queue.
  await setAutomaticActions(page, true);
  const row = studyRow(page, "caffeine/Draft2021");
  await row.getByRole("checkbox", { name: "Select caffeine/Draft2021" }).check();
  await expect(page.getByText("1 study selected")).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Validation queued for 1 study." })).toBeVisible();
  await expect(row.getByText("Queued", { exact: true })).toBeVisible();

  await setAutomaticActions(page, false);
  await expect(row.getByText("Queued", { exact: true })).toBeHidden();
  await expect(row.getByRole("cell", { name: "1 error" })).toBeVisible();
});

test("a dialog returns the keyboard focus to the control that opened it", async ({ page }) => {
  const settings = page.getByRole("button", { name: "Settings", exact: true });
  await settings.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Connection settings" });
  await expect(dialog).toBeVisible();
  // The dialog takes the focus once it shows; Escape closes it from there.
  await expect.poll(() => dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(settings).toBeFocused();

  // An item of a menu goes with the menu: the focus returns to the button of the menu.
  const connection = page.getByRole("button", { name: /^Connection: / });
  await connection.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Connection settings" }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(connection).toBeFocused();
});

test("the theme that the curator chose paints first on a page without stored choice", async ({ app, page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  const application = page.locator(".v-application");
  await expect(application).toHaveClass(/(^| )v-theme--light( |$)/);
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(application).toHaveClass(/(^| )v-theme--dark( |$)/);
  // pkdb curate keeps the choice and puts it into index.html.
  await expect
    .poll(async () => (await page.request.get(`${app.server.origin}/`)).text())
    .toMatch(/<meta name="pkdb-theme" content="dark"/);

  // As after a restart on another port: the storage of the origin is empty.
  await page.evaluate(() => localStorage.clear());
  await page.addInitScript(() => {
    const observer = new MutationObserver(() => {
      const element = document.querySelector(".v-application");
      if (!element) return;
      document.documentElement.dataset.firstTheme = [...element.classList].find((name) => name.startsWith("v-theme--"));
      observer.disconnect();
    });
    observer.observe(document, { childList: true, subtree: true });
  });
  await page.reload();
  await expect(application).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-first-theme", "v-theme--dark");

  // Back to the theme of the system, for the other tests of the file.
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(application).toHaveClass(/(^| )v-theme--light( |$)/);
  await expect
    .poll(async () => (await page.request.get(`${app.server.origin}/`)).text())
    .toMatch(/<meta name="pkdb-theme" content="system"/);
});
