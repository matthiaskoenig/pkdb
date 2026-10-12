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
