import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
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

  const panel = pane.getByRole("region", { name: /^Notes of the subjects/ });
  const notes = (await panel.boundingBox())!;
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

  // The cut notes fade out at the bottom of their body until it scrolls to its end.
  const fade = panel.locator(".pane-more");
  await expect(fade).toBeVisible();
  await panel.locator(".table-notes-body").evaluate((body) => body.scrollTo(0, body.scrollHeight));
  await expect(fade).toBeHidden();
});

/** Three descriptions of several lines each, as the notes of a real study have them. */
const LONG_DESCRIPTIONS = [
  "In a preliminary trial six volunteers rinsed their mouths for 5 s with 2 ml of a solution that contained 400 mg of caffeine sodium salicylate. After spitting it out, they rinsed twice for 10 s with 25 ml of water each.",
  "In the first part of the study eight volunteers took 7 mg/kg of caffeine in soft gelatine capsules under standardized conditions. After the dose with 200 ml of water at body temperature, they rinsed their mouths, and a sample of saliva was taken as the blank value, to rule out absorption in the mouth and to check the abstinence from caffeine.",
  "In the second part of the study five volunteers received 220 mg of caffeine as caffeine sodium salicylate by intravenous injection.",
];

test("open notes take the room that the rows of a short table leave, and keep their cap above a long table", async ({
  app,
  page,
}) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    const notes = JSON.parse(original) as StudyJson;
    notes.notes = {
      ...notes.notes,
      interventions: { descriptions: LONG_DESCRIPTIONS, comments: [] },
      timecourses: { descriptions: LONG_DESCRIPTIONS, comments: [] },
    };
    writeFileSync(path, `${JSON.stringify(notes, null, 2)}\n`);
    const box = async (part: Locator) => (await part.boundingBox())!;
    const bottom = (rect: { y: number; height: number }) => rect.y + rect.height;

    // interventions.tsv has three rows: the notes show whole, with the rows below them.
    await app.open(`${STUDY}/data?file=interventions.tsv`);
    let pane = rowsPane(page, "interventions.tsv");
    await pane.getByRole("button", { name: /^Notes of the interventions 3 descriptions/ }).click();
    let panel = pane.getByRole("region", { name: /^Notes of the interventions/ });
    await expect(panel.getByRole("textbox", { name: "Description 3" })).toHaveValue(LONG_DESCRIPTIONS[2]!);
    let body = panel.locator(".table-notes-body");
    // Longer than the cap of the notes above a long table: 40 % of the window.
    expect(await body.evaluate((element) => element.scrollHeight)).toBeGreaterThan(0.4 * 900);
    await expect(panel.getByRole("button", { name: "Add comment on interventions" })).toBeInViewport();
    await expect(panel.locator(".pane-more")).toHaveCount(0);
    expect(await body.evaluate((element) => element.scrollHeight - element.clientHeight)).toBeLessThanOrEqual(1);
    const rows = pane.getByRole("region", { name: "Rows of interventions.tsv" });
    const [open, grid, section] = await Promise.all([panel, rows, pane].map(box));
    expect(bottom(open!)).toBeLessThanOrEqual(grid!.y);
    expect(bottom(grid!)).toBeLessThanOrEqual(bottom(section!));
    // The rows show whole: the last one ends inside their region.
    expect(bottom(await box(rows.getByRole("row").last()))).toBeLessThanOrEqual(bottom(grid!));

    // timecourses_Fig1.tsv needs the room for its rows: the same notes take at most 40 % of the
    // window, and scroll with a fade at their bottom.
    await app.open(`${STUDY}/data?file=timecourses_Fig1.tsv`);
    pane = rowsPane(page, "timecourses_Fig1.tsv");
    panel = pane.getByRole("region", { name: /^Notes of the timecourses/ });
    body = panel.locator(".table-notes-body");
    await pane.getByRole("button", { name: /^Notes of the timecourses 3 descriptions/ }).click();
    await expect(panel.locator(".pane-more")).toBeVisible();
    expect(Math.abs((await box(body)).height - 0.4 * 900)).toBeLessThanOrEqual(1);
  } finally {
    writeFileSync(path, original);
  }
});

test("the long notes of a kind without a table show whole in Metadata, which scrolls as a page", async ({ app, page }) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    // Demo2020 has no table of scatters: Metadata shows their notes.
    const notes = JSON.parse(original) as StudyJson;
    notes.notes = { ...notes.notes, scatters: { descriptions: LONG_DESCRIPTIONS, comments: [] } };
    writeFileSync(path, `${JSON.stringify(notes, null, 2)}\n`);
    await app.open(`${STUDY}/metadata`);
    const panel = page.getByRole("region", { name: /^Notes of the scatters/ });
    await panel.getByRole("button", { name: /^Notes of the scatters 3 descriptions/ }).click();
    await expect(panel.getByRole("textbox", { name: "Description 3" })).toHaveValue(LONG_DESCRIPTIONS[2]!);
    // Longer than 40 % of the window, the body still has no scroll of its own and no fade.
    const body = panel.locator(".table-notes-body");
    expect(await body.evaluate((element) => element.scrollHeight)).toBeGreaterThan(0.4 * 900);
    expect(await body.evaluate((element) => element.scrollHeight - element.clientHeight)).toBeLessThanOrEqual(1);
    await expect(panel.locator(".pane-more")).toHaveCount(0);
  } finally {
    writeFileSync(path, original);
  }
});

test("Show notes of a problem in the notes of the subjects opens them above subjects.tsv", async ({ app, page }) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    // A user name with a space makes study.json invalid at a field of the notes of the subjects.
    const broken = JSON.parse(original) as StudyJson;
    broken.notes!.subjects!.comments![0]!.user = "the curator";
    writeFileSync(path, `${JSON.stringify(broken, null, 2)}\n`);

    await app.open(`${STUDY}/problems`);
    const problem = page.getByRole("listitem").filter({ hasText: "notes.subjects.comments.0.user" });
    await expect(problem).toContainText("A user name has no spaces.");
    await problem.getByRole("link", { name: "Show notes" }).click();

    await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/data\?file=subjects\.tsv$/);
    const pane = rowsPane(page, "subjects.tsv");
    const toggle = pane.getByRole("button", { name: /^Notes of the subjects/ });
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveText("Notes of the subjects study.json is not valid");
    const notes = pane.getByRole("region", { name: /^Notes of the subjects/ });
    await expect(notes.getByRole("listitem")).toHaveText(["A user name has no spaces."]);
    await expect(notes.getByRole("link", { name: "Metadata" })).toBeVisible();
  } finally {
    writeFileSync(path, original);
  }
});
