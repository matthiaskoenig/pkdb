// Capture the screenshots of docs/web-interface.md from the disposable website of the browser tests,
// as README.md describes:
//   tools/website_docs/run.sh
// or, against a website of tools/frontend_testing that already runs:
//   node tools/website_docs/render.mjs
// The website holds only the artificial fixture data of tools/frontend_testing/serve.py. The renderer
// adds the synthetic studies of the curation app screenshots (tools/curation_testing/fixture): it signs
// in as the account `curator` of the fixture, creates an API key and uploads them with `pkdb upload`.
// It quantizes the images with ../curation_docs/optimize_png.py. Both need uv.
import { execFileSync } from "node:child_process";
import { cp, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
import { alignColumns, alignTabs, cutColumns, fitPanes, settled } from "../curation_docs/capture.mjs";

const repository = fileURLToPath(new URL("../../", import.meta.url));
/** The address of the website of tools/frontend_testing, which compose.frontend-test.yaml publishes. */
const website = process.env.PKDB_WEBSITE_URL ?? "http://127.0.0.1:18184";
const parsed = URL.canParse(website) ? new URL(website) : null;
if (!parsed || parsed.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
  throw new Error("PKDB_WEBSITE_URL must be the website of tools/frontend_testing, on a loopback address.");
}
const destination = resolve(process.env.PKDB_WEBSITE_SCREENSHOTS ?? join(repository, "docs/images/web"));

/** The width of every image, and the height of the window. */
const WIDTH = 1440;
const HEIGHT = 900;
/** The height that the images of the longer pages, the data search and a record, do not exceed. */
const TALL = 1200;
/** The account of the fixture that curates the studies, and the password of every account. */
const CURATOR = "curator";
const PASSWORD = "Frontend-test-password-42!";
/** The study of the study pages, from the screenshots of the curation app, and the study format 1 study. */
const STUDY = "caffeine/Demo2020";
const FORMAT1_STUDY = "FRONTEND_SCOPE";
/**
 * The studies of the curation app fixture that the renderer uploads, released and public, so that a
 * visitor sees them, with an issue. Draft2021 gets the substance that its fixture misspells and the
 * sex of its subjects, which a release needs, so that it validates.
 */
const UPLOADS = [
  { study: "caffeine/Demo2020", pkdb_id: "PKDB09904", issue: 2161 },
  { study: "caffeine/Draft2021", pkdb_id: "PKDB09905", issue: 2162, repair: repairDraft },
];
const RELEASE_DATE = "2026-09-30";

try {
  await mkdir(destination, { recursive: true });
  const written = await render();
  python("tools/curation_docs/optimize_png.py", ...written);
  for (const path of written) console.log(`Wrote ${path}`);
} catch (error) {
  console.error(error instanceof Error ? (error.stack ?? error.message) : String(error));
  process.exitCode = 1;
}

/** Upload the studies, then capture the images, first as a visitor and then as the curator; the paths of the files. */
async function render() {
  const written = [];
  // A partial raster of a changed area can differ from a whole one by a level in a pixel, so that
  // two runs gave different images.
  const browser = await chromium.launch({ args: ["--disable-partial-raster"] });
  try {
    const contexts = [];
    const newPage = async () => {
      const context = await browser.newContext({
        baseURL: website,
        viewport: { width: WIDTH, height: HEIGHT },
        deviceScaleFactor: 1,
        colorScheme: "light",
        reducedMotion: "reduce",
      });
      contexts.push(context);
      return context.newPage();
    };
    const curator = await newPage();
    await signIn(curator);
    await upload(await createKey(curator));
    const visitor = await newPage();
    for (const [page, pages] of [
      [visitor, visitorPages],
      [curator, curatorPages],
    ]) {
      await pages(page, async (name, ready, options) => written.push(await screenshot(page, name, ready, options)));
    }
    for (const context of contexts) await context.close();
  } finally {
    await browser.close();
  }
  return written;
}

/** Sign in as the curator. */
async function signIn(page) {
  await page.goto("/account");
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(CURATOR);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Account settings", exact: true }).waitFor();
}

/** A new API key of the signed-in account that may upload studies, as Account settings creates one. */
async function createKey(page) {
  const secret = await page.evaluate(async () => {
    const { csrf_token: token } = await (await fetch("/api/v1/auth/csrf")).json();
    const response = await fetch("/api/v1/me/api-keys", {
      method: "POST",
      headers: { "content-type": "application/json", "x-csrf-token": token },
      body: JSON.stringify({ name: "Website screenshots", lifetime_days: 1, scopes: ["read", "studies:write"] }),
    });
    return response.ok ? (await response.json()).secret : null;
  });
  if (typeof secret !== "string") throw new Error("The API key of the curator could not be created.");
  return secret;
}

/** Upload the studies of UPLOADS from a copy of the curation app fixture with `pkdb upload`, as the curator. */
async function upload(key) {
  const folder = await mkdtemp(join(tmpdir(), "pkdb-website-docs-"));
  try {
    for (const { study, pkdb_id, issue, repair } of UPLOADS) {
      const target = join(folder, study);
      await cp(join(repository, "tools/curation_testing/fixture", study), target, { recursive: true });
      const path = join(target, "study.json");
      const metadata = JSON.parse(await readFile(path, "utf8"));
      Object.assign(metadata, { access: "public", issue, release: { pkdb_id, date: RELEASE_DATE } });
      await writeFile(path, `${JSON.stringify(metadata, null, 2)}\n`);
      await repair?.(target);
    }
    // The website's own vocabulary, which pkdb upload checks against the server's.
    const environment = { ...process.env, PKDB_NO_UPDATE: "1", PKDB_CACHE_DIR: join(folder, ".cache") };
    delete environment.PKDB_ENDPOINT;
    delete environment.PKDB_API_KEY;
    pkdb(folder, environment, "vocabulary", "sync", "--endpoint", website);
    const substances = [...new Set(UPLOADS.map(({ study }) => study.split("/")[0]))];
    for (const substance of substances) {
      pkdb(folder, { ...environment, PKDB_API_KEY: key, PKDB_USER: CURATOR }, "upload", "--endpoint", website, substance);
    }
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
}

/** Correct the substance that Draft2021 misspells on purpose and add the sex of its subjects. */
async function repairDraft(folder) {
  const outputs = join(folder, "outputs_Tab1.tsv");
  await writeFile(outputs, (await readFile(outputs, "utf8")).replaceAll("\tcafeine\t", "\tcaffeine\t"));
  const characteristica = join(folder, "characteristica.tsv");
  const lines = (await readFile(characteristica, "utf8")).trimEnd().split("\n");
  const columns = lines[0].split("\t");
  const row = columns.map((column) => ({ study: "Draft2021", source: "Text", subjects: "all", measurement: "sex", choice: "M" })[column] ?? "");
  await writeFile(characteristica, `${[...lines, row.join("\t")].join("\n")}\n`);
}

/** The images of the pages as a visitor, who has not signed in, sees them. */
async function visitorPages(page, capture) {
  await page.goto("/account");
  await capture("login.png", [page.getByRole("heading", { name: "Sign in to PK-DB" })]);

  // The data search on its Studies and on its Measurements tab.
  await page.goto("/data");
  for (const [tab, name] of [
    ["Studies", "browse-studies.png"],
    ["Measurements", "browse-measurements.png"],
  ]) {
    await page.getByRole("tab", { name: new RegExp(`^${tab} `) }).click();
    await page.waitForURL(new RegExp(`tab=${tab.toLowerCase()}`));
    await capture(
      name,
      [
        page.getByText(new RegExp(`^\\d+ ${tab.toLowerCase()} in the applied selection$`)),
        page.getByRole("button", { name: /^View / }).first(),
      ],
      { limit: TALL },
    );
  }

  // The record page of the study format 1 study, and the plot of its timecourse.
  await page.goto(`/data/${FORMAT1_STUDY}`);
  await capture(
    "study-details.png",
    [page.getByRole("region", { name: "Study status" }), page.getByRole("combobox", { name: "Study data category" })],
    { limit: TALL },
  );
  const category = page.getByRole("combobox", { name: "Study data category" });
  await category.focus();
  await category.press("ArrowDown");
  await page.getByRole("option", { name: "Timecourses", exact: true }).click();
  await page.getByRole("button", { name: /Fixture timecourse/ }).click();
  await page.getByRole("button", { name: "Show timecourse plot", exact: true }).click();
  await capture("timecourse.png", [
    page.getByRole("heading", { name: "Fixture timecourse", exact: true }),
    page.locator(".plot .main-svg").first(),
  ]);

  // The Studies page, and the study on Metadata and on Data.
  await page.goto("/studies");
  const studies = page.getByRole("table", { name: "Studies of PK-DB" });
  await capture("studies.png", [studies.getByRole("link", { name: STUDY, exact: true })]);
  await studies.getByRole("link", { name: STUDY, exact: true }).click();
  const sections = page.getByRole("navigation", { name: "Study sections" });
  await sections.getByRole("link", { name: /^Metadata/ }).click();
  await capture("study-metadata.png", [
    page.getByRole("heading", { name: STUDY, level: 1 }),
    page.getByText("Descriptions and comments", { exact: true }),
  ]);
  await sections.getByRole("link", { name: /^Data/ }).click();
  await showFigure(page);
  await capture("study-data.png", [page.locator(".overlay-host .main-svg").first()], { panes: true });
}

/** The images of the pages as the curator of the studies sees them. */
async function curatorPages(page, capture) {
  await page.goto("/studies");
  const studies = page.getByRole("table", { name: "Studies of PK-DB" });
  await capture("studies-curator.png", [
    studies.getByRole("link", { name: STUDY, exact: true }),
    page.getByRole("group", { name: "Filter by status" }),
  ]);

  // Data: the digitization of the figure on its image, with its problem, beside the rows of its table.
  await studies.getByRole("link", { name: STUDY, exact: true }).click();
  const sections = page.getByRole("navigation", { name: "Study sections" });
  await sections.getByRole("link", { name: /^Data/ }).click();
  await showFigure(page);
  await capture(
    "study-curator-data.png",
    [page.getByRole("img", { name: /^Figure Fig1 with/ }), page.getByText("digitized_mismatch", { exact: true })],
    { panes: true },
  );

  // Review: all items, and the resolved issue about the subjects with its thread and its target row.
  await sections.getByRole("link", { name: /^Review/ }).click();
  await page.getByRole("group", { name: "Filter by state" }).getByRole("button", { name: /^All/ }).click();
  await page
    .getByRole("list", { name: "Review items" })
    .getByRole("button", { name: /^Issue/ })
    .click();
  await capture("study-curator-review.png", [
    page.getByRole("article", { name: "Issue" }),
    page.getByRole("region", { name: "Target" }).getByRole("table"),
  ]);
}

/** In the Data section, show the rows of the timecourses of the figure Fig1 beside the figure. */
async function showFigure(page) {
  const navigator = page.getByRole("navigation", { name: "Tables and sources" });
  await navigator.getByRole("button", { name: /^timecourses_Fig1/ }).click();
  await navigator.getByRole("button", { name: /^Fig1/ }).click();
  await page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv", exact: true }).waitFor();
  await page.getByRole("list", { name: "Series" }).waitFor();
}

/**
 * Save `name` once the page is ready: every locator of `ready` is visible, the fonts and images are
 * loaded, nothing loads, no menu or dialog is open, nothing animates, and the tab bars stand still.
 * With `panes`, the panes of the Data section end below their content and the separator stands
 * where no rows table cuts a column. The pointer rests on an empty spot of the header, so that
 * nothing shows a hover, and no control keeps the focus. The image shows the page from its top to
 * the end of its content, without the footer, whose release and commit change with every build.
 * The image of a page that is longer than `limit` ends above the first line of text that the limit
 * would cut. Every image starts in a window of the same size.
 */
async function screenshot(page, name, ready, { limit = Infinity, panes = false } = {}) {
  await page.evaluate(() => window.scrollTo(0, 0));
  for (const locator of ready) await locator.waitFor();
  await waitForPage(page);
  if (panes) {
    // The separator changes the width of the figure and so the height of its pane.
    await fitPanes(page);
    await alignColumns(page, await page.locator(".rows-scroll").filter({ visible: true }).all());
    await fitPanes(page);
  }
  await page.mouse.move(480, 32);
  await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
  await waitForPage(page);
  if (await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)) {
    throw new Error(`${name} scrolls sideways.`);
  }
  const cut = await cutColumns(page);
  if (cut.length) throw new Error(`${name} cuts a column of ${cut.join(", ")}.`);
  const height = await page.evaluate((limit) => {
    // The end of the content: the lowest child of the main element and the padding below it,
    // above the border of the footer.
    const main = document.querySelector("main");
    const padding = Number.parseFloat(getComputedStyle(main).paddingBottom);
    const end = Math.max(...[...main.children].map((child) => child.getBoundingClientRect().bottom)) + padding;
    const footer = document.querySelector("footer").getBoundingClientRect().top;
    let cut = Math.floor(Math.min(end, footer, limit));
    if (cut < limit) return cut;
    // Move the cut above every line of text that it would cross or that would end less than
    // a margin above it.
    const margin = 8;
    const lines = [];
    const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (!node.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const box of range.getClientRects()) if (box.height > 1) lines.push(box);
    }
    for (let moved = true; moved; ) {
      moved = false;
      for (const line of lines) {
        if (line.top < cut && line.bottom > cut - margin) {
          cut = Math.floor(line.top) - 1;
          moved = true;
        }
      }
    }
    return cut;
  }, limit);
  const path = join(destination, name);
  await page.screenshot({ path, caret: "hide", fullPage: true, clip: { x: 0, y: 0, width: WIDTH, height } });
  await page.setViewportSize({ width: WIDTH, height: HEIGHT });
  return path;
}

/** Wait until the fonts and images are loaded, nothing loads, no overlay is open and nothing moves. */
async function waitForPage(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.images].every((image) => image.complete));
  await page.waitForFunction(
    () =>
      !document.querySelector('[aria-busy="true"], .v-progress-linear--active, .v-skeleton-loader') &&
      !document.querySelector(".v-overlay--active"),
  );
  await settled(page);
  for (const tabs of await page.getByRole("tablist").all()) await alignTabs(tabs);
  await settled(page);
}

/** Run a script of the repository with the Python environment of python/, which `uv run` prepares. */
function python(script, ...args) {
  execFileSync("uv", ["run", "--project", join(repository, "python"), "python", join(repository, script), ...args], {
    stdio: ["ignore", "ignore", "inherit"],
  });
}

/** Run `pkdb` of python/ in `folder` with `environment`; its output goes to the error output only on a failure. */
function pkdb(folder, environment, ...args) {
  try {
    execFileSync("uv", ["run", "--project", join(repository, "python"), "pkdb", ...args], {
      cwd: folder,
      env: environment,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    throw new Error(`pkdb ${args[0]} failed: ${error.stdout ?? ""}${error.stderr ?? ""}`);
  }
}
