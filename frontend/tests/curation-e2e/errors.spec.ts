import { expect, test } from "./fixtures.ts";

// The opener of the system fails, as a broken or missing xdg-open does (#919): `false` exits with
// status 1 for every path.
test.use({ openCommand: "false" });

const STUDY = "#/studies/caffeine/Demo2020";
const OPEN_FAILED = "Could not open the tables of caffeine/Demo2020.";
const DETAIL = "CalledProcessError: false exited with status 1";

test("a failing Open tables says what failed and lists the failure in the activity", async ({ app, page }) => {
  await app.open(`${STUDY}/data`);
  // The local server answers the failed action with 500, which the browser logs.
  app.allowFailedRequest("/local/studies/tables", 500);
  await page.getByRole("button", { name: "Open tables" }).click();

  const alert = page.locator(".study-alert");
  await expect(alert.locator(".action-failure-text")).toHaveText(OPEN_FAILED);
  await expect(alert.locator(".action-failure-detail")).toHaveText(DETAIL);
  await alert.getByText("Details", { exact: true }).click();
  const facts = alert.locator(".failure-facts");
  await expect(facts).toContainText("Open tables (POST /local/studies/tables)");
  await expect(facts).toContainText("500");
  await expect(facts).toContainText("open_failed");
  await expect(facts).toContainText("CalledProcessError");
  await expect(facts).toContainText(/[0-9a-f]{8}/);
  await expect(facts).toContainText("curation.log");

  await alert.getByRole("link", { name: "Show in Activity" }).click();
  await expect(page).toHaveURL(/\/activity\?entry=[0-9a-f]{32}$/);
  const entry = page.locator(".activity-entry").filter({ hasText: OPEN_FAILED });
  await expect(entry).toBeFocused();
  await expect(entry.locator(".activity-status")).toHaveText("Failed");
  await expect(entry.locator(".activity-detail")).toHaveText(DETAIL);
});
