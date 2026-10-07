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
