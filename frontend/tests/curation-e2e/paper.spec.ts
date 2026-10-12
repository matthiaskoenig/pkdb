import { existsSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import type { Locator, Page } from "@playwright/test";
import { expect, runTool, test } from "./fixtures.ts";
import { pixelStats } from "./pixels.ts";

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
    "#/studies/caffeine/Demo2020/data?source=paper",
  );
  await expect(page.getByRole("link", { name: "PK-DB Local curation" })).toHaveCount(0);
  const viewer = page.locator(".paper-viewer");
  await expect(drawnPage(viewer)).toBeVisible();
  await expect(viewer.locator(".textLayer")).toContainText("Demo2020 is a synthetic test study of the PK-DB curation app.");
  await expect(page).toHaveTitle("Demo2020.pdf · caffeine/Demo2020 · PK-DB");
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

test("an image of a study still refuses to show in a frame", async ({ app, context }) => {
  await app.open("#/");
  // Its own page, whose console error of the refused frame is no error of the tests of the app.
  const probe = await context.newPage();
  try {
    // A page of the app, whose policy allows frames of its own origin; the files of a study forbid them.
    await probe.goto(`${app.server.origin}/`);
    const framed = await probe.evaluate(async (source) => {
      const frame = document.createElement("iframe");
      frame.src = source;
      document.body.append(frame);
      // An allowed frame shows the image in a document of this origin; a refused one shows the
      // error page of the browser, from another origin.
      for (let tries = 0; tries < 40; tries++) {
        await new Promise((resolve) => setTimeout(resolve, 50));
        if (frame.contentDocument?.querySelector("img")) return true;
      }
      return false;
    }, "/local/studies/caffeine/Demo2020/files/Demo2020_Fig1.png");
    expect(framed).toBe(false);
  } finally {
    await probe.close();
  }
});
