import { expect, test } from "@playwright/test";
import fixture from "../fixtures/statistics.json" with { type: "json" };

test("landing statistics renders interactive coverage charts on desktop and mobile", async ({ page }, testInfo) => {
  await page.route("**/api/v2/statistics", route => route.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(page.locator(".statistic-grid a")).toHaveCount(7);
  await expect(page.locator(".statistics-chart .main-svg").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cumulative studies", exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: "Cumulative studies and substances" }).uncheck();
  await expect(page.getByRole("heading", { name: "Studies per year", exact: true })).toBeVisible();
  await page.getByLabel("From year").selectOption("2022");
  await page.getByLabel("PK parameter", { exact: true }).selectOption("clearance");
  await page.getByText("View data for pk parameter values per year", { exact: true }).click();
  await expect(page.getByRole("table", { name: "PK parameter values per year", exact: true })).toContainText("2022");
  await expect.poll(() => page.locator(".chart").nth(2).evaluate(element => Reflect.get(element, "data")?.map((trace: { y: number[] }) => trace.y))).toEqual([[1], [1]]);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath("statistics-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect.poll(() => page.locator(".chart").first().evaluate(element => Reflect.get(element, "layout")?.font?.color)).toMatch(/^#(?:fff|ffffff)$/i);
  await page.screenshot({ path: testInfo.outputPath("statistics-dark.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("statistics-mobile.png"), fullPage: true });
  await page.getByLabel("To year").selectOption("2020");
  await expect(page.getByText("No dated studies in this range.")).toBeVisible();
});
