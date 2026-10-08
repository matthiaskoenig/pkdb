import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures.ts";

interface ReviewJson {
  items: { state: string; acknowledges?: string; text: string; target?: object }[];
}

const REASON = "D400 was planned, but the study reports no results for it.";

function problem(page: Page, code: string) {
  return page.getByRole("listitem").filter({ has: page.getByText(code, { exact: true }) });
}

test.beforeEach(async ({ app, page }) => {
  await app.open("#/studies/caffeine/Demo2020/problems");
  // The first validation of the study lists its warnings.
  await expect(problem(page, "digitized_mismatch")).toBeVisible();
});

test("acknowledges a warning with a reason, which a resolved review item keeps", async ({ app, page }) => {
  const severity = page.getByRole("group", { name: "Filter by severity" });
  await expect(severity).toContainText("Warnings2");
  const warning = problem(page, "unused_intervention");
  await expect(warning).toContainText("'D400' is not referenced by any row");
  await warning.getByRole("button", { name: "Acknowledge" }).click();
  const dialog = page.getByRole("dialog", { name: "Acknowledge warning" });
  await expect(dialog).toContainText("unused_intervention");
  await dialog.getByRole("textbox", { name: "Reason" }).fill(REASON);
  await dialog.getByRole("button", { name: "Acknowledge" }).click();
  await expect(dialog).toBeHidden();

  // The next validation moves the warning to the acknowledged ones.
  const acknowledged = page.getByRole("region", { name: "Acknowledged warnings (1)" });
  await expect(acknowledged).toContainText("unused_intervention");
  await expect(acknowledged).toContainText("interventions.tsv · name = D400 · column name");
  await expect(acknowledged).toContainText(REASON);
  await expect(acknowledged).toContainText("Acknowledged by curator on");
  // Only the acknowledged list names it.
  await expect(problem(page, "unused_intervention")).toHaveCount(1);
  await expect(severity).toContainText("Warnings1");

  const review = JSON.parse(
    readFileSync(join(app.server.workspace, "caffeine/Demo2020/review.json"), "utf8"),
  ) as ReviewJson;
  expect(review.items.filter((item) => item.acknowledges === "unused_intervention")).toEqual([
    expect.objectContaining({
      state: "resolved",
      text: REASON,
      target: { file: "interventions.tsv", rows: { name: "D400" }, column: "name" },
    }),
  ]);
  await acknowledged.getByRole("link", { name: "Show the review item" }).click();
  await expect(page.getByRole("article", { name: "Issue" })).toContainText(REASON);
});

test("Show in table opens the table with the cell of the problem focused", async ({ page }) => {
  const mismatch = problem(page, "digitized_mismatch");
  await expect(mismatch).toContainText("mean 1.24 at 4 hr lies");
  await mismatch.getByRole("link", { name: "Show in table" }).click();
  await expect(page.getByRole("tab", { name: /^timecourses_Fig1\.tsv/, selected: true })).toBeVisible();
  const grid = page.getByRole("region", { name: "Rows of timecourses_Fig1.tsv" });
  await expect(grid.getByRole("cell", { name: "1.24", exact: true })).toBeFocused();
});
