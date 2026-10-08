// Capture the screenshots of docs/local-curation.md from a running `pkdb curate` on a fresh copy
// of the fixture workspace, as README.md describes:
//   PKDB_CURATION_URL='http://127.0.0.1:PORT/#token=...' node tools/curation_docs/render.mjs
// The renderer never logs the launch URL. It changes the workspace: it edits a cell of Demo2020.
// It quantizes the images with tools/curation_docs/optimize_png.py, which needs uv.
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/playwright/index.mjs";

const repository = fileURLToPath(new URL("../../", import.meta.url));
const launchUrl = process.env.PKDB_CURATION_URL;
if (!launchUrl) throw new Error("Set PKDB_CURATION_URL to the launch URL that pkdb curate printed.");
const parsed = new URL(launchUrl);
if (parsed.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
  throw new Error("PKDB_CURATION_URL must be the launch URL of a local pkdb curate, on a loopback address.");
}
const destination = resolve(process.env.PKDB_CURATION_SCREENSHOTS ?? join(repository, "docs/images/curation"));
await mkdir(destination, { recursive: true });

/** The study of the fixture that the screenshots show, and its table of the digitized figure. */
const STUDY = "caffeine/Demo2020";
const TABLE = "timecourses_Fig1.tsv";
/** The line of the table whose mapped point lies away from its digitized point. */
const MISPLACED_LINE = 6;
/** The line of the table that the workbook and the TSV file change differently. */
const CONFLICT_LINE = 7;
/** The images that the renderer wrote. */
const written = [];

const browser = await chromium.launch();
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    colorScheme: "light",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  // The first validation of the fixture takes a few seconds.
  page.setDefaultTimeout(60_000);

  await page.goto(launchUrl);
  await page.getByRole("link", { name: "PK-DB Local curation" }).waitFor();

  // Overview, after the first validation of every study, with a study selected for the batch actions.
  const studies = page.getByRole("table", { name: "Studies of the workspace" });
  const study = studies.getByRole("link", { name: STUDY });
  await study.waitFor({ timeout: 15_000 }).catch(() => {
    throw new Error(`The workspace has no ${STUDY}. Start pkdb curate on a fresh copy of the fixture workspace.`);
  });
  await studies.getByRole("cell", { name: "2 warnings" }).waitFor();
  await studies.getByRole("cell", { name: "1 error" }).waitFor();
  await studies.getByRole("checkbox", { name: `Select ${STUDY}` }).check();
  await page.getByText("1 study selected").waitFor();
  await capture(page, "overview.png");

  // Review: the study opens on its open items; the item of an AI agent with its target rows.
  await study.click();
  const sections = page.getByRole("navigation", { name: "Study sections" });
  await page
    .getByRole("list", { name: "Review items" })
    .getByRole("button", { name: /^Uncertainty/ })
    .click();
  await page.getByRole("article", { name: "Uncertainty" }).waitFor();
  const target = page.getByRole("region", { name: "Target" });
  await target.getByRole("table").waitFor();
  await scrollToBottom(page, target);
  await capture(page, "review.png");

  // Sources: the digitization of the figure on its image, with the row of a mapped point.
  await sections.getByRole("link", { name: /^Sources\b/ }).click();
  await page.getByRole("tab", { name: "Fig1", selected: true }).waitFor();
  await page.getByRole("list", { name: "Series" }).waitFor();
  await scrollToBottom(page, page.getByText("Data of the plot"));
  await hoverMappedRow(page, "Fig1", MISPLACED_LINE);
  await capture(page, "sources.png", { pointer: true });

  // Metadata: the forms of study.json with an unsaved change, which is discarded afterwards.
  await sections.getByRole("link", { name: /^Metadata\b/ }).click();
  await page.getByRole("slider", { name: "Rating of curator" }).press("ArrowRight");
  await page.getByText("Unsaved changes in study.json").waitFor();
  await capture(page, "metadata.png");
  await page.getByRole("button", { name: "Discard", exact: true }).click();

  // Tables: the panel of a conflict between the workbook and the TSV file, above the table.
  await sections.getByRole("link", { name: /^Tables\b/ }).click();
  await page.getByRole("status").filter({ hasText: /^\s*In sync/ }).waitFor();
  const workspace = (await page.getByRole("button", { name: /^Workspace: / }).getAttribute("aria-label")).slice(
    "Workspace: ".length,
  );
  await setAutomaticActions(page, true);
  await conflict(join(workspace, STUDY));
  await setAutomaticActions(page, false);
  await page.getByRole("status").filter({ hasText: `Conflict in ${TABLE}` }).waitFor();
  await page.getByRole("region", { name: `Conflicting rows of ${TABLE}` }).waitFor();
  await page.getByRole("tab", { name: new RegExp(`^${TABLE.replace(".", "\\.")}`) }).click();
  await page.getByRole("region", { name: `Rows of ${TABLE}`, exact: true }).waitFor();
  await capture(page, "tables-conflict.png");
} finally {
  await browser.close();
}
python("tools/curation_docs/optimize_png.py", ...written);
for (const path of written) console.log(`Wrote ${path}`);

/**
 * Save the window as `name` once the fonts are loaded, the network is idle and the ripples of
 * clicks have faded. The pointer moves to the empty middle of the app bar, so that nothing shows
 * a hover, unless `pointer` keeps it where it is.
 */
async function capture(page, name, { pointer = false } = {}) {
  if (!pointer) await page.mouse.move(600, 32);
  // A control that a click or a key focused shows no focus ring in the picture.
  await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => !document.querySelector(".v-ripple__container"));
  // Tabs that scroll a chosen tab into view, and menus that close, move for a moment.
  await page.waitForTimeout(500);
  const path = join(destination, name);
  await page.screenshot({ path, animations: "disabled", caret: "hide" });
  written.push(path);
}

/** Run a script of the repository with the Python environment of python/, which `uv run` prepares. */
function python(script, ...args) {
  execFileSync("uv", ["run", "--project", join(repository, "python"), "python", join(repository, script), ...args], {
    stdio: ["ignore", "ignore", "inherit"],
  });
}

/** Scroll the window so that `locator` ends a little above its bottom edge, as far as the page allows. */
async function scrollToBottom(page, locator) {
  const box = await locator.boundingBox();
  const height = page.viewportSize().height;
  await page.evaluate((offset) => window.scrollBy(0, offset), box.y + box.height + 24 - height);
}

/** Hover the cross of a mapped row of the figure overlay, which shows the line and its values. */
async function hoverMappedRow(page, source, line) {
  const figure = page.getByRole("img", { name: new RegExp(`^Figure ${source} with`) });
  const view = await page.evaluate(
    async (url) => (await fetch(url)).json(),
    `/local/studies/${STUDY}/sources/${source}`,
  );
  const point = view.overlay.find((entry) => entry.role === "mapped" && entry.line === line);
  if (!point) throw new Error(`The overlay of ${source} has no mapped row of line ${line}.`);
  const box = await figure.boundingBox();
  const [width, height] = view.image_size;
  await page.mouse.move(box.x + (point.px * box.width) / width, box.y + (point.py * box.height) / height);
  await page.getByText(`${TABLE} line ${line}`).waitFor();
}

/** Pause or resume the automatic actions from the File watching menu of the header. */
async function setAutomaticActions(page, paused) {
  const [from, action, to] = paused
    ? ["Active", "Pause automatic actions", "Paused"]
    : ["Paused", "Resume automatic actions", "Active"];
  await page.getByRole("button", { name: `File watching: ${from}` }).click();
  await page.getByRole("button", { name: action }).click();
  await page.getByRole("button", { name: `File watching: ${to}` }).waitFor();
  await page.keyboard.press("Escape");
}

/** The spreadsheet name of the column at `index`: A for 0, Z for 25, AA for 26. */
function columnName(index) {
  let name = "";
  for (let number = index + 1; number > 0; number = Math.floor((number - 1) / 26)) {
    name = String.fromCharCode("A".charCodeAt(0) + ((number - 1) % 26)) + name;
  }
  return name;
}

/** Change the mean of a line of the table differently in the workbook and in the TSV file. */
async function conflict(folder) {
  const path = join(folder, TABLE);
  const rows = (await readFile(path, "utf8"))
    .split("\n")
    .filter(Boolean)
    .map((text) => text.split("\t"));
  const column = rows[0].indexOf("mean");
  // The sheet has the rows and columns of the table: the header is row 1, line 7 is row 7.
  const cell = `${columnName(column)}${CONFLICT_LINE}`;
  // openpyxl saves the workbook as a spreadsheet program does.
  const workbook = join(folder, `${STUDY.split("/")[1]}.xlsx`);
  python("tools/curation_testing/edit_workbook.py", workbook, TABLE.replace(/\.tsv$/, ""), cell, "1.08");
  rows[CONFLICT_LINE - 1][column] = "1.06";
  await writeFile(path, rows.map((cells) => `${cells.join("\t")}\n`).join(""));
}
