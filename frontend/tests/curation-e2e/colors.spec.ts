import { expect, test } from "./fixtures.ts";
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

test("a table shows its class of information: its kind, its header row and its cells in its color", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=subjects.tsv");
  const kind = page.getByRole("region", { name: "Table subjects.tsv" }).locator(".pane-head-kind");
  await expect(kind).toHaveText("Subjects");
  // The chip is tinted in blue, #1d5fb8, and its text stays in the text color of the surface.
  await expect(kind).toHaveCSS("color", "rgb(29, 95, 184)");
  await expect(kind.locator(".v-chip__content")).toHaveCSS("color", "rgb(0, 0, 0)");
  const rows = page.getByRole("region", { name: "Rows of subjects.tsv" });
  const header = rows.getByRole("columnheader", { name: "name", exact: true });
  const cell = rows.getByRole("cell", { name: "all", exact: true });
  await expect(cell).toBeVisible();
  expectColor((await pixelStats(header)).dominant, over("#1d5fb8", 0.16));
  expectColor((await pixelStats(cell)).dominant, over("#1d5fb8", 0.06));
});

test("the data of a figure are violet", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv");
  await expect(page.getByRole("region", { name: "Table timecourses_Fig1.tsv" }).locator(".pane-head-kind")).toHaveText("Timecourses");
  const rows = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  const header = rows.getByRole("columnheader", { name: "label", exact: true });
  await expect(header).toBeVisible();
  expectColor((await pixelStats(header)).dominant, over("#6a3fb5", 0.16));
});

test("the header row fades out to its own tint where more columns follow", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=timecourses_Fig1.tsv");
  const rows = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(rows.getByRole("columnheader", { name: "label", exact: true })).toBeVisible();
  await expect(page.locator(".rows-pane .table-grid")).toHaveClass(/table-grid--more/);
  const { width } = (await rows.boundingBox())!;
  // Ten pixels at the end of the header row, below the top of the fade and above the line of the row.
  const end = await pixelStats(rows, { x: width - 12, y: 8, width: 10, height: 12 });
  expectColor(end.dominant, over("#6a3fb5", 0.16));
});

test("the selected row has a frame of 1 px, and a problem in it keeps its outline inside the frame", async ({ app, page }) => {
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
});
