import AxeBuilder from "@axe-core/playwright";
import { expect, test, type BrowserContext, type Locator, type Page } from "@playwright/test";

test.use({ screenshot: "off" });

const password = "Frontend-test-password-42!";
/** Private, curated by `curator`: the curation view. */
const sid = "drug/Format2Fixture";
const address = `/data/${sid}`;
/** Public, also curated by `curator`: the public view for everyone else (tools/frontend_testing/serve.py). */
const publicSid = "drug/Format2Public";
const publicAddress = `/data/${publicSid}`;
const PUBLIC_COLUMNS = ["Study", "Release", "Curators"];
const CURATOR_COLUMNS = ["Study", "Release", "Issue", "Curators", "Review", "Open items", "Problems"];
const CURATOR_TABS = [/^Metadata/, /^Data/, /^Problems/, /^Review/];

async function login(page: Page, username: string): Promise<void> {
  await page.goto("/account");
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Account settings", exact: true })).toBeVisible();
}

/** The requests of `page` for a file of a study or for PDF.js. */
function fileRequests(page: Page): string[] {
  const urls: string[] = [];
  page.on("request", (sent) => {
    if (/\/view\/files\/|\/pdfjs\//.test(sent.url())) urls.push(sent.url());
  });
  return urls;
}

/** The page in the light and the dark theme at 1280, 1440 and 390 px: no horizontal scroll, no axe violation, a screenshot of each. */
async function looksRight(page: Page, name: string): Promise<void> {
  const toggle = page.getByRole("button", { name: "Toggle color theme" });
  for (const theme of ["light", "dark"]) {
    for (const width of [1280, 1440, 390]) {
      await page.setViewportSize({ width, height: 900 });
      // The colors of the theme change in transitions; axe reads the colors where they end.
      await page.evaluate(() =>
        Promise.all(
          document
            .getAnimations()
            .filter((animation) => animation instanceof CSSTransition)
            .map((animation) => animation.finished.catch(() => undefined)),
        ),
      );
      await expect
        .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
        .toBe(0);
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
      expect(results.violations, `${name}, ${theme}, ${width} px`).toEqual([]);
      await page.screenshot({ path: test.info().outputPath(`${name}-${theme}-${width}.png`), fullPage: true });
    }
    await toggle.click();
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}

/** Whether `element` shows no focus ring. */
const ringless = (element: Locator) =>
  element.evaluate((node) => {
    const style = getComputedStyle(node);
    return style.outlineStyle === "none" || Number.parseFloat(style.outlineWidth) === 0;
  });

/** Where the data search left off: its address, the history length, the scroll position and the focused button. */
const searchState = (page: Page) =>
  page.evaluate(() => ({
    url: window.location.pathname + window.location.search,
    length: window.history.length,
    y: Math.round(window.scrollY),
    focus: document.activeElement?.getAttribute("aria-label") ?? null,
  }));

/**
 * Open `study` from the Studies tab of the data search, scrolled so that the search has to restore its
 * position, and return the state of the search before the study opened.
 */
async function openFromSearch(page: Page, study: string) {
  await page.setViewportSize({ width: 1280, height: 480 });
  await page.goto("/data");
  await page.getByRole("tab", { name: /^Studies / }).click();
  await expect(page).toHaveURL(/tab=studies/);
  const view = page.getByRole("button", { name: `View ${study}`, exact: true });
  await view.scrollIntoViewIfNeeded();
  await view.focus();
  const before = await searchState(page);
  expect(before.y).toBeGreaterThan(0);
  expect(before.focus).toBe(`View ${study}`);
  await view.click();
  return before;
}

/** "Back to the search" goes back in the history to the search, where the reader left it. */
async function backToSearch(page: Page, before: Awaited<ReturnType<typeof searchState>>, study: string) {
  const length = await page.evaluate(() => window.history.length);
  await page.getByRole("button", { name: "Back to the search", exact: true }).click();
  await expect.poll(() => page.evaluate(() => window.location.pathname + window.location.search)).toBe(before.url);
  await expect(page.getByRole("button", { name: `View ${study}`, exact: true })).toBeFocused();
  const after = await searchState(page);
  expect(after.length).toBe(length);
  expect(Math.abs(after.y - before.y)).toBeLessThanOrEqual(2);
  // The entry of the study that the search opened stays ahead in the history.
  const forward = await page.evaluate(() => {
    const state: unknown = window.history.state;
    return typeof state === "object" && state !== null && "forward" in state ? state.forward : null;
  });
  expect(forward).toEqual(expect.stringMatching(new RegExp(`^/data/${study}[/?]`)));
  await page.setViewportSize({ width: 1280, height: 900 });
}

const sectionTabs = (page: Page) => page.getByRole("navigation", { name: "Study sections" }).getByRole("link");
const studyTable = (page: Page) => page.getByRole("table", { name: "Studies of PK-DB" });

test("a visitor lists the public study with its public columns and reads its metadata and data, without any file", async ({ page }) => {
  const files = fileRequests(page);
  await page.goto("/studies");
  await expect(studyTable(page).getByRole("columnheader")).toHaveText(PUBLIC_COLUMNS);
  // The private study is not listed.
  await expect(studyTable(page).locator("tr.study-row")).toHaveCount(1);
  await expect(studyTable(page).getByRole("link", { name: sid, exact: true })).toHaveCount(0);
  await expect(page.getByRole("group", { name: "Filter by status" })).toHaveCount(0);
  await looksRight(page, "studies-public");
  await studyTable(page).getByRole("link", { name: publicSid, exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${publicAddress}/metadata$`));
  const heading = page.getByRole("heading", { name: publicSid, level: 1 });
  await expect(heading).toBeFocused();
  // The heading takes the focus without a ring.
  await expect(heading).toHaveClass(/study-identity/);
  expect(await ringless(heading)).toBe(true);
  await expect(sectionTabs(page)).toHaveText(["Metadata", "Data"]);
  await expect(page.getByRole("link", { name: /GitHub issue/ })).toHaveCount(0);
  await looksRight(page, "study-public-metadata");
  await page.goto(`${publicAddress}/data?file=outputs_Tab2.tsv`);
  await expect(page.getByText("The image and the raw extraction of this table are not public.")).toBeVisible();
  await expect(page.locator(".rows-pane")).toContainText("gmean");
  await looksRight(page, "study-public-data");
  // A link to a section that the reader does not see opens the study where it starts.
  await page.goto(`${publicAddress}/review`);
  await expect(page).toHaveURL(new RegExp(`${publicAddress}/metadata$`));
  // A visitor never asks for a file of a study nor for PDF.js.
  expect(files).toEqual([]);
});

test("a visitor goes back from a study that the search opened at a section they may not see to where the search was", async ({ page }) => {
  const before = await openFromSearch(page, publicSid);
  // The search opens the study without a section; the study starts where the visitor may read it.
  await expect(page).toHaveURL(new RegExp(`${publicAddress}/metadata\\?.*v=1`));
  await expect(page.getByRole("heading", { name: publicSid, level: 1 })).toBeFocused();
  await backToSearch(page, before, publicSid);
});

test("a link that sorts or filters by the curation opens the list as a visitor sees it", async ({ page }) => {
  await page.goto("/studies?sort=review&order=desc&status=attention&substance=drug");
  await expect(page).toHaveURL(/\/studies\?substance=drug$/);
  await expect(studyTable(page).getByRole("columnheader")).toHaveText(PUBLIC_COLUMNS);
});

test("a signed-in reader who may not write a study sees the public view and not the private study", async ({ page, browserName }) => {
  await login(page, `reader-${browserName}`);
  await page.goto("/studies");
  await expect(studyTable(page).getByRole("columnheader")).toHaveText(PUBLIC_COLUMNS);
  await expect(studyTable(page).locator("tr.study-row")).toHaveCount(1);
  await page.goto(publicAddress);
  await expect(page).toHaveURL(new RegExp(`${publicAddress}/metadata$`));
  await expect(sectionTabs(page)).toHaveText(["Metadata", "Data"]);
  // The private study has no view for this reader: its record page says it is not found.
  await page.goto(address);
  await expect(page.getByRole("alert")).toContainText("Not found");
  await expect(page.getByRole("navigation", { name: "Study sections" })).toHaveCount(0);
});

// The login of an account is throttled, so the curator signs in once per browser.
test.describe("the curation view of the assigned curator", () => {
  test.describe.configure({ mode: "serial" });
  let context: BrowserContext;
  let page: Page;
  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    await login(page, "curator");
  });
  test.afterAll(async () => {
    await context.close();
  });

  test("lists the study with its curation, sorts by it and opens the study on its open item", async () => {
    await page.goto("/studies");
    await expect(studyTable(page).getByRole("columnheader")).toHaveText(CURATOR_COLUMNS);
    await expect(page.getByRole("group", { name: "Filter by status" })).toBeVisible();
    const row = studyTable(page).locator(`tr[data-study="${sid}"]`);
    await expect(row.getByRole("link", { name: "GitHub issue #2158" })).toHaveAttribute(
      "href",
      "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    );
    await expect(row.locator(".cell-review")).toContainText("In review");
    await expect(row.locator(".cell-open")).toHaveText("1");
    await studyTable(page).getByRole("button", { name: "Review", exact: true }).click();
    await expect(page).toHaveURL(/\/studies\?sort=review$/);
    await looksRight(page, "studies-curator");
    await row.getByRole("link", { name: sid, exact: true }).click();
    await expect(page).toHaveURL(new RegExp(`${address}/review$`));
    await expect(sectionTabs(page)).toHaveText(CURATOR_TABS);
    await expect(page.getByRole("link", { name: "GitHub issue #2158" })).toBeVisible();
    await expect(page.locator(".fact-review")).toHaveText("In review");
    await expect(page.getByText("Is the geometric mean read from the table?").first()).toBeVisible();
    for (const name of ["Resolve", "Dismiss", "Reopen"])
      await expect(page.getByRole("button", { name, exact: true })).toHaveCount(0);
    await looksRight(page, "study-curator-review");
  });

  test("shows the paper, the images and the raw table, and loads PDF.js only for the paper", async () => {
    const files = fileRequests(page);
    const pdfjs = () => files.filter((url) => url.includes("/pdfjs/"));
    await page.goto(`${address}/metadata`);
    await expect(page.getByRole("heading", { name: sid, level: 1 })).toBeVisible();
    await expect(page.getByText("PKDB09901").first()).toBeVisible();
    // The Data section opens on the first table, not on the paper.
    await sectionTabs(page).filter({ hasText: /^Data/ }).click();
    await expect(page).toHaveURL(new RegExp(`${address}/data\\?source=Tab2&file=outputs_Tab2\\.tsv$`));
    await expect(page.locator(".rows-pane")).toContainText("outputs_Tab2.tsv");
    expect(pdfjs()).toEqual([]);
    await page.goto(`${address}/data?source=paper`);
    await expect(page.locator(".paper-pane .textLayer")).toContainText("Format2Fixture paper");
    expect(pdfjs().some((url) => url.endsWith("/pdfjs/pdf.worker.min.mjs"))).toBe(true);
    await looksRight(page, "study-curator-paper");
    await page.goto(`${address}/data?source=Tab1`);
    const image = page.locator('img[src$="/view/files/Format2Fixture_Tab1.png"]').first();
    await expect.poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth)).toBe(240);
    await page.goto(`${address}/data?file=Format2Fixture_Tab2.tsv`);
    await expect(page.locator(".rows-pane")).toContainText("Concentration (mg/l)");
  });

  test("gives the side-by-side panes of the Data section the height of the window, each scrolling on its own", async () => {
    await page.goto(`${address}/data?file=outputs_Tab2.tsv`);
    const panes = page.locator(".data-panes");
    for (const width of [1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(panes).toHaveClass(/(^| )data-panes--sized( |$)/);
      await expect(page.locator(".source-pane")).toBeVisible();
      await expect(page.locator(".rows-pane")).toBeVisible();
      await panes.evaluate((element) => element.scrollIntoView({ block: "end" }));
      const layout = await page.evaluate(() => {
        const box = (selector: string) => {
          const element = document.querySelector(selector);
          if (!element) throw new Error(`${selector} is missing`);
          const rect = element.getBoundingClientRect();
          const style = getComputedStyle(element);
          return {
            top: rect.top,
            bottom: rect.bottom,
            overflowY: style.overflowY,
            scrolls: element.scrollHeight > element.clientHeight,
          };
        };
        const top = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--v-layout-top")) || 0;
        return {
          top,
          viewport: window.innerHeight,
          panes: box(".data-panes"),
          source: box(".source-pane"),
          sourceScroll: box(".source-pane .pane-body"),
          rows: box(".rows-pane"),
          rowsScroll: box(".rows-pane .rows-scroll"),
        };
      });
      // The window below the app bar, less 16 px, at least 480 px.
      const height = layout.panes.bottom - layout.panes.top;
      expect(Math.abs(height - Math.max(480, layout.viewport - 64 - 16))).toBeLessThanOrEqual(1);
      expect(layout.panes.bottom).toBeLessThanOrEqual(layout.viewport + 0.5);
      expect(layout.panes.top).toBeGreaterThanOrEqual(64 - 0.5);
      for (const [pane, scroller] of [
        [layout.source, layout.sourceScroll],
        [layout.rows, layout.rowsScroll],
      ] as const) {
        // The pane ends inside the panes and the window, and its body scrolls on its own.
        expect(pane.bottom).toBeLessThanOrEqual(layout.panes.bottom + 0.5);
        expect(scroller.bottom).toBeLessThanOrEqual(layout.panes.bottom + 0.5);
        expect(["auto", "scroll"]).toContain(scroller.overflowY);
      }
    }
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("goes back from a section switch of a study that the search opened to where the search was", async () => {
    const before = await openFromSearch(page, sid);
    // The search opens the study on its default section, then the reader switches to Data.
    await expect(page).toHaveURL(new RegExp(`${address}/review\\?.*v=1`));
    await expect(page.getByRole("heading", { name: sid, level: 1 })).toBeFocused();
    await sectionTabs(page).filter({ hasText: /^Data/ }).click();
    await expect(page).toHaveURL(new RegExp(`${address}/data\\?.*v=1`));
    await backToSearch(page, before, sid);
  });

  test("keeps a chosen review item below the app bar on a phone", async () => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${address}/review`);
    const card = page.getByRole("list", { name: "Review items" }).getByRole("button").first();
    await expect(card).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await card.click();
    await expect
      .poll(() => page.locator(".review-selected").evaluate((element) => element.getBoundingClientRect().top))
      .toBeGreaterThanOrEqual(64);
    await page.setViewportSize({ width: 1280, height: 900 });
  });

  test("shows a study format 2 study without a stored view on its record page", async () => {
    await page.goto("/data/drug/Format2Legacy");
    await expect(page.getByRole("region", { name: "Study status" })).toContainText("PKDB09902");
    await expect(page.getByRole("navigation", { name: "Study sections" })).toHaveCount(0);
  });
});

test("an administrator sees the curation view of a study that they are not assigned to", async ({ page }) => {
  await login(page, "administrator");
  await page.goto("/studies");
  await expect(studyTable(page).getByRole("columnheader")).toHaveText(CURATOR_COLUMNS);
  await page.goto(address);
  await expect(page).toHaveURL(new RegExp(`${address}/review$`));
  await expect(sectionTabs(page)).toHaveText(CURATOR_TABS);
});
