import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";
/** The first description and the comment of the notes of the subjects in study.json of the fixture. */
const DESCRIPTION = "Healthy adult volunteers who abstained from caffeine for 48 hours before the study day.";
const COMMENT = "The paper gives no sex distribution of the group.";
const EDITED = "Healthy adult volunteers who abstained from caffeine for 72 hours before the study day.";

interface Notes {
  descriptions?: string[];
  comments?: { user: string; text: string }[];
}

interface StudyJson {
  notes?: Record<string, Notes>;
  [key: string]: unknown;
}

/** The path of study.json of Demo2020 in the workspace of the server. */
function studyJsonPath(workspace: string): string {
  return join(workspace, "caffeine/Demo2020/study.json");
}

/** study.json of Demo2020 as it is on disk. */
function studyJsonOnDisk(workspace: string): StudyJson {
  return JSON.parse(readFileSync(studyJsonPath(workspace), "utf8")) as StudyJson;
}

/**
 * The tab of a section, named with what screen readers hear after its label, such as "Data, unsaved changes".
 * Chromium puts a space before the comma that starts the part only screen readers hear, which they do not
 * pronounce, so the name matches with and without it.
 */
function sectionTab(page: Page, name: string) {
  const words = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replaceAll(",", " ?,");
  return page.getByRole("navigation", { name: "Study sections" }).getByRole("link", { name: new RegExp(`^${words}$`) });
}

/** The rows pane of the table `file` in the Data section. */
function rowsPane(page: Page, file: string) {
  return page.getByRole("region", { name: `Table ${file}`, exact: true });
}

test("the notes of the subjects show above subjects.tsv in the Data section", async ({ app, page }) => {
  await app.open(`${STUDY}/data?file=subjects.tsv`);
  const pane = rowsPane(page, "subjects.tsv");
  await expect(pane.getByRole("region", { name: "Rows of subjects.tsv" })).toBeVisible();
  const toggle = pane.getByRole("button", { name: /^Notes of the subjects/ });
  await expect(toggle).toHaveText("Notes of the subjects 2 descriptions · 1 comment");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(pane.getByRole("textbox", { name: "Description 1" })).toHaveValue(DESCRIPTION);
  await expect(pane.getByRole("textbox", { name: "Comment 1 by curator" })).toHaveValue(COMMENT);
});

test("edits a description of the subjects in Data and saves it from Metadata", async ({ app, page }) => {
  // The tests of a file share the workspace: study.json goes back to the fixture afterwards.
  const original = readFileSync(studyJsonPath(app.server.workspace), "utf8");
  try {
    const before = studyJsonOnDisk(app.server.workspace);
    await app.open(`${STUDY}/data?file=subjects.tsv`);
    const pane = rowsPane(page, "subjects.tsv");
    await pane.getByRole("button", { name: /^Notes of the subjects/ }).click();
    await pane.getByRole("textbox", { name: "Description 1" }).fill(EDITED);

    const bar = page.locator(".study-savebar");
    await expect(bar).toContainText("Unsaved changes in study.json");
    await expect(sectionTab(page, "Data, unsaved changes")).toBeVisible();
    await expect(sectionTab(page, "Metadata")).toBeVisible();
    // The panes keep filling the window with the bar below them: the page does not scroll.
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollHeight - document.documentElement.clientHeight))
      .toBe(0);

    // Metadata shows the same draft and the same bar, without asking to leave.
    await sectionTab(page, "Metadata").click();
    await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/metadata$/);
    await expect(bar).toContainText("Unsaved changes in study.json");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(bar).toContainText("study.json saved.");
    await expect(sectionTab(page, "Data")).toBeVisible();

    // Only the first description of the subjects changed on disk.
    const expected = structuredClone(before);
    expected.notes!.subjects!.descriptions![0] = EDITED;
    await expect.poll(() => studyJsonOnDisk(app.server.workspace)).toEqual(expected);
  } finally {
    writeFileSync(studyJsonPath(app.server.workspace), original);
  }
});

test("open notes leave rows of the table in view in a short window, with the save bar below the panes", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 600 });
  await app.open(`${STUDY}/data?file=subjects.tsv`);
  const pane = rowsPane(page, "subjects.tsv");
  await pane.getByRole("button", { name: /^Notes of the subjects/ }).click();
  await pane.getByRole("textbox", { name: "Description 1" }).fill(EDITED);
  const bar = page.locator(".study-savebar");
  await expect(bar).toContainText("Unsaved changes in study.json");

  const notes = (await pane.getByRole("region", { name: /^Notes of the subjects/ }).boundingBox())!;
  const rows = pane.getByRole("region", { name: "Rows of subjects.tsv" });
  const grid = (await rows.boundingBox())!;
  const header = (await rows.getByRole("row").first().boundingBox())!;
  const section = (await pane.boundingBox())!;
  // The notes scroll on their own rather than push the rows out of the pane, which keeps their header and four rows.
  expect(notes.y + notes.height).toBeLessThanOrEqual(grid.y);
  expect(grid.y + grid.height).toBeLessThanOrEqual(section.y + section.height);
  expect(grid.height).toBeGreaterThanOrEqual(5 * header.height);
  // The bar ends the section below the panes rather than cover them.
  expect((await bar.boundingBox())!.y).toBeGreaterThanOrEqual(section.y + section.height);
});
