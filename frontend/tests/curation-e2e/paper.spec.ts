import { existsSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, runTool, test } from "./fixtures.ts";
import { inkColumns, pixelStats } from "./pixels.ts";

/** The source pane of the paper in the Data section, named after the PDF that it shows. */
function paperPane(page: Page, file: string): Locator {
  return page.getByRole("region", { name: `Paper ${file}` });
}

/** Page `number` of the PDF in `within` once PDF.js has drawn it. */
function drawnPage(within: Locator, number = 1): Locator {
  return within.locator(
    `.page[data-page-number="${number}"][data-loaded="true"]`,
  );
}

/** The list of the sources in the navigator of the Data section. */
function sourcesList(page: Page): Locator {
  return page
    .getByRole("navigation", { name: "Tables and sources" })
    .getByRole("list", { name: "Sources", exact: true });
}

/** The button of a source or a table file in the navigator of the Data section. */
function navigatorButton(page: Page, name: RegExp): Locator {
  return page.getByRole("navigation", { name: "Tables and sources" }).getByRole("button", { name });
}

/**
 * A PDF of `pages` letter pages, each with the line "Page <n> of <title>." in Helvetica, one of
 * the standard fonts of PDF readers. `title` is plain ASCII without parentheses or backslashes.
 */
function pdfOf(title: string, pages: number): Buffer {
  const kids = Array.from({ length: pages }, (_, index) => `${4 + 2 * index} 0 R`).join(" ");
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    `<< /Type /Pages /Kids [${kids}] /Count ${pages} >>`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  for (let page = 1; page <= pages; page += 1) {
    const text = `BT /F1 24 Tf 72 700 Td (Page ${page} of ${title}.) Tj ET`;
    objects.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${5 + 2 * (page - 1)} 0 R >>`,
      `<< /Length ${text.length} >>\nstream\n${text}\nendstream`,
    );
  }
  let pdf = "%PDF-1.4\n";
  const offsets = objects.map((object, index) => {
    const offset = pdf.length;
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
    return offset;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf, "latin1");
}

declare global {
  interface Window {
    /** The Content Security Policy violations of a tab that New tab opened. */
    __tabViolations: string[];
    /** The tops of an element in the animation frames after a navigation, while it is there. */
    __tops: number[];
  }
}

/** The address of the PDF of Demo2020 in a tab of its own. */
const PAPER_TAB = "#/studies/caffeine/Demo2020/paper/Demo2020.pdf";

test("the Data section shows page 1 of Demo2020.pdf as the source Paper, first among the sources", async ({
  app,
  page,
}) => {
  await app.open("#/studies/caffeine/Demo2020/data");
  const first = sourcesList(page).getByRole("button").first();
  await expect(first).toHaveAccessibleName(/^Paper\b/);
  await first.click();
  const pane = paperPane(page, "Demo2020.pdf");
  await expect(drawnPage(pane)).toBeVisible();
  await expect(pane.locator(".textLayer")).toContainText(
    "Demo2020 is a synthetic test study of the PK-DB curation app.",
  );
});

test("a PDF opens in a tab of its own without the app bar", async ({ app, page }) => {
  await app.open(PAPER_TAB);
  await expect(page.getByRole("heading", { name: "Demo2020.pdf", level: 1 })).toBeVisible();
  await expect(page.getByRole("link", { name: "caffeine/Demo2020" })).toHaveAttribute(
    "href",
    "#/studies/caffeine/Demo2020/data?source=paper&pdf=Demo2020.pdf",
  );
  await expect(page.getByRole("link", { name: "PK-DB Local curation" })).toHaveCount(0);
  const viewer = page.locator(".paper-viewer");
  await expect(drawnPage(viewer)).toBeVisible();
  await expect(viewer.locator(".textLayer")).toContainText("Demo2020 is a synthetic test study of the PK-DB curation app.");
  await expect(page).toHaveTitle("Demo2020.pdf · caffeine/Demo2020 · PK-DB");
});

/** How many animation frames `sampleTops` records. */
const FRAMES = 12;

/**
 * Record the top of `selector` in each of the next FRAMES animation frames that show it;
 * `window.__tops` holds them. A count of frames, not a time, as a busy runner draws few frames.
 */
async function sampleTops(page: Page, selector: string): Promise<void> {
  await page.evaluate(
    ({ target, frames }) => {
      window.__tops = [];
      const sample = (): void => {
        const element = document.querySelector(target);
        if (element) window.__tops.push(Math.round(element.getBoundingClientRect().top));
        if (window.__tops.length < frames) requestAnimationFrame(sample);
      };
      requestAnimationFrame(sample);
    },
    { target: selector, frames: FRAMES },
  );
}

/** The tops that `sampleTops` recorded, once it has all of them. */
async function sampledTops(page: Page): Promise<number[]> {
  await expect.poll(() => page.evaluate(() => window.__tops.length), { timeout: 10_000 }).toBe(FRAMES);
  return page.evaluate(() => window.__tops);
}

test("the pages of the app stand still when the app bar comes and goes between the tab of a PDF and the study", async ({
  app,
  page,
}) => {
  await app.open(PAPER_TAB);
  await expect(drawnPage(page.locator(".paper-viewer"))).toBeVisible();
  // The link back to the study: its header is below the app bar from the first frame on.
  await sampleTops(page, ".study-header");
  await page.getByRole("link", { name: "caffeine/Demo2020" }).click();
  const study = await sampledTops(page);
  expect(new Set(study)).toEqual(new Set([study.at(-1)]));
  expect(study.at(-1)).toBeGreaterThanOrEqual(36);
  // Back in the history to the tab: its head is at the top from the first frame on.
  await sampleTops(page, ".paper-page-head");
  await page.goBack();
  const tab = await sampledTops(page);
  expect(new Set(tab)).toEqual(new Set([0]));
});

for (const scheme of ["light", "dark"] as const) {
  test(`the stylesheet of PDF.js leaves the ${scheme} color scheme of the app to the whole page`, async ({ app, page }) => {
    await page.emulateMedia({ colorScheme: scheme });
    await app.open(PAPER_TAB);
    await expect(drawnPage(page.locator(".paper-viewer"))).toBeVisible();
    await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${scheme}( |$)`));
    await expect
      .poll(() => page.evaluate(() => getComputedStyle(document.documentElement).colorScheme))
      .toBe(scheme);
  });
}

test("find highlights the matches of a word, and Enter and Shift+Enter go through them", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const pane = paperPane(page, "Demo2020.pdf");
  await expect(drawnPage(pane)).toBeVisible();
  const find = pane.getByRole("searchbox", { name: "Find in the paper" });
  const count = pane.locator(".paper-count");
  // "the" is in "synthetic", "of the PK-DB" and "for the publication".
  await find.fill("the");
  await expect(count).toHaveText("1 of 3");
  await expect(pane.locator(".textLayer .highlight")).toHaveCount(3);
  // The highlights lie on the drawn words: the text layer covers the drawn page exactly.
  const [canvas, text] = await Promise.all([
    drawnPage(pane).locator("canvas").boundingBox(),
    drawnPage(pane).locator(".textLayer").boundingBox(),
  ]);
  for (const side of ["x", "y", "width", "height"] as const) expect(Math.abs(canvas![side] - text![side])).toBeLessThan(0.5);
  await expect(pane.locator(".textLayer .highlight.selected")).toHaveCount(1);
  await find.press("Enter");
  await expect(count).toHaveText("2 of 3");
  await find.press("Shift+Enter");
  await expect(count).toHaveText("1 of 3");
  await find.fill("xylophone");
  await expect(count).toHaveText("No matches");
  await find.fill("");
  await expect(count).toHaveText("");
  await expect(pane.locator(".textLayer .highlight")).toHaveCount(0);
});

test("a double click on a word that the page shows selects that word", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const drawn = drawnPage(paperPane(page, "Demo2020.pdf"));
  await expect(drawn).toBeVisible();
  // The line "Demo2020 is a synthetic test study of the PK-DB curation app." of the text layer
  // gives the band of the line; its words are where the canvas has ink.
  const line = drawn.locator(".textLayer span", { hasText: "synthetic test study" });
  const canvas = drawn.locator("canvas");
  const [lineBox, canvasBox] = [(await line.boundingBox())!, (await canvas.boundingBox())!];
  const top = Math.round(lineBox.y - canvasBox.y);
  const ink = await inkColumns(canvas, { x: 0, y: top, width: Math.floor(canvasBox.width), height: Math.round(lineBox.height) });
  // The last word, "app.": its letters stand at most 2 px apart, the words at least 3 px.
  const end = ink.lastIndexOf(true);
  let start = end;
  while (ink.slice(Math.max(start - 3, 0), start).includes(true)) start = ink.lastIndexOf(true, start - 1);
  await page.mouse.dblclick(canvasBox.x + (start + end) / 2, canvasBox.y + top + lineBox.height / 2);
  expect(await page.evaluate(() => document.getSelection()?.toString().trim())).toBe("app");
});

for (const width of [1440, 800, 390]) {
  test(`at Fit width the pages of the paper fit into the pane of a window ${width} px wide`, async ({ app, page }) => {
    await page.setViewportSize({ width, height: 900 });
    await app.open("#/studies/caffeine/Demo2020/data?source=paper");
    const pane = paperPane(page, "Demo2020.pdf");
    await expect(drawnPage(pane)).toBeVisible();
    await expect(pane.getByRole("combobox", { name: "Zoom" })).toHaveValue("page-width");
    const scroll = pane.locator(".paper-scroll");
    expect(await scroll.evaluate((element) => element.scrollWidth - element.clientWidth)).toBe(0);
  });
}

test("at Fit width the pages of the paper fit into a tab of its own", async ({ app, page }) => {
  await app.open(PAPER_TAB);
  const viewer = page.locator(".paper-viewer");
  await expect(drawnPage(viewer)).toBeVisible();
  expect(await viewer.locator(".paper-scroll").evaluate((element) => element.scrollWidth - element.clientWidth)).toBe(0);
});

test("Ctrl+F in the paper focuses its find field", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const pane = paperPane(page, "Demo2020.pdf");
  await expect(drawnPage(pane)).toBeVisible();
  await pane.locator(".paper-scroll").focus();
  await page.keyboard.press("Control+f");
  await expect(pane.getByRole("searchbox", { name: "Find in the paper" })).toBeFocused();
});

test("the paper keeps its zoom while a table of another source shows", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const pane = paperPane(page, "Demo2020.pdf");
  await expect(drawnPage(pane)).toBeVisible();
  const zoom = pane.getByRole("combobox", { name: "Zoom" });
  await zoom.selectOption("1");
  await expect(zoom).toHaveValue("1");
  await pane.locator(".pdfViewer").evaluate((element) => element.setAttribute("data-kept", "yes"));
  await navigatorButton(page, /^outputs_Tab2\.tsv/).click();
  await expect(page.getByRole("region", { name: "Source Tab2" })).toBeVisible();
  await expect(pane).toBeHidden();
  await navigatorButton(page, /^Paper\b/).click();
  await expect(pane).toBeVisible();
  await expect(pane.locator(".pdfViewer")).toHaveAttribute("data-kept", "yes");
  await expect(zoom).toHaveValue("1");
});

test("the paper keeps its page while a table of another source shows, and when the panes stack", async ({
  app,
  page,
}) => {
  const pdf = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Long.pdf");
  writeFileSync(pdf, pdfOf("the long paper", 3));
  try {
    await app.open("#/studies/caffeine/Demo2020/data?source=paper");
    const choice = page.getByRole("combobox", { name: "PDF of the paper" });
    await choice.selectOption("Demo2020_Long.pdf");
    const pane = paperPane(page, "Demo2020_Long.pdf");
    await expect(drawnPage(pane)).toBeVisible();
    const pageField = pane.getByRole("spinbutton", { name: "Page" });
    await pageField.fill("3");
    await pageField.press("Enter");
    await expect(drawnPage(pane, 3)).toBeInViewport();
    await expect(pageField).toHaveValue("3");

    await navigatorButton(page, /^outputs_Tab2\.tsv/).click();
    await expect(page.getByRole("region", { name: "Source Tab2" })).toBeVisible();
    await expect(pane).toBeHidden();
    await navigatorButton(page, /^Paper\b/).click();
    await expect(drawnPage(pane, 3)).toBeInViewport();
    await expect(pageField).toHaveValue("3");

    // The pane mounts again below 960 px, and the viewer opens the PDF on its page again.
    await page.setViewportSize({ width: 900, height: 900 });
    await expect(page.locator(".data-stack")).toBeVisible();
    await expect(drawnPage(pane, 3)).toBeInViewport();
    await expect(pageField).toHaveValue("3");
  } finally {
    rmSync(pdf);
  }
});

test("the address names the PDF chosen in the head of the pane, so that a reload and the link back from its tab show it", async ({
  app,
  page,
}) => {
  const pdf = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Long.pdf");
  writeFileSync(pdf, pdfOf("the long paper", 3));
  try {
    await app.open("#/studies/caffeine/Demo2020/data?source=paper");
    await expect(navigatorButton(page, /^Paper\b/)).toHaveAccessibleName("Paper Demo2020.pdf and 1 more PDF");
    await page.getByRole("combobox", { name: "PDF of the paper" }).selectOption("Demo2020_Long.pdf");
    const pane = paperPane(page, "Demo2020_Long.pdf");
    await expect(drawnPage(pane)).toBeVisible();
    await expect.poll(() => new URL(page.url()).hash).toContain("source=paper&pdf=Demo2020_Long.pdf");
    await page.reload();
    await expect(drawnPage(pane)).toBeVisible();
    await expect(pane.locator(".textLayer").first()).toContainText("Page 1 of the long paper.");
    await app.open("#/studies/caffeine/Demo2020/paper/Demo2020_Long.pdf");
    await page.getByRole("link", { name: "caffeine/Demo2020" }).click();
    await expect(drawnPage(pane)).toBeVisible();
    await expect(pane.locator(".textLayer").first()).toContainText("Page 1 of the long paper.");
  } finally {
    rmSync(pdf);
  }
});

test("a quick switch between the PDFs of a study shows the PDF chosen last", async ({ app, page }) => {
  const pdf = join(app.server.workspace, "caffeine/Demo2020/Demo2020_Long.pdf");
  writeFileSync(pdf, pdfOf("the long paper", 3));
  try {
    await app.open("#/studies/caffeine/Demo2020/data?source=paper");
    const choice = page.getByRole("combobox", { name: "PDF of the paper" });
    await expect(drawnPage(paperPane(page, "Demo2020.pdf"))).toBeVisible();
    // Each choice starts to load its PDF before the next one comes.
    for (const file of ["Demo2020_Long.pdf", "Demo2020.pdf", "Demo2020_Long.pdf", "Demo2020.pdf", "Demo2020_Long.pdf"])
      await choice.selectOption(file);
    const pane = paperPane(page, "Demo2020_Long.pdf");
    await expect(drawnPage(pane)).toBeVisible();
    await expect(pane.locator(".textLayer").first()).toContainText("Page 1 of the long paper.");
    await expect(pane.locator(".page")).toHaveCount(3);
    await expect(pane.locator(".paper-of")).toHaveText("of 3");
    await expect(pane.getByRole("alert")).toHaveCount(0);
  } finally {
    rmSync(pdf);
  }
});

test("a study without a PDF shows the paper as a disabled source, and the paper again once the PDF is back", async ({
  app,
  page,
}) => {
  // Legacy1990 of the fixture is a study format 1 folder, which the app does not open: Draft2021 lends its PDF.
  const pdf = join(app.server.workspace, "caffeine/Draft2021/Draft2021.pdf");
  await app.open("#/studies/caffeine/Draft2021/data?source=paper");
  await expect(drawnPage(paperPane(page, "Draft2021.pdf"))).toBeVisible();
  // The study page has the ETag of the files as the watcher of the local server last scanned
  // them. Once the watcher has seen the PDF go, it sees it come back as a change too.
  const filesVersion = async () =>
    ((await (await page.request.get(`${app.server.origin}/local/studies/caffeine/Draft2021`)).json()) as { files_version: string })
      .files_version;
  const withPdf = await filesVersion();
  renameSync(pdf, `${pdf}.away`);
  const paper = sourcesList(page).getByRole("button").first();
  try {
    await expect.poll(filesVersion).not.toBe(withPdf);
    // The app opens again on the address of the paper, which the study lacks now.
    await page.reload();
    await expect(paper).toBeDisabled();
    await expect(paper).toContainText("No Draft2021.pdf");
    // The address asks for the paper, which the study lacks: its table shows beside its source.
    await expect(page.getByRole("region", { name: /^Source / })).toBeVisible();
    await expect(page.getByRole("region", { name: /^Paper / })).toHaveCount(0);
  } finally {
    renameSync(`${pdf}.away`, pdf);
  }
  await expect(paper).toBeEnabled();
  await expect(drawnPage(paperPane(page, "Draft2021.pdf"))).toBeVisible();
});

test("Open in PDF program opens the PDF with the program of the system", async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const pane = paperPane(page, "Demo2020.pdf");
  await pane.getByRole("button", { name: "Open in PDF program" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Demo2020.pdf opened in the PDF program." })).toHaveCount(1);
  const pdf = join(app.server.workspace, "caffeine/Demo2020/Demo2020.pdf");
  await expect
    .poll(() => (existsSync(app.server.openLog) ? readFileSync(app.server.openLog, "utf8").split("\n") : []))
    .toContain(pdf);
});

test("New tab opens the paper in a tab of its own in the same session", async ({ app, page, context }) => {
  await context.addInitScript(() => {
    window.__tabViolations = [];
    document.addEventListener("securitypolicyviolation", (event) =>
      window.__tabViolations.push(`${event.violatedDirective} ${event.blockedURI}`),
    );
  });
  await app.open("#/studies/caffeine/Demo2020/data?source=paper");
  const pane = paperPane(page, "Demo2020.pdf");
  await expect(drawnPage(pane)).toBeVisible();
  const [tab] = await Promise.all([context.waitForEvent("page"), pane.getByRole("link", { name: "New tab" }).click()]);
  await expect.poll(() => new URL(tab.url()).hash).toBe("#/studies/caffeine/Demo2020/paper/Demo2020.pdf");
  await expect(tab.getByRole("heading", { name: "Demo2020.pdf", level: 1 })).toBeVisible();
  await expect(drawnPage(tab.locator(".paper-viewer"))).toBeVisible();
  await expect(tab.locator(".textLayer")).toContainText("Demo2020 is a synthetic test study of the PK-DB curation app.");
  expect(await tab.evaluate(() => window.__tabViolations)).toEqual([]);
  await tab.close();
});

test("the paper beside the rows leaves the layout of the page to the Data section in a narrow window", async ({
  app,
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await app.open("#/studies/caffeine/Demo2020/data?source=paper&file=subjects.tsv");
  await expect(drawnPage(paperPane(page, "Demo2020.pdf"))).toBeVisible();
  // The page scrolls as a whole, so the reason why Upload is disabled stays on a line of its own
  // below the actions of the study header.
  const upload = await page.getByRole("button", { name: "Upload", exact: true }).boundingBox();
  const reason = await page.locator(".upload-reason").boundingBox();
  expect(reason!.y).toBeGreaterThanOrEqual(upload!.y + upload!.height);
  expect(reason!.height).toBeLessThan(40);
  const rows = page.getByRole("region", { name: "Rows of subjects.tsv" });
  await rows.scrollIntoViewIfNeeded();
  await expect(rows).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollTop)).toBeGreaterThan(0);
});

test("the JavaScript decoders draw the CCITT and JPEG 2000 images of a PDF without WebAssembly", async ({ app, page }) => {
  // In Draft2021, so that the PDFs of Demo2020 stay as the other tests expect them; removed again below.
  const pdf = join(app.server.workspace, "caffeine/Draft2021/Draft2021_Decoders.pdf");
  await runTool("decoders_pdf.py", pdf);
  try {
    const requests: string[] = [];
    page.on("request", (request) => requests.push(new URL(request.url()).pathname));
    // The worker of PDF.js has its own console; a violation there never reaches the listener of the page.
    const policy: string[] = [];
    page.on("console", (message) => {
      if (message.worker() && /content security policy/i.test(message.text())) policy.push(message.text());
    });
    await app.open("#/studies/caffeine/Draft2021/data?source=paper");
    const pane = page.getByRole("region", { name: /^Paper / });
    await pane.getByRole("combobox", { name: "PDF of the paper" }).selectOption("Draft2021_Decoders.pdf");
    await expect(drawnPage(pane, 1)).toBeVisible();
    const black = (await pixelStats(pane.locator('.page[data-page-number="1"] canvas'))).dominant;
    expect(Math.max(...black)).toBeLessThan(30);
    await pane.getByRole("button", { name: "Next page" }).click();
    await expect(pane.getByRole("spinbutton", { name: "Page" })).toHaveValue("2");
    await expect(drawnPage(pane, 2)).toBeVisible();
    const [red, green, blue] = (await pixelStats(pane.locator('.page[data-page-number="2"] canvas'))).dominant;
    expect([red > 200, green < 30, blue < 30]).toEqual([true, true, true]);
    expect(requests).toEqual(
      expect.arrayContaining(["/pdfjs/wasm/jbig2_nowasm_fallback.js", "/pdfjs/wasm/openjpeg_nowasm_fallback.js"]),
    );
    expect(requests.filter((path) => path.endsWith(".wasm"))).toEqual([]);
    expect(policy).toEqual([]);
  } finally {
    rmSync(pdf, { force: true });
  }
});

test("an image and a PDF of a study refuse to show in a frame, which the page of the app may show them in", async ({
  app,
  context,
  playwright,
}) => {
  await app.open("#/");
  // Chromium itself, in a browser of its own: its headless shell, which runs the tests, has no PDF
  // viewer and downloads a PDF in a frame, which is no frame to refuse. Its console errors of the
  // refused frames are no errors of the tests of the app.
  const browser = await playwright.chromium.launch({ channel: "chromium" });
  try {
    const session = await browser.newContext();
    await session.addCookies(await context.cookies());
    const probe = await session.newPage();
    // A page of the app, whose policy allows frames of its own origin; the files of a study forbid them.
    await probe.goto(`${app.server.origin}/`);
    const shown = await probe.evaluate(
      async ({ image, pdf }) => {
        /** A frame with `attributes` in the page, once it has loaded, or after 3 s. */
        const frameOf = async (attributes: Partial<HTMLIFrameElement>): Promise<HTMLIFrameElement> => {
          const frame = Object.assign(document.createElement("iframe"), attributes);
          const loaded = new Promise((resolve) => {
            frame.addEventListener("load", resolve, { once: true });
            setTimeout(resolve, 3000);
          });
          document.body.append(frame);
          await loaded;
          return frame;
        };
        /**
         * Whether a frame of the file at `source` is refused: it then shows the error page of the
         * browser, from another origin. An allowed frame shows the image, or the PDF in the PDF
         * viewer, in a document of this origin.
         */
        const refused = async (source: string): Promise<boolean> => (await frameOf({ src: source })).contentDocument === null;
        // The controls: both files are there, and the image shows in a frame of the page itself.
        const answers = await Promise.all([image, pdf].map(async (source) => (await fetch(source)).status));
        const own = await frameOf({ srcdoc: `<img src="${image}" alt="">` });
        const control = (own.contentDocument?.querySelector("img")?.naturalWidth ?? 0) > 0;
        return { answers, control, refused: [await refused(image), await refused(pdf)] };
      },
      {
        image: "/local/studies/caffeine/Demo2020/files/Demo2020_Fig1.png",
        pdf: "/local/studies/caffeine/Demo2020/files/Demo2020.pdf",
      },
    );
    expect(shown).toEqual({ answers: [200, 200], control: true, refused: [true, true] });
  } finally {
    await browser.close();
  }
});
