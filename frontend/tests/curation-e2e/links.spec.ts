import type { Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

/** outputs_Tab2.tsv of Demo2020 beside Tab2: its lines 1 to 4 name the dose D100, 5 to 8 the dose D200. */
const OUTPUTS = "#/studies/caffeine/Demo2020/data?source=Tab2&file=outputs_Tab2.tsv";
/** timecourses_Fig1.tsv beside Fig1: its rows name the subject all and the dose D100. */
const FIG1 = "#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv";

/** The row of the rows pane of `file` at `line`. */
function rowAt(page: Page, file: string, line: number) {
  return page
    .getByRole("region", { name: `Rows of ${file}` })
    .getByRole("row")
    .filter({ has: page.getByRole("rowheader", { name: String(line), exact: true }) });
}

/** The entry of the navigator that names the source that shows. */
function sourceItem(page: Page, name: string) {
  return page.getByRole("list", { name: "Sources", exact: true }).locator("[aria-current]").filter({ hasText: name });
}

test("a name in a cell opens its row in interventions.tsv or subjects.tsv, and Back returns to the row of the link", async ({
  app,
  page,
}) => {
  await app.open(OUTPUTS);
  // D200 is line 2 of interventions.tsv. Line 6 is not selected yet.
  await rowAt(page, "outputs_Tab2.tsv", 6).getByRole("button", { name: "D200", exact: true }).click();
  await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data\?file=interventions\.tsv&line=2$/);
  const dose = rowAt(page, "interventions.tsv", 2);
  await expect(dose).toHaveClass(/grid-row--focus/);
  await expect(dose).toBeInViewport();
  await expect(dose.getByRole("rowheader")).toBeFocused();

  await page.goBack();
  await expect(page).toHaveURL(/data\?source=Tab2&file=outputs_Tab2\.tsv&line=6$/);
  const start = rowAt(page, "outputs_Tab2.tsv", 6);
  await expect(start).toHaveClass(/grid-row--focus/);
  await expect(start.getByRole("rowheader")).toBeFocused();
  await page.goForward();
  await expect(page).toHaveURL(/data\?file=interventions\.tsv&line=2$/);
  await page.goBack();

  await rowAt(page, "outputs_Tab2.tsv", 6).getByRole("button", { name: "all", exact: true }).click();
  await expect(page).toHaveURL(/data\?file=subjects\.tsv&line=1$/);
  const group = rowAt(page, "subjects.tsv", 1);
  await expect(group).toHaveClass(/grid-row--focus/);
  // The name of subjects.tsv is the row itself: it links nowhere.
  await expect(group.getByRole("button", { name: "all", exact: true })).toHaveCount(0);
});

test("the arrow keys reach the names of a row from its line number, and Enter follows one", async ({ app, page }) => {
  await app.open(`${OUTPUTS}&line=6`);
  const row = rowAt(page, "outputs_Tab2.tsv", 6);
  await expect(row.getByRole("rowheader")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(row.getByRole("button", { name: "all", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await expect(row.getByRole("button", { name: "D200", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await expect(row.getByRole("button", { name: "6", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/data\?file=interventions\.tsv&line=2$/);
  await expect(rowAt(page, "interventions.tsv", 2).getByRole("rowheader")).toBeFocused();
  await page.goBack();
  await expect(rowAt(page, "outputs_Tab2.tsv", 6).getByRole("rowheader")).toBeFocused();
});

test("a link to a table of another source switches the source pane, and Back returns to the table, line and source", async ({
  app,
  page,
}) => {
  await app.open(`${FIG1}&line=2`);
  await expect(sourceItem(page, "Fig1")).toBeVisible();
  const start = rowAt(page, "timecourses_Fig1.tsv", 2);
  await expect(start.getByRole("rowheader")).toBeFocused();
  // subjects.tsv names the source Text for its row all.
  await start.getByRole("button", { name: "all", exact: true }).click();
  await expect(page).toHaveURL(/data\?file=subjects\.tsv&line=1$/);
  await expect(sourceItem(page, "Text")).toBeVisible();
  await expect(sourceItem(page, "Fig1")).toHaveCount(0);
  const target = rowAt(page, "subjects.tsv", 1);
  await expect(target).toHaveClass(/grid-row--focus/);
  await expect(target.getByRole("rowheader")).toBeFocused();

  await page.goBack();
  await expect(page).toHaveURL(/data\?source=Fig1&file=timecourses_Fig1\.tsv&line=2$/);
  await expect(sourceItem(page, "Fig1")).toBeVisible();
  const back = rowAt(page, "timecourses_Fig1.tsv", 2);
  await expect(back).toHaveClass(/grid-row--focus/);
  await expect(back.getByRole("rowheader")).toBeFocused();
});

test("a link names its target table and line to screen readers", async ({ app, page }) => {
  await app.open(`${OUTPUTS}&line=6`);
  const row = rowAt(page, "outputs_Tab2.tsv", 6);
  await expect(row.getByRole("button", { name: "D200", exact: true })).toHaveAccessibleDescription(
    "Goes to line 2 of interventions.tsv.",
  );
  await expect(row.getByRole("button", { name: "all", exact: true })).toHaveAccessibleDescription(
    "Goes to line 1 of subjects.tsv.",
  );
});

test("the links of the names read well in both themes at 1440 and 1280 pixels", async ({ app, page }, testInfo) => {
  await app.open(`${OUTPUTS}&line=6`);
  const row = rowAt(page, "outputs_Tab2.tsv", 6);
  await expect(row.getByRole("rowheader")).toBeFocused();
  // The keyboard focus on a link shows its ring and its solid line in the screenshots.
  await page.keyboard.press("ArrowRight");
  const link = row.getByRole("button", { name: "all", exact: true });
  await expect(link).toBeFocused();
  await expect(link).toHaveCSS("text-decoration-style", "solid");
  await expect(row.getByRole("button", { name: "D200", exact: true })).toHaveCSS("text-decoration-style", "dotted");
  // Under the pointer a link has the pointer cursor and a solid line; the screenshots show neither.
  const dose = row.getByRole("button", { name: "D200", exact: true });
  await dose.hover();
  await expect(dose).toHaveCSS("cursor", "pointer");
  await expect(dose).toHaveCSS("text-decoration-style", "solid");
  await page.mouse.move(0, 0);
  await expect(dose).toHaveCSS("text-decoration-style", "dotted");
  for (const width of [1440, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await expectAccessible(page);
      const name = `links-${theme}-${width}.png`;
      const shot = await page.screenshot({ path: testInfo.outputPath(name) });
      await testInfo.attach(name, { body: shot, contentType: "image/png" });
    }
  }
});

test("Right scrolls a wide table sideways at the last name of a row, where the focus has nowhere to move", async ({ app, page }) => {
  await app.open(`${OUTPUTS}&line=6`);
  const row = rowAt(page, "outputs_Tab2.tsv", 6);
  await expect(row.getByRole("rowheader")).toBeFocused();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(row.getByRole("button", { name: "D200", exact: true })).toBeFocused();
  const region = page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" });
  const before = await region.evaluate((element) => element.scrollLeft);
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(before);
  await expect(row.getByRole("button", { name: "D200", exact: true })).toBeFocused();
});
