import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { columnLetters } from "../../src/curation-app/columns.ts";
import { expect, runTool, setAutomaticActions, test } from "./fixtures.ts";

const TABLE = "timecourses_Fig1.tsv";
const SHEET = "timecourses_Fig1";

/** The cells of the TSV table of Demo2020 by line, the header being line 1. */
function readTable(workspace: string): string[][] {
  return readFileSync(join(workspace, "caffeine/Demo2020", TABLE), "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => line.split("\t"));
}

function cellOf(workspace: string, line: number, column: string): string {
  const rows = readTable(workspace);
  return rows[line - 1]?.[rows[0]!.indexOf(column)] ?? "";
}

/** Change a cell of the TSV table, as an editor saves it. */
function editTable(workspace: string, line: number, column: string, value: string): void {
  const rows = readTable(workspace);
  rows[line - 1]![rows[0]!.indexOf(column)] = value;
  writeFileSync(join(workspace, "caffeine/Demo2020", TABLE), rows.map((cells) => `${cells.join("\t")}\n`).join(""));
}

/** Change a cell of the workbook with openpyxl, as a spreadsheet program saves it. */
async function editWorkbook(workspace: string, line: number, column: string, value: string): Promise<void> {
  // The sheet has the rows and columns of the table: line 6 is row 6, the header is row 1.
  const cell = `${columnLetters(readTable(workspace)[0]!.indexOf(column))}${line}`;
  const workbook = join(workspace, "caffeine/Demo2020/Demo2020.xlsx");
  await runTool("edit_workbook.py", workbook, SHEET, cell, value);
}

/** The sync status of the study header, which starts with `text`; a chip, which has no role. */
function syncStatus(page: Page, text: string) {
  return page.locator(".fact-sync").filter({ hasText: text });
}

/** The sync text of the Data toolbar, a live region that explains a sync that is not clean. */
function syncText(page: Page, text: string) {
  return page.getByRole("status").filter({ hasText: text });
}

/** The cell of the grid at `line` that shows `value`. */
function gridCell(page: Page, line: number, value: string) {
  return page
    .getByRole("region", { name: `Rows of ${TABLE}` })
    .getByRole("row")
    .filter({ has: page.getByRole("rowheader", { name: String(line), exact: true }) })
    .getByRole("cell", { name: value, exact: true });
}

interface OverlayPoint {
  role: "raw" | "mapped";
  px: number;
  py: number;
  file: string;
  line: number | null;
}

interface SourceView {
  image_size: [number, number];
  overlay: OverlayPoint[];
}

/** The source view that the app draws, from the local API of the page's session. */
function sourceView(page: Page, source: string): Promise<SourceView> {
  return page.evaluate(
    async (url) => (await (await fetch(url)).json()) as SourceView,
    `/local/studies/caffeine/Demo2020/sources/${source}`,
  );
}

/** The button of a source or a table file in the navigator of the Data section. */
function navigatorButton(page: Page, name: RegExp) {
  return page.getByRole("navigation", { name: "Sources and tables" }).getByRole("button", { name });
}

/** Where the panes of the Data section end, how high they are, and how far the page scrolls. */
async function panesLayout(page: Page): Promise<{ bottom: number; height: number; scroll: number }> {
  const box = (await page.locator(".data-panes").boundingBox())!;
  const scroll = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
  return { bottom: Math.round(box.y + box.height), height: box.height, scroll };
}

/**
 * The alert `alert` above the panes of the Data section in a 1600 × 1000 window keeps the height
 * of its text, and the panes, which were `panes` px high without it, give it just that room and
 * a gap: they still end at the padding of 8 px below the study page, which does not scroll.
 */
async function expectAlertAbovePanes(page: Page, alert: Locator, panes: number): Promise<void> {
  await expect(alert).toBeVisible();
  const { height } = (await alert.boundingBox())!;
  expect(height).toBeLessThan(80);
  const layout = await panesLayout(page);
  expect(layout).toMatchObject({ bottom: 992, scroll: 0 });
  expect(layout.height).toBeGreaterThanOrEqual(panes - height - 6);
}

test.describe("sources", () => {
  test.beforeEach(async ({ app }) => {
    await app.open("#/studies/caffeine/Demo2020/data");
  });

  test("the navigator lists each source in 40 px with its thumbnail and each table file in 24 px", async ({ page }) => {
    const height = async (name: RegExp) => (await navigatorButton(page, name).boundingBox())!.height;
    expect(await height(/^Fig1/)).toBe(40);
    expect(await height(/^Tab2/)).toBe(40);
    expect(await height(/^subjects\.tsv/)).toBe(24);
  });

  test("the Fig1 overlay shows the row of a mapped point and focuses it in the rows of the Data section", async ({ page }) => {
    await navigatorButton(page, /^Fig1/).click();
    const figure = page.getByRole("img", {
      name: /^Figure Fig1 with \d+ digitized points, \d+ digitized error bar ends and \d+ mapped rows/,
    });
    await expect(figure).toBeVisible();
    // Plotly keeps the traces that it drew on its element.
    await expect
      .poll(() => figure.evaluate((element) => (element as HTMLElement & { data?: unknown[] }).data?.length ?? 0))
      .toBeGreaterThan(0);
    await expect(page.getByRole("list", { name: "Series" })).toContainText("caf_plasma_100mg");

    // The misplaced point of line 6 has no digitized point near it, so the cross is alone there.
    const view = await sourceView(page, "Fig1");
    const point = view.overlay.find((entry) => entry.role === "mapped" && entry.line === 6);
    expect(point).toMatchObject({ file: "timecourses_Fig1.tsv" });
    const box = await figure.boundingBox();
    if (!point || !box) throw new Error("The overlay has no point of line 6");
    const [width, height] = view.image_size;
    const x = box.x + (point.px * box.width) / width;
    const y = box.y + (point.py * box.height) / height;
    await page.mouse.move(x, y);
    await expect(page.getByText("timecourses_Fig1.tsv line 6")).toBeVisible();

    await page.mouse.click(x, y);
    await expect(page.getByRole("heading", { name: "Data", level: 2 })).toBeVisible();
    await expect(navigatorButton(page, /^timecourses_Fig1\.tsv/)).toHaveAttribute("aria-current", "true");
    const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
    await expect(grid.getByRole("rowheader", { name: "6", exact: true })).toBeFocused();
  });

  test("the Tab2 source shows the table image, the raw extraction and the rows of its table", async ({ page }) => {
    await navigatorButton(page, /^Tab2/).click();
    await expect(page.getByRole("img", { name: "Tab2 of caffeine/Demo2020" })).toBeVisible();
    const raw = page.getByRole("region", { name: "Raw extraction Demo2020_Tab2.tsv" });
    await expect(raw.getByRole("cell", { name: "AUC0-inf (mg·h/l)" })).toBeVisible();
    await expect(raw.getByRole("cell", { name: "36.1 ± 8.5" })).toBeVisible();
    await expect(navigatorButton(page, /^outputs_Tab2\.tsv/)).toHaveAttribute("aria-current", "true");
    const rows = page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" });
    await expect(rows.getByRole("button", { name: "2", exact: true })).toBeVisible();
  });
});

test("the app bar, the study header and the section tabs take at most 110 px of a 1600 × 1000 window", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await app.open("#/studies/caffeine/Demo2020/data");
  const status = page.getByRole("combobox", { name: "Review status" });
  await expect(status).toBeVisible();
  const tabs = await page.getByRole("navigation", { name: "Study sections" }).boundingBox();
  expect(tabs!.y + tabs!.height).toBeLessThanOrEqual(110);
  // The field of the review status stays inside the header line, below the app bar.
  const field = await page.locator(".review-select .v-field").boundingBox();
  const bar = await page.getByRole("banner").first().boundingBox();
  expect(field!.y).toBeGreaterThanOrEqual(bar!.y + bar!.height + 4);
});

test("the Data section fills the window below the page above it, which does not scroll, also below a status banner", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  await expect(page.locator(".data-panes")).toBeVisible();
  // The panes end at the padding of 8 px below the study page.
  await expect.poll(() => panesLayout(page)).toMatchObject({ bottom: 992, scroll: 0 });
  // The state of the local server cannot be read: the status banner shows above the page.
  await page.route("**/local/state", (route) => route.fulfill({ json: {} }));
  await expect(page.getByText("The state of the local server could not be loaded.")).toBeVisible();
  await expect.poll(() => panesLayout(page)).toMatchObject({ bottom: 992, scroll: 0 });
});

test("the alert of a failed action of the Data section keeps the height of its text above the panes", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  await expect(page.locator(".data-panes")).toBeVisible();
  await expect.poll(() => panesLayout(page)).toMatchObject({ bottom: 992, scroll: 0 });
  const { height } = await panesLayout(page);
  const sync = page.getByRole("button", { name: "Sync", exact: true });
  const alerts = page.getByRole("alert");

  // The local server fails the sync.
  app.allowFailedRequest("/local/studies/tables", 500);
  await page.route("**/local/studies/tables", (route) =>
    route.fulfill({ status: 500, json: { error: "The workbook cannot be read." } }),
  );
  await sync.click();
  await expectAlertAbovePanes(page, alerts.filter({ hasText: "The workbook cannot be read." }), height);
  await page.getByRole("button", { name: "Close" }).click();
  await expect(alerts).toHaveCount(0);

  // The local server refuses the sync without a user: the hint offers the settings.
  app.allowFailedRequest("/local/studies/tables", 403);
  await page.unroute("**/local/studies/tables");
  await page.route("**/local/studies/tables", (route) =>
    route.fulfill({ status: 403, json: { error: "no_user", message: "Set your PK-DB user." } }),
  );
  await sync.click();
  await expectAlertAbovePanes(page, alerts.filter({ hasText: "Set your PK-DB user in Connection settings." }), height);
});

test("the alert of a study that cannot be loaded again keeps the height of its text above the Data section", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  await expect(page.locator(".data-panes")).toBeVisible();
  await expect.poll(() => panesLayout(page)).toMatchObject({ bottom: 992, scroll: 0 });
  const { height } = await panesLayout(page);
  // The next poll of the study gets an answer that the app cannot read; the page keeps the study.
  await page.route("**/local/studies/caffeine/Demo2020", (route) => route.fulfill({ json: {} }));
  await expectAlertAbovePanes(page, page.getByRole("alert").filter({ hasText: "The study could not be loaded." }), height);
  await expect(page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" })).toBeVisible();
});

test("the alerts of a source and a table that cannot be loaded keep the height of their text in their panes", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  // The local server answers the source and the table with what the app cannot read.
  await page.route("**/local/studies/caffeine/Demo2020/sources/**", (route) => route.fulfill({ json: {} }));
  await page.route("**/local/studies/caffeine/Demo2020/tables/**", (route) => route.fulfill({ json: {} }));
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  for (const name of ["Source Tab2", "Table outputs_Tab2.tsv"]) {
    const alert = page.getByRole("region", { name }).getByRole("alert");
    await expect(alert).toContainText("could not be loaded.");
    expect((await alert.boundingBox())!.height).toBeLessThan(80);
  }
});

test("on a phone the review status and More actions share a line above the buttons of the study", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await app.open("#/studies/caffeine/Demo2020/data");
  const top = async (name: string, role: "combobox" | "button") =>
    (await page.getByRole(role, { name, exact: true }).boundingBox())!.y;
  const status = await top("Review status", "combobox");
  const more = await top("More actions", "button");
  expect(Math.abs(more - status)).toBeLessThan(4);
  for (const button of ["Open tables", "Validate"]) expect(await top(button, "button")).toBeGreaterThan(status + 20);
});

test("the section tabs keep their places when another one becomes active and bold", async ({ app, page }) => {
  const navigation = page.getByRole("navigation", { name: "Study sections" });
  const tab = (name: string) => navigation.getByRole("link", { name, exact: true });
  const places = () =>
    navigation.getByRole("link").evaluateAll((links) => links.map((link) => link.getBoundingClientRect().left));
  await app.open("#/studies/caffeine/Demo2020/data");
  await expect(tab("Data")).toHaveAttribute("aria-current", "page");
  const onData = await places();
  await tab("Metadata").click();
  await expect(tab("Metadata")).toHaveAttribute("aria-current", "page");
  expect(await places()).toEqual(onData);
});

test("old addresses of the Sources and Tables sections open the Data section", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/tables?file=timecourses_Fig1.tsv&line=6");
  await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data\?file=timecourses_Fig1\.tsv&line=6$/);
  await expect(
    page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("rowheader", { name: "6", exact: true }),
  ).toBeFocused();
});

test("the separator moves with the keyboard and keeps its place after a reload", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data");
  const separator = page.getByRole("separator", { name: "Resize the source and the rows" });
  const before = Number(await separator.getAttribute("aria-valuenow"));
  await separator.focus();
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect(separator).toHaveAttribute("aria-valuenow", String(before + 4));
  await page.reload();
  await expect(page.getByRole("separator", { name: "Resize the source and the rows" })).toHaveAttribute(
    "aria-valuenow",
    String(before + 4),
  );
});

test("the separator follows the mouse from where it was grabbed and selects no text on the way", async ({ app, page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  await expect(page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" })).toBeVisible();
  const separator = page.getByRole("separator", { name: "Resize the source and the rows" });
  const before = Number(await separator.getAttribute("aria-valuenow"));
  const box = (await separator.boundingBox())!;
  // The share of the source pane is a whole percent of the split, which the separator moves by.
  const percent = (await page.locator(".data-split").boundingBox())!.width / 100;
  // Grabbed 1 px inside its end and moved across the rows, whose text a drag would select, by
  // 10.5 % less half the grab. The share rounds that to 10 %, which keeps the grabbed place under
  // the pointer as closely as whole percents can; a separator that put its start under the
  // pointer would move by the grab more, which rounds to 11 %.
  const grab = box.width - 1;
  const x = box.x + grab;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 10.5 * percent - grab / 2, y + 60, { steps: 12 });
  await page.mouse.up();
  await expect(separator).toHaveAttribute("aria-valuenow", String(before + 10));
  const after = (await separator.boundingBox())!;
  expect(Math.abs(after.x - (box.x + 10 * percent))).toBeLessThanOrEqual(1);
  expect(await page.evaluate(() => window.getSelection()?.toString() ?? "")).toBe("");
});

test("the pane heads keep the source and the count of rows whole while a pane is at its narrowest", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Fig1");
  const whole = (element: Element) => element.scrollWidth <= element.clientWidth;
  const name = page.locator(".source-pane .pane-head-name");
  const count = page.locator(".rows-pane .pane-head").getByText(/^\d+ rows$/);
  const separator = page.getByRole("separator", { name: "Resize the source and the rows" });
  await separator.focus();
  await page.keyboard.press("Home");
  await expect(name).toHaveText("Fig1");
  await expect.poll(() => name.evaluate(whole)).toBe(true);
  await page.keyboard.press("End");
  await expect(count).toBeVisible();
  await expect.poll(() => count.evaluate(whole)).toBe(true);
});

test("the Fit and 100 % buttons of the image are 24 px high inside the 26 px head of the source pane", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  const zoom = page.getByRole("group", { name: "Image size" });
  for (const name of ["Fit", "100 %"]) {
    const box = (await zoom.getByRole("button", { name, exact: true }).boundingBox())!;
    expect(box.height).toBeGreaterThanOrEqual(24);
  }
  const head = (await page.locator(".source-pane .pane-head").boundingBox())!;
  expect(head.height).toBe(26);
  const fit = (await zoom.getByRole("button", { name: "Fit", exact: true }).boundingBox())!;
  expect(fit.y).toBeGreaterThanOrEqual(head.y);
  expect(fit.y + fit.height).toBeLessThanOrEqual(head.y + head.height);
});

test("the ring of the selected line leaves room around its number in a row of 22 px", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv&line=6");
  const cell = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("rowheader", { name: "6", exact: true });
  await expect(cell).toBeFocused();
  const room = await cell.evaluate((element) => {
    const style = getComputedStyle(element);
    const box = element.getBoundingClientRect();
    // The outline is drawn inside the cell: its inner edge is the offset away from the border.
    const inset = -parseFloat(style.outlineOffset);
    const range = document.createRange();
    range.selectNodeContents(element);
    const text = range.getBoundingClientRect();
    return {
      ring: parseFloat(style.outlineWidth) <= inset,
      side: text.left - (box.left + inset),
      height: box.height - 2 * inset - parseFloat(style.fontSize),
    };
  });
  expect(room.ring).toBe(true);
  expect(room.side).toBeGreaterThanOrEqual(3);
  expect(room.height).toBeGreaterThanOrEqual(2);
});

test("the line buttons of the rows are one Tab stop, which the arrow keys move, and Enter selects a row", async ({
  app,
  page,
}) => {
  await app.open(`#/studies/caffeine/Demo2020/data?source=Fig1&file=${TABLE}`);
  const rows = page.getByRole("region", { name: `Rows of ${TABLE}` });
  await rows.focus();
  await page.keyboard.press("Tab");
  await expect(rows.getByRole("button", { name: "2", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  await expect(rows.getByRole("button", { name: "4", exact: true })).toBeFocused();
  await expect(page).not.toHaveURL(/line=/);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/line=4/);
  // Tab leaves the rows: the other line buttons are no Tab stops.
  await rows.getByRole("button", { name: "4", exact: true }).focus();
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.closest(".rows-scroll") === null)).toBe(true);
});

test("a clicked row of a figure rings its point", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv");
  await page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("button", { name: "6", exact: true }).click();
  await expect(page).toHaveURL(/line=6/);
  const figure = page.getByRole("img", { name: /^Figure Fig1/ });
  await expect
    .poll(() =>
      figure.evaluate((element) =>
        ((element as HTMLElement & { data?: { meta?: string }[] }).data ?? []).some((trace) => trace.meta === "selected"),
      ),
    )
    .toBe(true);
});

test.describe("tables", () => {
  test.beforeEach(async ({ app, page }) => {
    await app.open(`#/studies/caffeine/Demo2020/data?file=${TABLE}`);
    await expect(syncStatus(page, "In sync")).toBeVisible();
  });

  test("Open tables opens the workbook of the study", async ({ app, page }) => {
    await page.getByRole("button", { name: "Open tables" }).click();
    await expect(page.getByRole("status").filter({ hasText: "The workbook opened." })).toBeVisible();
    const workbook = join(app.server.workspace, "caffeine/Demo2020/Demo2020.xlsx");
    expect(readFileSync(app.server.openLog, "utf8").split("\n")).toContain(workbook);
  });

  test("a saved workbook updates the tables within the next polls", async ({ app, page }) => {
    await expect(gridCell(page, 6, "1.24")).toBeVisible();
    await editWorkbook(app.server.workspace, 6, "mean", "1.42");
    await expect(gridCell(page, 6, "1.42")).toBeVisible();
    expect(cellOf(app.server.workspace, 6, "mean")).toBe("1.42");
    await expect(syncStatus(page, "In sync")).toBeVisible();
  });

  test("a conflict between the workbook and the tables is resolved by keeping the workbook", async ({ app, page }) => {
    const workspace = app.server.workspace;
    // Both sides change line 7 before a sync runs.
    await setAutomaticActions(page, true);
    await editWorkbook(workspace, 7, "mean", "1.08");
    editTable(workspace, 7, "mean", "1.06");
    await setAutomaticActions(page, false);

    await expect(syncStatus(page, "Conflict")).toBeVisible();
    await expect(syncText(page, `Conflict in ${TABLE}`)).toBeVisible();
    const panel = page.getByRole("region", { name: "Conflicting rows" });
    const rows = panel.getByRole("region", { name: `Conflicting rows of ${TABLE}` });
    await expect(rows.getByRole("cell", { name: "1.08", exact: true })).toBeVisible();
    await expect(rows.getByRole("cell", { name: "1.06", exact: true })).toBeVisible();
    await panel.getByRole("button", { name: "Keep workbook" }).click();

    await expect(syncStatus(page, "In sync")).toBeVisible();
    await expect(panel).toBeHidden();
    await expect(gridCell(page, 7, "1.08")).toBeVisible();
    expect(cellOf(workspace, 7, "mean")).toBe("1.08");
  });

  test("Add table previews the new table on the local server while the curator types, then adds its sheet", async ({ page }) => {
    await page.getByRole("button", { name: "Add table", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Add table" });
    const source = dialog.getByRole("textbox", { name: "Source" });
    const add = dialog.getByRole("button", { name: "Add", exact: true });
    const preview = dialog.locator(".table-preview");

    // Typed key by key without a pause, the preview follows the last key.
    await source.pressSequentially("Tab2");
    await expect(dialog.getByText("outputs_Tab2.tsv already exists")).toBeVisible();
    await expect(preview).toBeHidden();
    await expect(add).toBeDisabled();
    await source.press("Backspace");
    await source.pressSequentially("3");
    await expect(preview).toContainText("outputs_Tab3.tsv");
    await expect(preview).toContainText("Demo2020_Tab3.png");
    await expect(add).toBeEnabled();

    await dialog.getByRole("radio", { name: "Raw table" }).check();
    await source.fill("Fig2");
    await expect(dialog.getByText("A raw table needs a paper table source such as Tab3")).toBeVisible();
    await expect(add).toBeDisabled();
    await source.fill("Tab3");
    await expect(preview).toContainText("Demo2020_Tab3.tsv");
    await add.click();

    await expect(dialog).toBeHidden();
    await expect(page.getByRole("status").filter({ hasText: "Added the sheet Demo2020_Tab3 to the workbook." })).toBeVisible();
  });
});
