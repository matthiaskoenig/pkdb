import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
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

/** The sync alert of the section, which starts with `text`; a summary of the last sync may follow. */
function syncStatus(page: Page, text: string) {
  const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page.getByRole("status").filter({ hasText: new RegExp(`^\\s*${escaped}`) });
}

/** The cell of the grid at `line` that shows `value`. */
function gridCell(page: Page, line: number, value: string) {
  return page
    .getByRole("region", { name: `Rows of ${TABLE}` })
    .getByRole("row")
    .filter({ has: page.getByRole("rowheader", { name: String(line), exact: true }) })
    .getByRole("cell", { name: value, exact: true });
}

test.beforeEach(async ({ app, page }) => {
  await app.open(`#/studies/caffeine/Demo2020/tables?file=${TABLE}`);
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

  await expect(syncStatus(page, `Conflict in ${TABLE}`)).toBeVisible();
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
