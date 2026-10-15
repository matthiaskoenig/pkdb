// Capture the screenshots of docs/web-interface.md from the disposable website of the browser tests,
// as README.md describes:
//   tools/website_docs/run.sh
// or, against a website of tools/frontend_testing that already runs:
//   node tools/website_docs/render.mjs
// The website shows only the artificial fixture data of tools/frontend_testing/serve.py. The renderer
// signs in as its account `curator`. It quantizes the images with ../curation_docs/optimize_png.py,
// which needs uv.
import { execFileSync } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../frontend/node_modules/playwright/index.mjs";
import { alignTabs, settled } from "../curation_docs/settle.mjs";

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
/** The account of the fixture that curates its study format 2 studies, and the password of every account. */
const CURATOR = "curator";
const PASSWORD = "Frontend-test-password-42!";
/** The public study format 2 study of the fixture, which `curator` curates, and its study format 1 study. */
const STUDY = "drug/Format2Public";
const FORMAT1_STUDY = "FRONTEND_SCOPE";

try {
  await mkdir(destination, { recursive: true });
  const written = await render();
  python("tools/curation_docs/optimize_png.py", ...written);
  for (const path of written) console.log(`Wrote ${path}`);
} catch (error) {
  console.error(error instanceof Error ? (error.stack ?? error.message) : String(error));
  process.exitCode = 1;
}

/** Capture the images, first as a visitor and then as the curator; the paths of the files. */
async function render() {
  const written = [];
  const browser = await chromium.launch();
  try {
    for (const pages of [visitorPages, curatorPages]) {
      const context = await browser.newContext({
        baseURL: website,
        viewport: { width: WIDTH, height: HEIGHT },
        deviceScaleFactor: 1,
        colorScheme: "light",
        reducedMotion: "reduce",
      });
      const page = await context.newPage();
      await pages(page, async (name, ready, options) => written.push(await screenshot(page, name, ready, options)));
      await context.close();
    }
  } finally {
    await browser.close();
  }
  return written;
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
  await capture("study-metadata.png", [page.getByRole("heading", { name: STUDY, level: 1 }), page.getByText("Plasma levels in mg/l.")]);
  await sections.getByRole("link", { name: /^Data/ }).click();
  const navigator = page.getByRole("navigation", { name: "Tables and sources" });
  await navigator.getByRole("button", { name: /^timecourses_Fig1/ }).click();
  await navigator.getByRole("button", { name: /^Fig1/ }).click();
  await capture("study-data.png", [
    page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv", exact: true }),
    page.getByRole("list", { name: "Series" }),
    page.locator(".overlay-host .main-svg").first(),
  ]);
}

/** The images of the pages as the curator of the study sees them. */
async function curatorPages(page, capture) {
  await page.goto("/account");
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(CURATOR);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("heading", { name: "Account settings", exact: true }).waitFor();

  await page.goto("/studies");
  const studies = page.getByRole("table", { name: "Studies of PK-DB" });
  await capture("studies-curator.png", [
    studies.getByRole("link", { name: STUDY, exact: true }),
    page.getByRole("group", { name: "Filter by status" }),
  ]);

  // Data: the outputs of Tab2 beside the image and the raw extraction of Tab2.
  await studies.getByRole("link", { name: STUDY, exact: true }).click();
  const sections = page.getByRole("navigation", { name: "Study sections" });
  await sections.getByRole("link", { name: /^Data/ }).click();
  const navigator = page.getByRole("navigation", { name: "Tables and sources" });
  await navigator.getByRole("button", { name: /^outputs_Tab2/ }).click();
  await navigator.getByRole("button", { name: /^Tab2/ }).click();
  await capture("study-curator-data.png", [
    page.getByRole("region", { name: "Rows of outputs_Tab2.tsv", exact: true }),
    page.getByText("Raw extraction", { exact: true }),
  ]);

  // Review: the open item, chosen, with its target rows.
  await sections.getByRole("link", { name: /^Review/ }).click();
  await page.getByRole("list", { name: "Review items" }).getByRole("button").first().click();
  await capture("study-curator-review.png", [page.getByRole("region", { name: "Target" }).getByRole("table")]);
}

/**
 * Save `name` once the page is ready: every locator of `ready` is visible, the fonts and images are
 * loaded, nothing loads, no menu or dialog is open, nothing animates, and the tab bars stand still.
 * The pointer rests on an empty spot of the header, so that nothing shows a hover, and no control
 * keeps the focus. The image shows the page from its top to the end of its content, without the
 * footer, whose release and commit change with every build. The image of a page that is longer
 * than `limit` ends above the first line of text that the limit would cut.
 */
async function screenshot(page, name, ready, { limit = Infinity } = {}) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.mouse.move(480, 32);
  await page.evaluate(() => document.activeElement instanceof HTMLElement && document.activeElement.blur());
  for (const locator of ready) await locator.waitFor();
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
  if (await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)) {
    throw new Error(`${name} scrolls sideways.`);
  }
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
  return path;
}

/** Run a script of the repository with the Python environment of python/, which `uv run` prepares. */
function python(script, ...args) {
  execFileSync("uv", ["run", "--project", join(repository, "python"), "python", join(repository, script), ...args], {
    stdio: ["ignore", "ignore", "inherit"],
  });
}
