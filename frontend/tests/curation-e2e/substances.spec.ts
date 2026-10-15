import { cpSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

/** The watcher reads changed tables after its next scan; it does so well within this time. */
const VALIDATED_MS = 30_000;

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

/**
 * Copy caffeine/Draft2021, whose dosing is of caffeine, to midazolam/Draft2021, and give
 * caffeine/Draft2021 a dosing of midazolam, as aliskiren/Nussberger2002 names enalapril. The
 * tests of this file share the workspace, so a second call changes nothing.
 */
function addMidazolam(workspace: string): void {
  const copy = join(workspace, "midazolam", "Draft2021");
  if (existsSync(copy)) return;
  cpSync(join(workspace, "caffeine", "Draft2021"), copy, { recursive: true });
  const path = join(workspace, "caffeine", "Draft2021", "interventions.tsv");
  const [header = "", first = "", ...rest] = readFileSync(path, "utf8").split("\n");
  const columns = header.split("\t");
  const cells = first.split("\t");
  const name = columns.indexOf("name");
  const substance = columns.indexOf("substance");
  if (name < 0 || substance < 0) {
    throw new Error(`interventions.tsv of Draft2021 has no name or substance column: ${header}`);
  }
  cells[name] = "D300";
  cells[substance] = "midazolam";
  writeFileSync(path, [header, first, cells.join("\t"), ...rest].join("\n"));
}

async function chooseSubstance(page: Page, name: string): Promise<void> {
  // The selection text covers the input, so the menu is opened from the keyboard.
  const select = page.getByRole("combobox", { name: "Substance" });
  await select.focus();
  await select.press("ArrowDown");
  await page.getByRole("option", { name, exact: true }).click();
}

for (const theme of ["light", "dark"] as const) {
  test(`finds a study under every substance folder that its tables name, in the ${theme} theme`, async ({
    app,
    page,
  }) => {
    test.setTimeout(120_000);
    addMidazolam(app.server.workspace);
    await page.emulateMedia({ colorScheme: theme });
    await app.open();
    await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
    await expect(studyRow(page, "midazolam/Draft2021")).toBeVisible({ timeout: VALIDATED_MS });

    await chooseSubstance(page, "midazolam");
    // The watcher reads the changed tables; until then a study is found under its folder only.
    await expect(studyRows(page)).toHaveCount(2, { timeout: VALIDATED_MS });
    await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
    await expect(studyRow(page, "midazolam/Draft2021")).toBeVisible();

    // The copy keeps the dosing of caffeine.
    await chooseSubstance(page, "caffeine");
    await expect(studyRows(page)).toHaveCount(3, { timeout: VALIDATED_MS });

    await studyRow(page, "caffeine/Draft2021").getByRole("link", { name: "caffeine/Draft2021" }).hover();
    const tooltip = page.getByRole("tooltip");
    await expect(tooltip).toHaveText(/^\s*caffeine\/Draft2021\s*\+ midazolam\s*$/);
    // Once it faded in: the transition starts a frame after the text shows, so that an
    // earlier check could measure the contrast of the half transparent tooltip.
    await expect(tooltip).toHaveCSS("opacity", "1");
    await expectAccessible(page);
  });
}
