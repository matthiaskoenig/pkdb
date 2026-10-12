import { expect, expectAccessible, test } from "./fixtures.ts";

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
  // At most 6 lines of the detail show; the rest scrolls.
  const cap = await alert.locator(".action-failure-detail").evaluate((element) => getComputedStyle(element).maxHeight);
  expect(cap).not.toBe("none");
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
  // The entry caps its detail as the alert does.
  await expect(entry.locator(".activity-detail")).toHaveCSS("max-height", cap);
});

// The alert with its details open, as screens.spec.ts checks the other screens: both themes, wide and
// narrow. It is here because the failing opener is an option of the whole spec file.
const NARROW = { width: 390, height: 844 };

for (const theme of ["light", "dark"] as const) {
  test(`the alert of a failed Open tables with its details is accessible in the ${theme} theme and fits a narrow window`, async ({
    app,
    page,
  }, testInfo) => {
    await page.emulateMedia({ colorScheme: theme });
    await app.open(`${STUDY}/data`);
    await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
    app.allowFailedRequest("/local/studies/tables", 500);
    await page.getByRole("button", { name: "Open tables" }).click();
    const alert = page.locator(".study-alert");
    await alert.getByText("Details", { exact: true }).click();
    await expect(alert.locator(".failure-facts")).toBeVisible();
    await testInfo.attach(`failure-alert-${theme}.png`, { body: await alert.screenshot(), contentType: "image/png" });
    await expectAccessible(page);

    await page.setViewportSize(NARROW);
    await expect(alert.locator(".failure-facts")).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth))
      .toBe(0);
    await testInfo.attach(`failure-alert-${theme}-narrow.png`, { body: await alert.screenshot(), contentType: "image/png" });
    await expectAccessible(page);
  });
}
