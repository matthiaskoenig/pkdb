import { expect, expectAccessible, test } from "./fixtures.ts";
import { pixelStats } from "./pixels.ts";

/** `hex` at `share` over the white surface of the light theme, as the browser mixes it. */
function over(hex: string, share: number): number[] {
  return [1, 3, 5].map((start) => Math.round(Number.parseInt(hex.slice(start, start + 2), 16) * share + 255 * (1 - share)));
}

function expectColor(actual: readonly number[], expected: readonly number[]): void {
  for (const [index, value] of actual.entries())
    expect(Math.abs(value - expected[index]!), `${actual.join(",")} is near ${expected.join(",")}`).toBeLessThanOrEqual(2);
}

/** The primary color of the light theme, #176b70. */
const PRIMARY = "rgb\\(23, 107, 112\\)";
/** The colors of the classes in the light theme (info.ts). */
const SUBJECTS = "#1d5fb8";
const INTERVENTIONS = "#2e7d32";
const DATA = "#616161";
const WHITE = [255, 255, 255];
/** The text of `study` and `source`: the medium emphasis of the light theme. */
const MUTED = "rgba(0, 0, 0, 0.6)";

test("subjects.tsv is blue but for study and source, which are muted in italics without a tint", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=subjects.tsv");
  const kind = page.getByRole("region", { name: "Table subjects.tsv" }).locator(".pane-head-kind");
  await expect(kind).toHaveText("Subjects");
  // The chip is tinted in blue, #1d5fb8, and its text stays in the text color of the surface.
  await expect(kind).toHaveCSS("color", "rgb(29, 95, 184)");
  await expect(kind.locator(".v-chip__content")).toHaveCSS("color", "rgb(0, 0, 0)");
  const rows = page.getByRole("region", { name: "Rows of subjects.tsv" });
  const cell = rows.getByRole("cell", { name: "all", exact: true });
  await expect(cell).toBeVisible();
  expectColor((await pixelStats(rows.getByRole("columnheader", { name: "name", exact: true }))).dominant, over(SUBJECTS, 0.16));
  expectColor((await pixelStats(cell)).dominant, over(SUBJECTS, 0.06));
  const study = rows.getByRole("cell", { name: "Demo2020", exact: true });
  await expect(study).toHaveCSS("font-style", "italic");
  await expect(study).toHaveCSS("color", MUTED);
  expectColor((await pixelStats(study)).dominant, WHITE);
  const studyHeader = rows.getByRole("columnheader", { name: "study", exact: true });
  await expect(studyHeader).toHaveCSS("font-style", "italic");
  expectColor((await pixelStats(studyHeader)).dominant, WHITE);
});

test("a table of data tints its subjects column blue, its interventions column green and its other columns grey, apart from the page", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv");
  const kind = page.getByRole("region", { name: "Table timecourses_Fig1.tsv" }).locator(".pane-head-kind");
  await expect(kind).toHaveText("Timecourses");
  await expect(kind).toHaveCSS("color", "rgb(97, 97, 97)");
  const rows = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  const header = (name: string) => rows.getByRole("columnheader", { name, exact: true });
  await expect(header("label")).toBeVisible();
  expectColor((await pixelStats(header("subjects"))).dominant, over(SUBJECTS, 0.16));
  expectColor((await pixelStats(header("interventions"))).dominant, over(INTERVENTIONS, 0.16));
  expectColor((await pixelStats(header("label"))).dominant, over(DATA, 0.22));
  expectColor((await pixelStats(header("source"))).dominant, WHITE);
  const first = rows.getByRole("row").filter({ has: page.getByRole("rowheader", { name: "1", exact: true }) });
  const cell = (name: string) => first.getByRole("cell", { name, exact: true });
  expectColor((await pixelStats(cell("all"))).dominant, over(SUBJECTS, 0.06));
  expectColor((await pixelStats(cell("D100"))).dominant, over(INTERVENTIONS, 0.06));
  const data = (await pixelStats(cell("caf_plasma_100mg"))).dominant;
  expectColor(data, over(DATA, 0.12));
  await expect(cell("Fig1")).toHaveCSS("font-style", "italic");
  await expect(cell("Fig1")).toHaveCSS("color", MUTED);
  // The grey of the data differs from the grey page around the panes.
  const background = await page.locator(".v-application").evaluate((element) => getComputedStyle(element).backgroundColor);
  const pageColor = background.match(/\d+/g)!.slice(0, 3).map(Number);
  expect(Math.max(...data.map((value, index) => Math.abs(value - pageColor[index]!)))).toBeGreaterThanOrEqual(8);
});

test("the header row fades out to the tint of the column at the end of the view", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv");
  const rows = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(rows.getByRole("columnheader", { name: "label", exact: true })).toBeVisible();
  const grid = page.locator(".rows-pane .table-grid");
  await expect(grid).toHaveClass(/table-grid--more/);
  // The class of the header cell that the end of the view cuts, below the fade.
  const info = await rows.evaluate((region) => {
    const box = region.getBoundingClientRect();
    const x = box.left + region.clientLeft + region.clientWidth - 2;
    const cell = document.elementsFromPoint(x, box.top + 11).find((element) => element.matches("thead th"));
    return cell instanceof HTMLElement ? (cell.dataset.info ?? null) : null;
  });
  const tints: Record<string, number[]> = {
    subjects: over(SUBJECTS, 0.16),
    interventions: over(INTERVENTIONS, 0.16),
    data: over(DATA, 0.22),
  };
  expect(Object.keys(tints)).toContain(info);
  await expect(grid).toHaveClass(new RegExp(`(^| )grid-info--${info}( |$)`));
  const { width } = (await rows.boundingBox())!;
  // Ten pixels at the end of the header row, below the top of the fade and above the line of the row.
  const end = await pixelStats(rows, { x: width - 12, y: 8, width: 10, height: 12 });
  expectColor(end.dominant, tints[info!]!);
});

test("the selected row has a frame of 1 px and its own tint over the tints of the columns, and a problem in it keeps its outline inside the frame", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv&line=5");
  const row = page
    .getByRole("region", { name: "Rows of timecourses_Fig1.tsv" })
    .getByRole("row")
    .filter({ has: page.getByRole("rowheader", { name: "5", exact: true }) });
  // The line cell draws the start and the top of the frame and the other cells its top and bottom.
  const line = `${PRIMARY} 0px 1px 0px 0px inset, ${PRIMARY} 0px -1px 0px 0px inset`;
  await expect(row.getByRole("rowheader")).toHaveCSS("box-shadow", new RegExp(`${PRIMARY} 1px 1px 0px 0px inset, ${PRIMARY} 0px -1px 0px 0px inset$`));
  await expect(row.getByRole("cell").first()).toHaveCSS("box-shadow", new RegExp(`${line}$`));
  // The amber outline of the warning digitized_mismatch at the mean of line 5, once validation reported it, inside the frame.
  await expect(row.locator("td.grid-cell--warning")).toHaveCSS(
    "box-shadow",
    new RegExp(`^rgb\\(143, 83, 0\\) 0px 0px 0px 2px inset, ${line}$`),
  );
  // The selected row shows the primary color at 12 %, not the grey of its data columns or the blue of its subjects.
  expectColor((await pixelStats(row.getByRole("cell", { name: "caf_plasma_100mg", exact: true }))).dominant, over("#176b70", 0.12));
  expectColor((await pixelStats(row.getByRole("cell", { name: "all", exact: true }))).dominant, over("#176b70", 0.12));
});

test("a raw extraction has no tint, and the navigator marks the data grey and the raw extractions with an outline", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=Demo2020_Tab2.tsv");
  const kind = page.getByRole("region", { name: "Table Demo2020_Tab2.tsv" }).locator(".pane-head-kind");
  await expect(kind).toHaveText("Raw table");
  await expect(kind).toHaveClass(/v-chip--variant-outlined/);
  const rows = page.getByRole("region", { name: "Raw table Demo2020_Tab2.tsv" });
  const cell = rows.getByRole("cell", { name: "Cmax (mg/l)", exact: true });
  await expect(cell).toBeVisible();
  expectColor((await pixelStats(cell)).dominant, WHITE);
  expectColor((await pixelStats(rows.getByRole("columnheader", { name: "A", exact: true }))).dominant, WHITE);
  const navigator = page.getByRole("navigation", { name: "Tables and sources" });
  const bar = (stem: string) => navigator.locator(".nav-file").filter({ hasText: stem }).locator(".nav-bar");
  await expect(bar("timecourses_Fig1")).toHaveCSS("background-color", "rgb(97, 97, 97)");
  await expect(bar("Demo2020_Tab2")).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(bar("Demo2020_Tab2")).toHaveCSS("border-top-color", "rgb(95, 107, 109)");
});

test("the tints of the columns read well in both themes at 1440 and 1280 pixels", async ({ app, page }, testInfo) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv&line=5");
  const pane = page.getByRole("region", { name: "Table timecourses_Fig1.tsv" });
  await expect(page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" })).toBeVisible();
  for (const width of [1440, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await expectAccessible(page);
      const name = `columns-${theme}-${width}.png`;
      const shot = await page.screenshot({ path: testInfo.outputPath(name) });
      await testInfo.attach(name, { body: shot, contentType: "image/png" });
    }
  }
  await expect(pane).toBeVisible();
});
