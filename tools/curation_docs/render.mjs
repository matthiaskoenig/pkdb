// Capture the screenshots of docs/local-curation.md from a running `pkdb curate` on a fresh copy
// of the fixture workspace, as README.md describes:
//   PKDB_CURATION_URL='http://127.0.0.1:PORT/#token=...' node tools/curation_docs/render.mjs
// The renderer never logs the launch token, also not in an error. It changes the workspace: it
// edits a cell of Demo2020. It quantizes the images with optimize_png.py, which needs uv.
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
// Node strips the types of this module, which imports nothing.
import { columnLetters } from "../../frontend/src/curation-app/columns.ts";

const repository = fileURLToPath(new URL("../../", import.meta.url));
const launchUrl = process.env.PKDB_CURATION_URL;
if (!launchUrl) throw new Error("Set PKDB_CURATION_URL to the launch URL that pkdb curate printed.");
// An invalid URL must not reach the error output, which would show it.
const parsed = URL.canParse(launchUrl) ? new URL(launchUrl) : null;
if (!parsed) throw new Error("PKDB_CURATION_URL is not a URL. Copy the launch URL that pkdb curate printed.");
if (parsed.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
  throw new Error("PKDB_CURATION_URL must be the launch URL of a local pkdb curate, on a loopback address.");
}
/** The launch token, which errors of Playwright would repeat with the URL. */
const token = new URLSearchParams(parsed.hash.slice(1)).get("token");
const destination = resolve(process.env.PKDB_CURATION_SCREENSHOTS ?? join(repository, "docs/images/curation"));

/** The width of every image, and the height of those that need no more. */
const WIDTH = 1440;
const HEIGHT = 900;
/** The heights that show the review item with all its target rows, and the figure with its legend, below the study header. */
const REVIEW_HEIGHT = 1010;
const SOURCES_HEIGHT = 1100;
/** The folder of the copy of the fixture workspace, whose name the header of every image shows. */
const WORKSPACE = "demo_studies";
/** The study of the fixture that the screenshots show, and its table of the digitized figure. */
const STUDY = "caffeine/Demo2020";
const TABLE = "timecourses_Fig1.tsv";
/** The line of the table whose mapped point lies away from its digitized point. */
const MISPLACED_LINE = 6;
/** The line of the table that the workbook and the TSV file change differently. */
const CONFLICT_LINE = 7;

try {
  await mkdir(destination, { recursive: true });
  const written = await render();
  python("tools/curation_docs/optimize_png.py", ...written);
  for (const path of written) console.log(`Wrote ${path}`);
} catch (error) {
  console.error(redact(error instanceof Error ? (error.stack ?? error.message) : String(error)));
  process.exitCode = 1;
}

/** `text` without the launch token. */
function redact(text) {
  return token ? text.replaceAll(token, "<launch token>") : text;
}

/** Capture the five images; the paths of the files. */
async function render() {
  const written = [];
  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({
      viewport: { width: WIDTH, height: HEIGHT },
      deviceScaleFactor: 1,
      colorScheme: "light",
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    // The first validation of the fixture takes a few seconds.
    page.setDefaultTimeout(60_000);
    const capture = async (name, ready, options) => written.push(await screenshot(page, name, ready, options));

    await page.goto(launchUrl);
    await page.getByRole("link", { name: "PK-DB Local curation" }).waitFor();
    const workspace = (await page.getByRole("button", { name: /^Workspace: / }).getAttribute("aria-label")).slice(
      "Workspace: ".length,
    );
    if (workspace.split(/[\\/]/).at(-1) !== WORKSPACE) {
      throw new Error(`Start pkdb curate on a copy of the fixture workspace in a folder named ${WORKSPACE}.`);
    }

    // Overview, after the first validation of every study, with a study selected for the batch actions.
    const studies = page.getByRole("table", { name: "Studies of the workspace" });
    const study = studies.getByRole("link", { name: STUDY });
    await study.waitFor({ timeout: 15_000 }).catch(() => {
      throw new Error(`The workspace has no ${STUDY}. Start pkdb curate on a fresh copy of the fixture workspace.`);
    });
    await studies.getByRole("cell", { name: "2 warnings" }).waitFor();
    await studies.getByRole("checkbox", { name: `Select ${STUDY}` }).check();
    await capture("overview.png", [studies.getByRole("cell", { name: "1 error" }), page.getByText("1 study selected")]);

    // Review: the study opens on its open items; the item of an AI agent with its target rows.
    await study.click();
    const sections = page.getByRole("navigation", { name: "Study sections" });
    await page
      .getByRole("list", { name: "Review items" })
      .getByRole("button", { name: /^Uncertainty/ })
      .click();
    const target = page.getByRole("region", { name: "Target" });
    await page.setViewportSize({ width: WIDTH, height: REVIEW_HEIGHT });
    await capture("review.png", [page.getByRole("article", { name: "Uncertainty" }), target.getByRole("table")], {
      whole: target,
    });

    // Sources: the digitization of the figure on its image, with the row of a mapped point.
    await page.setViewportSize({ width: WIDTH, height: SOURCES_HEIGHT });
    await sections.getByRole("link", { name: /^Sources\b/ }).click();
    await page.getByRole("tab", { name: "Fig1", selected: true }).waitFor();
    const legend = page.getByRole("list", { name: "Series" });
    await legend.waitFor();
    await hoverMappedRow(page, "Fig1", MISPLACED_LINE);
    await capture("sources.png", [legend, page.getByText(`${TABLE} line ${MISPLACED_LINE}`)], {
      pointer: true,
      whole: page.getByText("Data of the plot"),
    });

    // Metadata: the forms of study.json with an unsaved change, which is discarded afterwards.
    await page.setViewportSize({ width: WIDTH, height: HEIGHT });
    await sections.getByRole("link", { name: /^Metadata\b/ }).click();
    await page.getByRole("slider", { name: "Rating of curator" }).press("ArrowRight");
    await capture("metadata.png", [page.getByText("Unsaved changes in study.json")]);
    await page.getByRole("button", { name: "Discard", exact: true }).click();

    // Tables: the panel of a conflict between the workbook and the TSV file, above the table.
    await sections.getByRole("link", { name: /^Tables\b/ }).click();
    await page.getByRole("status").filter({ hasText: /^\s*In sync/ }).waitFor();
    await setAutomaticActions(page, true);
    await conflict(join(workspace, STUDY));
    await setAutomaticActions(page, false);
    await page.getByRole("status").filter({ hasText: `Conflict in ${TABLE}` }).waitFor();
    const tabs = page.getByRole("tablist", { name: "Tables" });
    await tabs.getByRole("tab", { name: new RegExp(`^${TABLE.replace(".", "\\.")}`) }).click();
    // The job of the conflict has ended once its report, the conflict as an error, is the study's.
    await capture("tables-conflict.png", [
      page.getByRole("region", { name: `Conflicting rows of ${TABLE}` }),
      page.getByRole("region", { name: `Rows of ${TABLE}`, exact: true }),
      page.getByText("1 error", { exact: true }),
    ]);
  } finally {
    await browser.close();
  }
  return written;
}

/**
 * Save the window as `name` from the top of the page once the app is ready: every locator of
 * `ready` is visible, the images are loaded, no menu or dialog is open, nothing animates, and
 * the tab bars stand still. The pointer moves to the empty middle of the app bar, so that nothing
 * shows a hover, unless `pointer` keeps it where it is. `whole` must fit into the window.
 */
async function screenshot(page, name, ready, { pointer = false, whole = null } = {}) {
  await page.evaluate(() => window.scrollTo(0, 0));
  if (!pointer) await page.mouse.move(600, 32);
  // A control that a click or a key focused shows no focus ring in the picture.
  await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
  for (const locator of ready) await locator.waitFor();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.images].every((image) => image.complete));
  await page.waitForFunction(() => !document.querySelector(".v-overlay--active"));
  await settled(page);
  for (const tabs of await page.getByRole("tablist").all()) await alignTabs(tabs);
  await settled(page);
  if (whole) {
    const box = await whole.boundingBox();
    const height = page.viewportSize().height;
    if (!box || box.y + box.height > height) throw new Error(`${name} cuts off its content: raise its height.`);
  }
  const path = join(destination, name);
  // Not `animations: "disabled"`: it plays the paused animations of hidden loaders afterwards.
  await page.screenshot({ path, caret: "hide" });
  return path;
}

/**
 * Wait until nothing animates and the tab bars have kept their scroll position for two
 * animation frames: a chosen tab scrolls into view, and a ripple of a click fades.
 */
async function settled(page) {
  await page.evaluate(() => {
    window.__renderFrames = { position: null, stable: 0 };
  });
  await page.waitForFunction(
    () => {
      const position = [...document.querySelectorAll(".v-slide-group__container")]
        .map((container) => container.scrollLeft)
        .join(",");
      const frames = window.__renderFrames;
      frames.stable = position === frames.position ? frames.stable + 1 : 0;
      frames.position = position;
      // Hidden loaders keep paused animations, so only running ones count.
      return frames.stable >= 2 && document.getAnimations().every((animation) => animation.playState !== "running");
    },
    undefined,
    { polling: "raf" },
  ).catch(async (error) => {
    const state = await page.evaluate(() => ({
      tabs: window.__renderFrames,
      running: document
        .getAnimations()
        .filter((animation) => animation.playState === "running")
        .map((animation) => {
          const target = animation.effect?.target;
          const chain = [];
          for (let node = target; node && chain.length < 8; node = node.parentElement) chain.push(`${node.tagName}.${node.getAttribute("class") ?? ""}[${node.getAttribute("aria-label") ?? ""}]`);
          return `${animation.animationName ?? animation.transitionProperty ?? "script"} ${JSON.stringify(target?.getBoundingClientRect())} ${chain.join(" < ")}`;
        }),
    }));
    throw new Error(`The page did not settle: ${JSON.stringify(state)}`, { cause: error });
  });
}

/**
 * Scroll a tab bar so that a whole tab starts at its left edge, while the chosen tab stays in
 * view: a tab bar that centers the chosen tab can cut the first visible one.
 */
async function alignTabs(tabs) {
  await tabs.evaluate((list) => {
    const container = list.querySelector(".v-slide-group__container");
    const items = [...list.querySelectorAll('[role="tab"]')];
    const chosen = items.find((item) => item.getAttribute("aria-selected") === "true");
    if (!container || !chosen) return;
    const origin = container.getBoundingClientRect().left - container.scrollLeft;
    const start = (item) => item.getBoundingClientRect().left - origin;
    const end = (item) => item.getBoundingClientRect().right - origin;
    const widest = container.scrollWidth - container.clientWidth;
    // The start of a tab that the bar can scroll to, with the chosen tab in view.
    const possible = items
      .map(start)
      .filter((left) => left <= widest + 0.5 && start(chosen) >= left && end(chosen) <= left + container.clientWidth);
    const current = container.scrollLeft;
    const nearest = possible.sort((a, b) => Math.abs(a - current) - Math.abs(b - current))[0];
    if (nearest !== undefined) container.scrollLeft = nearest;
  });
}

/** Run a script of the repository with the Python environment of python/, which `uv run` prepares. */
function python(script, ...args) {
  execFileSync("uv", ["run", "--project", join(repository, "python"), "python", join(repository, script), ...args], {
    stdio: ["ignore", "ignore", "inherit"],
  });
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
  await page.evaluate(() => window.scrollTo(0, 0));
  const box = await figure.boundingBox();
  const [width, height] = view.image_size;
  await page.mouse.move(box.x + (point.px * box.width) / width, box.y + (point.py * box.height) / height);
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

/** Change the mean of a line of the table differently in the workbook and in the TSV file. */
async function conflict(folder) {
  const path = join(folder, TABLE);
  const rows = (await readFile(path, "utf8"))
    .split("\n")
    .filter(Boolean)
    .map((text) => text.split("\t"));
  const column = rows[0].indexOf("mean");
  // The sheet has the rows and columns of the table: the header is row 1, line 7 is row 7.
  const cell = `${columnLetters(column)}${CONFLICT_LINE}`;
  // openpyxl saves the workbook as a spreadsheet program does.
  const workbook = join(folder, `${STUDY.split("/")[1]}.xlsx`);
  python("tools/curation_testing/edit_workbook.py", workbook, TABLE.replace(/\.tsv$/, ""), cell, "1.08");
  rows[CONFLICT_LINE - 1][column] = "1.06";
  await writeFile(path, rows.map((cells) => `${cells.join("\t")}\n`).join(""));
}
