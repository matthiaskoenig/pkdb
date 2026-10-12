import type { Locator, Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

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

/** The address of the PDF of Demo2020 in a tab of its own. */
const PAPER_TAB = "#/studies/caffeine/Demo2020/paper/Demo2020.pdf";

test("the Data section shows page 1 of Demo2020.pdf as the source Paper, first among the sources", async ({
  app,
  page,
}) => {
  // Fails until the paper is a source of the Data section (#917).
  test.fail();
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
