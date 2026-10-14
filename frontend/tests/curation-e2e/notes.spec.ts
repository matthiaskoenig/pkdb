import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, expectAccessible, test } from "./fixtures.ts";

const STUDY = "#/studies/caffeine/Demo2020";
/** The first description and the comment of the notes of the subjects in study.json of the fixture. */
const DESCRIPTION = "Healthy adult volunteers who abstained from caffeine for 48 hours before the study day.";
const COMMENT = "The paper gives no sex distribution of the group.";
const EDITED = "Healthy adult volunteers who abstained from caffeine for 72 hours before the study day.";

/** Three descriptions of several lines each, as the notes of a real study have them. */
const LONG_DESCRIPTIONS = [
  "In a preliminary trial six volunteers rinsed their mouths for 5 s with 2 ml of a solution that contained 400 mg of caffeine sodium salicylate. After spitting it out, they rinsed twice for 10 s with 25 ml of water each.",
  "In the first part of the study eight volunteers took 7 mg/kg of caffeine in soft gelatine capsules under standardized conditions. After the dose with 200 ml of water at body temperature, they rinsed their mouths, and a sample of saliva was taken as the blank value, to rule out absorption in the mouth and to check the abstinence from caffeine.",
  "In the second part of the study five volunteers received 220 mg of caffeine as caffeine sodium salicylate by intravenous injection.",
];

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

/**
 * Wait until the viewer of the paper beside a shared table has drawn page 1: axe checks the page
 * as the curator sees it, not while PDF.js still draws.
 */
async function paperDrawn(page: Page): Promise<void> {
  await expect(page.locator('.page[data-page-number="1"][data-loaded="true"]')).toBeVisible();
  await expect(page.getByRole("searchbox", { name: "Find in the paper" })).toBeEnabled();
}

/**
 * The height of an element once it stopped changing from one frame to the next. Open notes first
 * take the height of their content, and a resize observer limits them to the room that the rows
 * leave in the next frame.
 */
async function settledHeight(locator: Locator): Promise<number> {
  return locator.evaluate(async (element) => {
    const frame = () => new Promise((resolve) => requestAnimationFrame(resolve));
    let last = -1;
    for (;;) {
      await frame();
      const height = element.getBoundingClientRect().height;
      if (height === last) return height;
      last = height;
    }
  });
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

test("the notes show their descriptions and comments without labels, and the author of a comment once", async ({
  app,
  page,
}, testInfo) => {
  await app.open(`${STUDY}/data?file=subjects.tsv`);
  const pane = rowsPane(page, "subjects.tsv");
  await pane.getByRole("button", { name: /^Notes of the subjects/ }).click();
  const notes = pane.getByRole("region", { name: /^Notes of the subjects/ });
  await expect(notes.getByRole("textbox", { name: "Description 2", exact: true })).toHaveValue(
    "Age and body weight are the mean and the standard deviation of the group.",
  );
  // Screen readers name every text area; no label shows.
  await expect(notes.getByRole("textbox")).toHaveCount(3);
  await expect(notes.locator("label")).toHaveCount(0);
  await expect(notes.getByText(/^(Description \d+|Comment \d+ by )/)).toHaveCount(0);
  // The author of the comment shows once, above the text of the comment.
  const comment = notes.locator(".comment-row");
  const author = comment.locator(".comment-author");
  await expect(author).toHaveCount(1);
  await expect(author).toContainText("curator");
  const text = comment.getByRole("textbox", { name: "Comment 1 by curator", exact: true });
  await expect(text).toHaveValue(COMMENT);
  const [line, field] = await Promise.all([author.boundingBox(), text.boundingBox()]);
  expect(line!.y + line!.height).toBeLessThanOrEqual(field!.y);
  // Every text area shows its whole text.
  for (const area of await notes.getByRole("textbox").all()) {
    expect(await area.evaluate((element) => element.scrollHeight - element.clientHeight)).toBeLessThanOrEqual(1);
  }

  for (const width of [1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
      await paperDrawn(page);
      await expectAccessible(page);
      const shot = await notes.screenshot({ path: testInfo.outputPath(`notes-${theme}-${width}.png`) });
      await testInfo.attach(`notes-${theme}-${width}.png`, { body: shot, contentType: "image/png" });
    }
  }
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

    const banner = page.locator(".unsaved-banner");
    await expect(banner).toContainText("Unsaved changes to study.json: Notes of the subjects");
    await expect(sectionTab(page, "Data, unsaved changes")).toBeVisible();
    await expect(sectionTab(page, "Metadata")).toBeVisible();
    // The panes keep filling the window below the banner: the page does not scroll.
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollHeight - document.documentElement.clientHeight))
      .toBe(0);

    // Metadata shows the same draft and the same banner, without asking to leave.
    await sectionTab(page, "Metadata").click();
    await expect(page).toHaveURL(/#\/studies\/caffeine\/Demo2020\/metadata$/);
    await expect(banner).toContainText("Unsaved changes to study.json: Notes of the subjects");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(banner).toContainText("study.json saved.");
    await expect(sectionTab(page, "Data")).toBeVisible();

    // Only the first description of the subjects changed on disk.
    const expected = structuredClone(before);
    expected.notes!.subjects!.descriptions![0] = EDITED;
    await expect.poll(() => studyJsonOnDisk(app.server.workspace)).toEqual(expected);
  } finally {
    writeFileSync(studyJsonPath(app.server.workspace), original);
  }
});

test("open notes leave rows of the table in view in a short window, with the banner above the panes", async ({
  app,
  page,
}) => {
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    const value = JSON.parse(original) as StudyJson;
    value.notes = { ...value.notes, timecourses: { descriptions: LONG_DESCRIPTIONS, comments: [] } };
    writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
    await page.setViewportSize({ width: 1366, height: 600 });
    const box = async (part: Locator) => (await part.boundingBox())!;
    const bottom = (rect: { y: number; height: number }) => rect.y + rect.height;

    // timecourses_Fig1.tsv has 18 rows.
    await app.open(`${STUDY}/data?file=timecourses_Fig1.tsv`);
    const pane = rowsPane(page, "timecourses_Fig1.tsv");
    await pane.getByRole("button", { name: /^Notes of the timecourses/ }).click();
    await pane.getByRole("textbox", { name: "Description 1" }).fill(EDITED);
    const banner = page.locator(".unsaved-banner");
    await expect(banner).toContainText("Unsaved changes to study.json: Notes of the timecourses");

    const panel = pane.getByRole("region", { name: /^Notes of the timecourses/ });
    const rows = pane.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
    const [notes, grid, header, section] = await Promise.all([panel, rows, rows.getByRole("row").first(), pane].map(box));
    // The notes scroll on their own rather than push the rows out of the pane, which keeps their header and four rows.
    expect(bottom(notes!)).toBeLessThanOrEqual(grid!.y);
    expect(bottom(grid!)).toBeLessThanOrEqual(bottom(section!));
    expect(grid!.height).toBeGreaterThanOrEqual(5 * header!.height);
    // The banner stands above the panes rather than cover them.
    expect(bottom(await box(banner))).toBeLessThanOrEqual(section!.y);

    // The cut notes fade out at the bottom of their body until it scrolls to its end.
    const fade = panel.locator(".pane-more");
    await expect(fade).toBeVisible();
    await panel.locator(".table-notes-body").evaluate((body) => body.scrollTo(0, body.scrollHeight));
    await expect(fade).toBeHidden();

    // subjects.tsv has one row: the rows keep their header and that row, and leave the rest to the
    // notes, which start at their top.
    await page.getByRole("navigation", { name: "Tables and sources" }).getByRole("button", { name: /^subjects\.tsv/ }).click();
    const subjects = rowsPane(page, "subjects.tsv");
    await subjects.getByRole("button", { name: /^Notes of the subjects/ }).click();
    const short = subjects.getByRole("region", { name: /^Notes of the subjects/ });
    const row = subjects.getByRole("region", { name: "Rows of subjects.tsv" });
    await expect(row.getByRole("row")).toHaveCount(2);
    expect(await short.locator(".table-notes-body").evaluate((body) => body.scrollTop)).toBe(0);
    await expect(short.locator(".pane-more")).toBeVisible();
    const [cut, region, last, whole] = await Promise.all([short, row, row.getByRole("row").last(), subjects].map(box));
    expect(bottom(cut!)).toBeLessThanOrEqual(region!.y);
    expect(bottom(last!)).toBeLessThanOrEqual(bottom(region!));
    // No room stays empty below the row while the notes are cut: only the border of the region.
    expect(bottom(region!) - bottom(last!)).toBeLessThanOrEqual(2);
    expect(bottom(region!)).toBeLessThanOrEqual(bottom(whole!));
  } finally {
    writeFileSync(path, original);
  }
});

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

    // In a window of 1366 x 680 px the notes are cut; the three rows keep only their own room.
    await page.setViewportSize({ width: 1366, height: 680 });
    await expect(panel.locator(".pane-more")).toBeVisible();
    const [cut, shorter, last] = await Promise.all([panel, rows, rows.getByRole("row").last()].map(box));
    expect(bottom(cut!)).toBeLessThanOrEqual(shorter!.y);
    expect(bottom(last!)).toBeLessThanOrEqual(bottom(shorter!));
    expect(bottom(shorter!) - bottom(last!)).toBeLessThanOrEqual(2);
    await page.setViewportSize({ width: 1440, height: 900 });

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

test("open notes grow with their content without a loop of resize observers", async ({ app, page }) => {
  // A size changed inside a callback of a ResizeObserver that resizes what another observes makes
  // the browser fire an error event on the window, which the fixture collects.
  const path = studyJsonPath(app.server.workspace);
  const original = readFileSync(path, "utf8");
  try {
    const notes = JSON.parse(original) as StudyJson;
    notes.notes = { ...notes.notes, interventions: { descriptions: LONG_DESCRIPTIONS, comments: [] } };
    writeFileSync(path, `${JSON.stringify(notes, null, 2)}\n`);
    // Above interventions.tsv the notes have room to grow; above subjects.tsv they are short.
    for (const [file, kind] of [
      ["interventions.tsv", "interventions"],
      ["subjects.tsv", "subjects"],
    ] as const) {
      await app.open(`${STUDY}/data?file=${file}`);
      const pane = rowsPane(page, file);
      const toggle = pane.getByRole("button", { name: new RegExp(`^Notes of the ${kind}`) });
      await toggle.click();
      const panel = pane.getByRole("region", { name: new RegExp(`^Notes of the ${kind}`) });
      const description = panel.getByRole("textbox", { name: "Description 1" });
      await expect(description).toBeVisible();
      const before = await settledHeight(panel);
      // A longer description wraps to more lines: the notes grow with it.
      await description.press("End");
      await description.pressSequentially(
        " These two sentences wrap the description to more lines in the pane. The text area and the notes grow with them.",
      );
      await expect.poll(async () => (await panel.boundingBox())!.height).toBeGreaterThan(before);
      await toggle.click();
      await page.getByRole("button", { name: "Discard" }).click();
      await expect(page.locator(".unsaved-banner")).toContainText("Changes discarded.");
    }
    expect(await page.evaluate(() => window.__windowErrors)).toEqual([]);
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
    // The descriptions are one line shorter each than with labels: a lower window keeps them above 40 %.
    await page.setViewportSize({ width: 1366, height: 800 });
    await app.open(`${STUDY}/metadata`);
    const panel = page.getByRole("region", { name: /^Notes of the scatters/ });
    await panel.getByRole("button", { name: /^Notes of the scatters 3 descriptions/ }).click();
    await expect(panel.getByRole("textbox", { name: "Description 3" })).toHaveValue(LONG_DESCRIPTIONS[2]!);
    // Longer than 40 % of the window, the body still has no scroll of its own and no fade.
    const body = panel.locator(".table-notes-body");
    expect(await body.evaluate((element) => element.scrollHeight)).toBeGreaterThan(0.4 * 800);
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
