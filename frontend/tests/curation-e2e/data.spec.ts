import { existsSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { columnLetters } from "../../src/curation-app/columns.ts";
import { expect, expectAccessible, runTool, setAutomaticActions, test } from "./fixtures.ts";

const TABLE = "timecourses_Fig1.tsv";
const SHEET = "timecourses_Fig1";

/** The cells of the TSV table of Demo2020 by line, the header being line 0. */
function readTable(workspace: string): string[][] {
  return readFileSync(join(workspace, "caffeine/Demo2020", TABLE), "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => line.split("\t"));
}

function cellOf(workspace: string, line: number, column: string): string {
  const rows = readTable(workspace);
  return rows[line]?.[rows[0]!.indexOf(column)] ?? "";
}

/** Change a cell of the TSV table, as an editor saves it. */
function editTable(workspace: string, line: number, column: string, value: string): void {
  const rows = readTable(workspace);
  rows[line]![rows[0]!.indexOf(column)] = value;
  writeFileSync(join(workspace, "caffeine/Demo2020", TABLE), rows.map((cells) => `${cells.join("\t")}\n`).join(""));
}

/** Change a cell of the workbook with openpyxl, as a spreadsheet program saves it. */
async function editWorkbook(workspace: string, line: number, column: string, value: string): Promise<void> {
  // The sheet has the rows and columns of the table: the header, line 0, is row 1, so line 5 is row 6.
  const cell = `${columnLetters(readTable(workspace)[0]!.indexOf(column))}${line + 1}`;
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
  return page.getByRole("navigation", { name: "Tables and sources" }).getByRole("button", { name });
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

  test("the navigator lists the tables by class of information, then the sources", async ({ page }) => {
    const navigator = page.getByRole("navigation", { name: "Tables and sources" });
    await expect(navigator.getByRole("heading")).toHaveText(["Tables", "Subjects", "Interventions", "Data", "Raw extractions", "Sources"]);
    const names = (group: string) => navigator.getByRole("list", { name: group, exact: true }).locator(".nav-file-name");
    await expect(names("Subjects")).toHaveText(["subjects.tsv", "characteristica.tsv"]);
    await expect(names("Interventions")).toHaveText(["interventions.tsv"]);
    await expect(names("Data")).toHaveText(["outputs_Tab2.tsv", "timecourses_Fig1.tsv"]);
    await expect(names("Raw extractions")).toHaveText(["Demo2020_Tab2.tsv"]);
    await expect(navigator.getByRole("list", { name: "Sources", exact: true }).locator(".nav-name")).toHaveText(["Paper", "Fig1", "Tab2", "Text"]);
    await expect(navigatorButton(page, /^timecourses_Fig1\.tsv/).locator(".nav-rows")).toHaveAttribute("title", "18 rows");
    await expect(navigatorButton(page, /^subjects\.tsv/).locator(".nav-bar")).toHaveCSS("background-color", "rgb(29, 95, 184)");
    await expect(navigatorButton(page, /^timecourses_Fig1\.tsv/).locator(".nav-bar")).toHaveCSS("background-color", "rgb(106, 63, 181)");
  });

  test("below 1100 px the Table select lists the tables under the headings of their class, in a menu that the keyboard reaches", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1000, height: 800 });
    await page.locator(".data-select--table .v-field").click();
    const menu = page.getByRole("listbox");
    await expect(menu.locator(".v-list-subheader")).toHaveText(["Subjects", "Interventions", "Data", "Raw extractions"]);
    await expect(menu.getByRole("option")).toHaveText([
      "subjects.tsv",
      "characteristica.tsv",
      "interventions.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Demo2020_Tab2.tsv",
    ]);
    await expect(menu.getByRole("option", { name: "subjects.tsv" }).locator(".data-option-dot")).toHaveCSS(
      "background-color",
      "rgb(29, 95, 184)",
    );
    // The menu scrolls when the tables do not fit, so the keyboard must reach it.
    await expectAccessible(page);
    await menu.getByRole("option", { name: "timecourses_Fig1.tsv" }).click();
    await expect(page).toHaveURL(/file=timecourses_Fig1\.tsv/);
  });

  test("the focus ring of an option of the Table menu lies inside the menu, in both themes", async ({ page }) => {
    await page.setViewportSize({ width: 1000, height: 800 });
    for (const scheme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.locator(".data-select--table .v-field").click();
      const menu = page.getByRole("listbox");
      await expect(menu).toBeVisible();
      await page.keyboard.press("ArrowDown");
      const option = menu.locator(".v-list-item:focus-visible");
      await expect(option).toHaveCount(1);
      const ring = await option.evaluate((element) => {
        const style = getComputedStyle(element);
        const reach = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
        const box = element.getBoundingClientRect();
        return { left: box.left - reach, right: box.right + reach };
      });
      const list = (await menu.boundingBox())!;
      expect(ring.left).toBeGreaterThanOrEqual(list.x);
      expect(ring.right).toBeLessThanOrEqual(list.x + list.width);
      await page.keyboard.press("Escape");
      await expect(menu).toBeHidden();
    }
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

    // The misplaced point of line 5 has no digitized point near it, so the cross is alone there.
    const view = await sourceView(page, "Fig1");
    const point = view.overlay.find((entry) => entry.role === "mapped" && entry.line === 5);
    expect(point).toMatchObject({ file: "timecourses_Fig1.tsv" });
    const box = await figure.boundingBox();
    if (!point || !box) throw new Error("The overlay has no point of line 5");
    const [width, height] = view.image_size;
    const x = box.x + (point.px * box.width) / width;
    const y = box.y + (point.py * box.height) / height;
    await page.mouse.move(x, y);
    await expect(page.getByText("timecourses_Fig1.tsv line 5")).toBeVisible();

    await page.mouse.click(x, y);
    await expect(page.getByRole("heading", { name: "Data", level: 2 })).toBeVisible();
    await expect(navigatorButton(page, /^timecourses_Fig1\.tsv/)).toHaveAttribute("aria-current", "true");
    const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
    await expect(grid.getByRole("rowheader", { name: "5", exact: true })).toBeFocused();
  });

  test("the Tab2 source shows the table image, the raw extraction and the rows of its table", async ({ page }) => {
    await navigatorButton(page, /^Tab2/).click();
    await expect(page.getByRole("img", { name: "Tab2 of caffeine/Demo2020" })).toBeVisible();
    const raw = page.getByRole("region", { name: "Raw extraction Demo2020_Tab2.tsv" });
    await expect(raw.getByRole("cell", { name: "AUC0-inf (mg·h/l)" })).toBeVisible();
    await expect(raw.getByRole("cell", { name: "36.1 ± 8.5" })).toBeVisible();
    await expect(navigatorButton(page, /^outputs_Tab2\.tsv/)).toHaveAttribute("aria-current", "true");
    const rows = page.getByRole("region", { name: "Rows of outputs_Tab2.tsv" });
    await expect(rows.getByRole("button", { name: "1", exact: true })).toBeVisible();
  });
});

test("the navigator shows the whole name of a table beside a warning, an open review item and its rows, all lined up", async ({
  app,
  page,
}) => {
  // An open review item about the table, beside the warning of its misplaced point.
  const file = join(app.server.workspace, "caffeine/Demo2020/review.json");
  const original = readFileSync(file, "utf8");
  const review = JSON.parse(original) as { items: object[] };
  review.items.push({
    id: "01M2Z8Q4KX0T9V3B6N1C5D7E2F",
    kind: "question",
    state: "open",
    target: { file: TABLE },
    text: "Are the times after the first or the second dose?",
    author: "demo-reviewer",
    created: "2026-09-20T09:00:00+02:00",
  });
  writeFileSync(file, `${JSON.stringify(review, null, 2)}\n`);
  try {
    await app.open("#/studies/caffeine/Demo2020/data");
    const entry = navigatorButton(page, /^timecourses_Fig1\.tsv/);
    await expect(entry.locator(".nav-count--warning")).toHaveAttribute("title", "1 warning");
    await expect(entry.locator(".nav-count:not(.nav-count--warning)")).toHaveAttribute("title", "1 open review item");
    await expect(entry.locator(".nav-rows")).toHaveAttribute("title", "18 rows");
    const name = entry.locator(".nav-name");
    await expect(name).toHaveText("timecourses_Fig1");
    expect(await name.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
    // The drawn name keeps 8 px from the warning after it, twice the space between the badges.
    const apart = await entry.evaluate((element) => {
      const text = document.createRange();
      text.selectNodeContents(element.querySelector(".nav-name")!);
      return element.querySelector(".nav-count")!.getBoundingClientRect().left - text.getBoundingClientRect().right;
    });
    expect(apart).toBeGreaterThanOrEqual(8);
    // A pill of one or two digits has the width of two, so that the pills and the badges before them line up.
    const navigator = page.getByRole("navigation", { name: "Tables and sources" });
    const lefts = (selector: string) =>
      navigator.locator(selector).evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().left));
    expect(new Set(await lefts(".nav-file .nav-rows")).size).toBe(1);
    expect(new Set(await lefts(".nav-file .nav-count:not(.nav-count--error, .nav-count--warning)")).size).toBe(1);
    // A count of three digits (364 of the 1572 studies of pkdb_data have such a table) keeps the pill as wide.
    const widths = () =>
      navigator.locator(".nav-file .nav-rows").evaluateAll((elements) => elements.map((element) => element.getBoundingClientRect().width));
    const narrow = await widths();
    await navigator.locator(".nav-file .nav-rows").first().evaluate((element) => {
      element.textContent = "364";
    });
    const wide = await widths();
    expect(wide[0]).toBe(narrow[0]);
    expect(new Set(await lefts(".nav-file .nav-rows")).size).toBe(1);
  } finally {
    writeFileSync(file, original);
  }
});

test("the navigator takes the width of its longest name up to 320 px, beyond which the name ends with an ellipsis", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data");
  const navigator = page.getByRole("navigation", { name: "Tables and sources" });
  const width = async () => (await navigator.boundingBox())!.width;
  const entry = navigatorButton(page, /^timecourses_Fig1\.tsv/);
  const name = entry.locator(".nav-name");
  // At least 232 px, whatever font the machine draws the names in: with DejaVu Sans, the sans-serif
  // of the Linux runners of continuous integration, it is wider than with Noto Sans.
  await expect(entry.locator(".nav-count--warning")).toHaveAttribute("title", "1 warning");
  const short = await width();
  expect(short).toBeGreaterThanOrEqual(232);
  expect(short).toBeLessThan(320);
  await name.evaluate((element) => {
    element.textContent = "timecourses_Fig1_caffeine_paraxanthine_theophylline";
  });
  await expect.poll(width).toBe(320);
  expect(await name.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
  await expect(name).toHaveCSS("text-overflow", "ellipsis");
  await expect(name).toHaveAttribute("title", "timecourses_Fig1.tsv");
  // The warning and the rows keep their place at the end of the entry, inside the navigator.
  const rows = (await entry.locator(".nav-rows").boundingBox())!;
  const button = (await entry.boundingBox())!;
  expect(rows.x + rows.width).toBeLessThanOrEqual(button.x + button.width);
  await expect(entry.locator(".nav-count--warning")).toBeInViewport({ ratio: 1 });
});

test("subjects.tsv shows all of its rows when it is chosen, whichever source is selected", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data");
  await navigatorButton(page, /^subjects\.tsv/).click();
  // subjects.tsv of Demo2020 has one row, the group all, whose source is Text.
  const rows = page.getByRole("region", { name: "Rows of subjects.tsv" });
  await expect(rows.getByRole("rowheader", { name: "1", exact: true })).toBeVisible();
  await expect(rows.getByRole("cell", { name: "all", exact: true })).toBeVisible();
  await expect(page.getByText(/^No rows of /)).toHaveCount(0);
});

test("the Source filter of a shared table keeps its choice per table while the study is open", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=characteristica.tsv");
  const filter = page.getByRole("combobox", { name: "Source of the rows" });
  await expect(filter).toHaveValue("all");
  await expect(filter.locator("option")).toHaveText(["All (6)", "Text (6)", "No source (0)"]);
  await filter.selectOption({ label: "No source (0)" });
  await expect(page.getByText("Every row of characteristica.tsv names a source.")).toBeVisible();
  // Another shared table has a filter of its own, and a table of one source none.
  await navigatorButton(page, /^subjects\.tsv/).click();
  await expect(filter).toHaveValue("all");
  await navigatorButton(page, /^outputs_Tab2\.tsv/).click();
  await expect(filter).toHaveCount(0);
  // The choice survives other sections of the study.
  const tabs = page.getByRole("navigation", { name: "Study sections" });
  await tabs.getByRole("link", { name: /^Metadata\b/ }).click();
  await tabs.getByRole("link", { name: /^Data\b/ }).click();
  await navigatorButton(page, /^characteristica\.tsv/).click();
  await expect(filter).toHaveValue("none");
  await page.getByRole("button", { name: "Show all rows" }).click();
  await expect(filter).toHaveValue("all");
  // The header row and the six rows.
  await expect(page.getByRole("region", { name: "Rows of characteristica.tsv" }).getByRole("row")).toHaveCount(7);
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

test("in a stacked window the source pane fits a short image, up to 70 % of the window", async ({ app, page }) => {
  await page.setViewportSize({ width: 700, height: 900 });
  await app.open("#/studies/caffeine/Demo2020/data?source=Tab2");
  const pane = page.locator(".data-stack > .source-pane");
  await expect(pane.locator(".source-image")).toBeVisible();
  const body = pane.locator(".pane-body");
  const sizes = await body.evaluate((element) => ({ client: element.clientHeight, scroll: element.scrollHeight }));
  // Nothing scrolls and nothing is left empty below the content of the pane.
  expect(sizes.scroll - sizes.client).toBeLessThanOrEqual(1);
  const free = await body.evaluate((element) => {
    const last = element.querySelector(".pane-content")!.getBoundingClientRect().bottom;
    return element.getBoundingClientRect().bottom - last;
  });
  expect(free, "empty space below the content of the pane").toBeLessThanOrEqual(24);
  expect((await pane.boundingBox())!.height).toBeLessThan(0.7 * 900);
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
  await app.open("#/studies/caffeine/Demo2020/tables?file=timecourses_Fig1.tsv&line=5");
  await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data\?file=timecourses_Fig1\.tsv&line=5$/);
  await expect(
    page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("rowheader", { name: "5", exact: true }),
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

test("the head of the rows pane shows its kind, count, Source select and notes without cutting a word, also at its narrowest", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data?file=interventions.tsv");
  const pane = page.getByRole("region", { name: "Table interventions.tsv" });
  await expect(pane.getByRole("combobox", { name: "Source of the rows" })).toBeVisible();
  await expect(pane.getByText("1 problem is outlined.", { exact: true })).toBeVisible();
  // What the head and its notes cut or clip, apart from the file name, which may end in an ellipsis in a narrow pane.
  const cut = () =>
    pane.evaluate((section) => {
      const box = section.getBoundingClientRect();
      const parts = ".pane-head-name, .pane-head-kind, .pane-head-part, .pane-head-filter, .pane-head-line, .rows-pane-notes > *";
      return [...section.querySelectorAll<HTMLElement>(parts)]
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          const clipped = rect.left < box.left || rect.right > box.right;
          const name = element.classList.contains("pane-head-name");
          return clipped || (!name && element.scrollWidth > element.clientWidth);
        })
        .map((element) => element.textContent?.trim());
    });
  expect(await cut()).toEqual([]);
  await expect(pane.locator(".pane-head-kind")).toHaveText("Interventions");
  // Where it has room, the head is one line of 26 px, as the head of the source pane beside it.
  expect((await pane.locator(".pane-head").boundingBox())!.height).toBe(26);
  const separator = page.getByRole("separator", { name: "Resize the source and the rows" });
  await separator.focus();
  await page.keyboard.press("End");
  await expect.poll(() => pane.evaluate((section) => section.getBoundingClientRect().width)).toBeLessThan(300);
  expect(await cut()).toEqual([]);
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

test("the focus ring of the Source select lies inside the head of the rows pane, in both themes", async ({ app, page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    await app.open("#/studies/caffeine/Demo2020/data?file=subjects.tsv");
    const select = page.getByRole("combobox", { name: "Source of the rows" });
    await select.focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    await expect(select).toBeFocused();
    const ring = await select.evaluate((element) => {
      const style = getComputedStyle(element);
      const reach = parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth);
      const box = element.getBoundingClientRect();
      return { top: box.top - reach, bottom: box.bottom + reach, left: box.left - reach, right: box.right + reach };
    });
    const head = (await page.locator(".rows-pane > .pane-head").boundingBox())!;
    expect(ring.top).toBeGreaterThanOrEqual(head.y);
    expect(ring.bottom).toBeLessThanOrEqual(head.y + head.height);
    expect(ring.left).toBeGreaterThanOrEqual(head.x);
    expect(ring.right).toBeLessThanOrEqual(head.x + head.width);
  }
});

test("the source pane shows that more of it follows below, and scrolls to its end", async ({ app, page }) => {
  // Without its WebPlotDigitizer project Fig1 shows the note "No digitization" at the end of the
  // pane; in a short window (the section keeps its least height of 480 px) the pane is taller than its view.
  const project = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Fig1.wpd.json");
  renameSync(project, `${project}.away`);
  try {
    await page.setViewportSize({ width: 1440, height: 640 });
    await app.open("#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv");
    const pane = page.getByRole("region", { name: "Source Fig1" });
    const body = pane.locator(".pane-body");
    await expect(pane.getByText("No digitization:")).toBeAttached();
    await expect(pane.locator(".pane-more")).toBeVisible();
    // The problems of the study may still arrive after the first scroll and lengthen the pane: scroll again.
    await expect(async () => {
      await body.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
      await expect(pane.locator(".pane-more")).toBeHidden({ timeout: 500 });
      const last = (await pane.locator(".pane-content > *").last().boundingBox())!;
      const view = (await body.boundingBox())!;
      expect(last.y + last.height).toBeLessThanOrEqual(view.y + view.height);
    }).toPass();
    await expect(pane.getByText("No digitization:")).toBeInViewport({ ratio: 1 });
  } finally {
    renameSync(`${project}.away`, project);
  }
});

test("the ring of the selected line leaves room around its number in a row of 22 px", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv&line=5");
  const cell = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("rowheader", { name: "5", exact: true });
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
  await expect(rows.getByRole("button", { name: "1", exact: true })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  await expect(rows.getByRole("button", { name: "3", exact: true })).toBeFocused();
  await expect(page).not.toHaveURL(/line=/);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/line=3/);
  // Tab leaves the rows: the other line buttons are no Tab stops.
  await rows.getByRole("button", { name: "3", exact: true }).focus();
  await page.keyboard.press("Tab");
  expect(await page.evaluate(() => document.activeElement?.closest(".rows-scroll") === null)).toBe(true);
});

test("a clicked row of a figure rings its point", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=Fig1&file=timecourses_Fig1.tsv");
  await page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" }).getByRole("button", { name: "5", exact: true }).click();
  await expect(page).toHaveURL(/line=5/);
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
    await expect
      .poll(() => (existsSync(app.server.openLog) ? readFileSync(app.server.openLog, "utf8").split("\n") : []))
      .toContain(workbook);
  });

  test("a saved workbook updates the tables within the next polls", async ({ app, page }) => {
    await expect(gridCell(page, 5, "1.24")).toBeVisible();
    await editWorkbook(app.server.workspace, 5, "mean", "1.42");
    await expect(gridCell(page, 5, "1.42")).toBeVisible();
    expect(cellOf(app.server.workspace, 5, "mean")).toBe("1.42");
    await expect(syncStatus(page, "In sync")).toBeVisible();
  });

  test("a conflict between the workbook and the tables is resolved by keeping the workbook", async ({ app, page }) => {
    const workspace = app.server.workspace;
    // Both sides change line 6 before a sync runs.
    await setAutomaticActions(page, true);
    await editWorkbook(workspace, 6, "mean", "1.08");
    editTable(workspace, 6, "mean", "1.06");
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
    await expect(gridCell(page, 6, "1.08")).toBeVisible();
    expect(cellOf(workspace, 6, "mean")).toBe("1.08");
  });

  test("the conflicts keep their room above the open notes, and in a short window scroll with a fade and leave rows in view", async ({
    app,
    page,
  }) => {
    const workspace = app.server.workspace;
    await app.open("#/studies/caffeine/Demo2020/data?file=subjects.tsv");
    // Both sides change line 7 of the timecourses before a sync runs.
    await setAutomaticActions(page, true);
    await editWorkbook(workspace, 7, "mean", "0.91");
    editTable(workspace, 7, "mean", "0.92");
    await setAutomaticActions(page, false);
    const panel = page.getByRole("region", { name: "Conflicting rows", exact: true });
    await expect(panel).toBeVisible();
    const pane = page.getByRole("region", { name: "Table subjects.tsv", exact: true });
    const toggle = pane.getByRole("button", { name: /^Notes of the subjects/ });
    const notes = pane.getByRole("region", { name: /^Notes of the subjects/ });
    await toggle.click();
    // An unsaved edit turns the banner above the panes amber.
    await notes.getByRole("textbox", { name: "Description 1" }).fill("Edited.");
    await expect(page.locator(".unsaved-banner")).toContainText("Unsaved changes to study.json: Notes of the subjects");
    const box = async (part: Locator) => (await part.boundingBox())!;
    const bottom = (rect: { y: number; height: number }) => rect.y + rect.height;

    // In a window of 1440 x 900 px the notes give up their room first: the conflicts show whole.
    const lastVersion = panel.getByRole("row").last();
    await expect(lastVersion).toContainText("Tables line 7");
    expect(bottom(await box(lastVersion))).toBeLessThanOrEqual(bottom(await box(panel)));
    await expect(panel.locator(".pane-more")).toHaveCount(0);
    await expect(notes.locator(".pane-more")).toBeVisible();

    // In a short window the notes keep their header, and the conflicts scroll and fade out at their bottom.
    await page.setViewportSize({ width: 1366, height: 560 });
    await expect(panel.locator(".pane-more")).toBeVisible();
    const rows = pane.getByRole("region", { name: "Rows of subjects.tsv", exact: true });
    const [conflicts, open, head, grid, header, row, section] = await Promise.all(
      [panel, notes, toggle, rows, rows.getByRole("row").first(), rows.getByRole("row").last(), pane].map(box),
    );
    expect(bottom(conflicts!)).toBeLessThanOrEqual(open!.y);
    // The header of the notes stays whole above their body.
    expect(bottom(head!)).toBeLessThanOrEqual(bottom(open!));
    expect(bottom(open!)).toBeLessThanOrEqual(grid!.y);
    expect(bottom(grid!)).toBeLessThanOrEqual(bottom(section!));
    // The rows keep their header and their one row in view (a longer table keeps four rows, notes.spec.ts).
    expect(grid!.height).toBeGreaterThanOrEqual(2 * header!.height);
    expect(bottom(row!)).toBeLessThanOrEqual(bottom(grid!));

    // Keeping the workbook leaves the tables in sync for the next test.
    await panel.getByRole("button", { name: "Keep workbook" }).click();
    await expect(syncStatus(page, "In sync")).toBeVisible();
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
