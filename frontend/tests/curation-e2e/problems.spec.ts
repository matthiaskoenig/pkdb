import { existsSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, expectAccessible, runTool, test } from "./fixtures.ts";

interface ReviewJson {
  items: { state: string; acknowledges?: string; text: string; target?: object }[];
}

const REASON = "D400 was planned, but the study reports no results for it.";
const WORKBOOK = "caffeine/Demo2020/Demo2020.xlsx";

/** The lines of the open log, none before the first open. */
function openedPaths(log: string): string[] {
  return existsSync(log) ? readFileSync(log, "utf8").split("\n") : [];
}

function problem(page: Page, code: string) {
  return page.getByRole("listitem").filter({ has: page.getByText(code, { exact: true }) });
}

test.beforeEach(async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/problems");
  // The first validation of the study lists its warnings.
  await expect(problem(page, "digitized_mismatch")).toBeVisible();
});

test("acknowledges a warning with a reason, which a resolved review item keeps", async ({ app, page }) => {
  const severity = page.getByRole("group", { name: "Filter by severity" });
  await expect(severity).toContainText("Warnings2");
  const warning = problem(page, "unused_intervention");
  await expect(warning).toContainText("'D400' is not referenced by any row");
  await warning.getByRole("button", { name: "Acknowledge" }).click();
  const dialog = page.getByRole("dialog", { name: "Acknowledge warning" });
  await expect(dialog).toContainText("unused_intervention");
  await dialog.getByRole("textbox", { name: "Reason" }).fill(REASON);
  await dialog.getByRole("button", { name: "Acknowledge" }).click();
  await expect(dialog).toBeHidden();

  // The next validation moves the warning to the acknowledged ones.
  const acknowledged = page.getByRole("region", { name: "Acknowledged warnings (1)" });
  await expect(acknowledged).toContainText("unused_intervention");
  await expect(acknowledged).toContainText("interventions.tsv · name = D400 · column name");
  await expect(acknowledged).toContainText(REASON);
  await expect(acknowledged).toContainText("Acknowledged by curator on");
  // Only the acknowledged list names it.
  await expect(problem(page, "unused_intervention")).toHaveCount(1);
  await expect(severity).toContainText("Warnings1");

  const review = JSON.parse(
    readFileSync(join(app.server.workspace, "caffeine/Demo2020/review.json"), "utf8"),
  ) as ReviewJson;
  expect(review.items.filter((item) => item.acknowledges === "unused_intervention")).toEqual([
    expect.objectContaining({
      state: "resolved",
      text: REASON,
      target: { file: "interventions.tsv", rows: { name: "D400" }, column: "name" },
    }),
  ]);
  await acknowledged.getByRole("link", { name: "Show the review item" }).click();
  await expect(page.getByRole("article", { name: "Issue" })).toContainText(REASON);
});

test("Show in table opens the Data section with the cell of the problem focused", async ({ page }) => {
  const mismatch = problem(page, "digitized_mismatch");
  await expect(mismatch).toContainText("mean 1.24 at 4 hr lies");
  await mismatch.getByRole("link", { name: "Show in table" }).click();
  await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data\?/);
  await expect(
    page.getByRole("navigation", { name: "Tables and sources" }).getByRole("button", { name: /^timecourses_Fig1\.tsv/ }),
  ).toHaveAttribute("aria-current", "true");
  const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(grid.getByRole("cell", { name: "1.24", exact: true })).toBeFocused();
});

test("a problem names its line, counted from the header line 0, and its workbook cell (#938)", async ({ page }) => {
  const mismatch = problem(page, "digitized_mismatch");
  // The misplaced mean is entry 5 of timecourses_Fig1.tsv, in row 6 of its sheet.
  await expect(mismatch).toContainText("line 5 · mean · workbook cell O6");
  await mismatch.getByRole("link", { name: "Show in table" }).click();
  await expect(page).toHaveURL(/[?&]line=5(&|$)/);
  const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(grid.getByRole("columnheader", { name: "Line 0", exact: true })).toBeVisible();
  await expect(grid.getByRole("rowheader", { name: "1", exact: true })).toBeVisible();
});

test("Open in tables opens the workbook at the sheet and the cell of the problem", async ({ app, page }) => {
  await problem(page, "digitized_mismatch").getByRole("button", { name: "Open in tables" }).click();
  await expect(page.getByRole("status").filter({ hasText: "The workbook opened." })).toBeVisible();
  const workbook = join(app.server.workspace, WORKBOOK);
  await expect.poll(() => openedPaths(app.server.openLog)).toContain(workbook);
  // The mean 1.24 at 4 hr: the column mean and the row of its line in timecourses_Fig1.
  expect(await runTool("workbook_view.py", workbook)).toBe("timecourses_Fig1!O6\n");
});

test("Open in tables of an open workbook names the sheet to go to", async ({ app, page }) => {
  // A place that no earlier open selected, so that unchanged bytes show the lock path.
  const workbook = join(app.server.workspace, WORKBOOK);
  const lock = join(app.server.workspace, "caffeine/Demo2020/.~lock.Demo2020.xlsx#");
  const raw = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Tab2.tsv");
  const original = readFileSync(raw, "utf8");
  try {
    writeFileSync(raw, `<<<<<<< HEAD\n${original}`);
    await page.getByRole("button", { name: "Validate" }).click();
    const conflict = problem(page, "merge_conflict");
    await expect(conflict).toBeVisible();
    const before = readFileSync(workbook);
    writeFileSync(lock, "curator");
    await conflict.getByRole("button", { name: "Open in tables" }).click();
    const notice = page
      .getByRole("status")
      .filter({ hasText: "The workbook is already open. Go to sheet Demo2020_Tab2." });
    await expect(notice).toBeVisible();
    expect(readFileSync(workbook).equals(before)).toBe(true);
    await expectAccessible(page);
    await page.emulateMedia({ colorScheme: "dark" });
    await expect(notice).toBeVisible();
    await expectAccessible(page);
  } finally {
    rmSync(lock, { force: true });
    writeFileSync(raw, original);
  }
});

test("Open in tables of a problem of a raw table opens the workbook at the sheet of the raw table", async ({ app, page }) => {
  const raw = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Tab2.tsv");
  const original = readFileSync(raw, "utf8");
  try {
    writeFileSync(raw, `<<<<<<< HEAD\n${original}`);
    await page.getByRole("button", { name: "Validate" }).click();
    const conflict = problem(page, "merge_conflict");
    await expect(conflict).toBeVisible();
    await conflict.getByRole("button", { name: "Open in tables" }).click();
    await expect(page.getByRole("status").filter({ hasText: "The workbook opened." })).toBeVisible();
    const workbook = join(app.server.workspace, WORKBOOK);
    expect(await runTool("workbook_view.py", workbook)).toBe("Demo2020_Tab2!A1\n");
  } finally {
    writeFileSync(raw, original);
  }
});
