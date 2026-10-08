import type { Page } from "@playwright/test";
import { expect, setAutomaticActions, test } from "./fixtures.ts";

function studies(page: Page) {
  return page.getByRole("table", { name: "Studies of the workspace" });
}

/** The rows of the studies below the header row. */
function studyRows(page: Page) {
  return studies(page).getByRole("rowgroup").nth(1).getByRole("row");
}

function studyRow(page: Page, id: string) {
  return studies(page).getByRole("row", { name: new RegExp(`^Select ${id} `) });
}

function chip(page: Page, label: string) {
  return page.getByRole("group", { name: "Filter by status" }).getByRole("button", { name: new RegExp(`^${label} \\d+$`) });
}

/** Wait until the first validation of both studies has finished. */
async function validated(page: Page): Promise<void> {
  await expect(studyRow(page, "caffeine/Demo2020").getByRole("cell", { name: "2 warnings" })).toBeVisible();
  await expect(studyRow(page, "caffeine/Draft2021").getByRole("cell", { name: "1 error" })).toBeVisible();
}

test.beforeEach(async ({ app }) => {
  await app.open();
});

test("lists the format 2 studies of the workspace and counts the format 1 folder", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Studies", level: 1 })).toBeVisible();
  await expect(studyRows(page)).toHaveCount(2);
  await expect(studyRow(page, "caffeine/Demo2020")).toContainText(
    "Caffeine in plasma after two oral doses in a synthetic test study",
  );
  await expect(studyRow(page, "caffeine/Draft2021")).toContainText("A synthetic draft study of caffeine tablets");
  await expect(page.getByText("1 study format 1 folder is not listed.")).toHaveText(
    "1 study format 1 folder is not listed. It stays on the released app version until it is converted.",
  );
  await expect(page.getByRole("banner").getByText("curator", { exact: true })).toBeVisible();
  await validated(page);
});

test("the labels of the column headers share one baseline", async ({ page }) => {
  await expect(studyRows(page)).toHaveCount(2);
  // The box of the text of each label: with one font, equal bottoms mean one baseline.
  const labels = await studies(page)
    .getByRole("columnheader")
    .evaluateAll((headers) =>
      headers.flatMap((header) => {
        const text = document.createTreeWalker(header, NodeFilter.SHOW_TEXT, {
          acceptNode: (node) => (node.textContent?.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT),
        }).nextNode();
        if (!text) return [];
        const range = document.createRange();
        range.selectNodeContents(text);
        return [{ label: text.textContent?.trim() ?? "", bottom: range.getBoundingClientRect().bottom }];
      }),
    );
  expect(labels.map((entry) => entry.label)).toEqual([
    "Study",
    "Review",
    "Open items",
    "Problems",
    "Sync",
    "Release",
    "Issue",
    "Curators",
    "On save",
    "Last upload",
  ]);
  const bottoms = labels.map((entry) => entry.bottom);
  expect(Math.max(...bottoms) - Math.min(...bottoms), JSON.stringify(labels)).toBeLessThanOrEqual(1);
});

test("filters the studies by search and status", async ({ page }) => {
  await validated(page);
  const search = page.getByRole("textbox", { name: "Search studies" });
  await search.fill("draft2021");
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await expect(page.getByText("1 of 2 studies")).toBeVisible();
  // The title matches too.
  await search.fill("two oral doses");
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Demo2020")).toBeVisible();
  await page.getByRole("button", { name: "Clear Search studies" }).click();
  await expect(studyRows(page)).toHaveCount(2);

  // Draft2021 has an error; Demo2020 is in review with open items.
  await chip(page, "Needs attention").click();
  await expect(chip(page, "Needs attention")).toHaveAttribute("aria-pressed", "true");
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await expect(studyRows(page)).toHaveCount(2);
  await chip(page, "Draft").click();
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Draft2021")).toBeVisible();
  await chip(page, "In review").click();
  await expect(studyRows(page)).toHaveCount(1);
  await expect(studyRow(page, "caffeine/Demo2020")).toBeVisible();
  await chip(page, "Approved").click();
  await expect(page.getByText("No studies match these filters.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(chip(page, "All")).toHaveAttribute("aria-pressed", "true");
  await expect(studyRows(page)).toHaveCount(2);
});

test("Validate queues a job, and the study shows it until it ran", async ({ page }) => {
  await validated(page);
  // While automatic actions are paused, the job waits in the queue.
  await setAutomaticActions(page, true);
  const row = studyRow(page, "caffeine/Draft2021");
  await row.getByRole("checkbox", { name: "Select caffeine/Draft2021" }).check();
  await expect(page.getByText("1 study selected")).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Validation queued for 1 study." })).toBeVisible();
  await expect(row.getByText("Queued", { exact: true })).toBeVisible();

  await setAutomaticActions(page, false);
  await expect(row.getByText("Queued", { exact: true })).toBeHidden();
  await expect(row.getByRole("cell", { name: "1 error" })).toBeVisible();
});

test("a dialog returns the keyboard focus to the control that opened it", async ({ page }) => {
  const settings = page.getByRole("button", { name: "Settings", exact: true });
  await settings.focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Connection settings" });
  await expect(dialog).toBeVisible();
  // The dialog takes the focus once it shows; Escape closes it from there.
  await expect.poll(() => dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(settings).toBeFocused();

  // An item of a menu goes with the menu: the focus returns to the button of the menu.
  const connection = page.getByRole("button", { name: /^Connection: / });
  await connection.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Connection settings" }).click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await expect(dialog).toBeHidden();
  await expect(connection).toBeFocused();
});

test("the theme that the curator chose paints first on a page without stored choice", async ({ app, page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  const application = page.locator(".v-application");
  await expect(application).toHaveClass(/(^| )v-theme--light( |$)/);
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(application).toHaveClass(/(^| )v-theme--dark( |$)/);
  // pkdb curate keeps the choice and puts it into index.html.
  await expect
    .poll(async () => (await page.request.get(`${app.server.origin}/`)).text())
    .toMatch(/<meta name="pkdb-theme" content="dark"/);

  // As after a restart on another port: the storage of the origin is empty.
  await page.evaluate(() => localStorage.clear());
  await page.addInitScript(() => {
    const observer = new MutationObserver(() => {
      const element = document.querySelector(".v-application");
      if (!element) return;
      document.documentElement.dataset.firstTheme = [...element.classList].find((name) => name.startsWith("v-theme--"));
      observer.disconnect();
    });
    observer.observe(document, { childList: true, subtree: true });
  });
  await page.reload();
  await expect(application).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-first-theme", "v-theme--dark");

  // Back to the theme of the system, for the other tests of the file.
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(application).toHaveClass(/(^| )v-theme--light( |$)/);
  await expect
    .poll(async () => (await page.request.get(`${app.server.origin}/`)).text())
    .toMatch(/<meta name="pkdb-theme" content="system"/);
});
