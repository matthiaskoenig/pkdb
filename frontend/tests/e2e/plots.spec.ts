import { expect, test } from "@playwright/test";

test("study exploration loads Plotly on demand and preserves complete subset values", async ({
  page,
}) => {
  const engineRequests: string[] = [];
  page.on("request", (request) => {
    if (/plotly[.-].*\.js/i.test(request.url()))
      engineRequests.push(request.url());
  });
  await page.goto("/data/FRONTEND_SCOPE");
  await expect(
    page.getByRole("heading", { name: "Explore all data from this study" }),
  ).toBeVisible();
  expect(engineRequests).toHaveLength(0);
  await page.getByRole("combobox", { name: "Study data category" }).focus();
  await page
    .getByRole("combobox", { name: "Study data category" })
    .press("ArrowDown");
  await page.getByRole("option", { name: "Timecourses", exact: true }).click();
  await page.getByRole("button", { name: /Fixture timecourse/ }).click();
  await expect(
    page.getByRole("heading", { name: "Fixture timecourse", exact: true }),
  ).toBeVisible();
  expect(engineRequests).toHaveLength(0);
  await page
    .getByRole("button", { name: "Show timecourse plot", exact: true })
    .click();
  await expect(page.locator(".plot .main-svg").first()).toBeVisible();
  expect(engineRequests.length).toBeGreaterThan(0);
  await expect(page.locator('.modebar-btn[data-title*="Download"]')).toHaveCount(0);
  await expect(page.locator('a[download]')).toHaveCount(0);
  const trace = await page.locator(".plot").evaluate((element) => {
    const data: unknown = Reflect.get(element, "data");
    if (!Array.isArray(data))
      throw new Error("Rendered Plotly data is missing");
    const first: unknown = data[0];
    if (
      typeof first !== "object" ||
      first === null ||
      !("x" in first) ||
      !("y" in first)
    )
      throw new Error("Rendered trace is invalid");
    return { x: first.x, y: first.y };
  });
  expect(trace).toEqual({ x: [0, 1], y: [0, 0.002125] });
  await expect(
    page.getByText("The complete subset is shown as context;", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByText("Accessible plot data and uncertainty", { exact: true })
    .click();
  const table = page.getByRole("table", {
    name: "Reported point values; missing values are shown as -",
  });
  await expect(table).toContainText("0.002125");
  await expect(table).toContainText("gram / liter");
  await page.getByRole("checkbox", { name: "Logarithmic Y axis" }).check();
  await expect(
    page.getByText("Zero and negative values cannot appear", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back to previous record" }).click();
  await expect(
    page.getByRole("heading", { name: "Explore all data from this study" }),
  ).toBeVisible();
  await expect(page.locator(".plot")).toHaveCount(0);
  await page.getByRole("combobox", { name: "Study data category" }).focus();
  await page
    .getByRole("combobox", { name: "Study data category" })
    .press("ArrowDown");
  await page.getByRole("option", { name: "Scatters", exact: true }).click();
  await page.getByRole("button", { name: /Fixture scatter/ }).click();
  await page
    .getByRole("button", { name: "Show scatter plot", exact: true })
    .click();
  await expect(page.locator(".plot .main-svg").first()).toBeVisible();
  const scatter = await page.locator(".plot").evaluate((element) => {
    const data: unknown = Reflect.get(element, "data");
    if (!Array.isArray(data))
      throw new Error("Rendered scatter data is missing");
    const first: unknown = data[0];
    if (
      typeof first !== "object" ||
      first === null ||
      !("x" in first) ||
      !("y" in first)
    )
      throw new Error("Rendered scatter is invalid");
    return { x: first.x, y: first.y };
  });
  expect(scatter).toEqual({ x: [0], y: [0.002125] });
});

test("vocabulary search opens scientific terminology details and preserves text search", async ({
  page,
}, testInfo) => {
  await page.goto("/curation");
  const searched = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/info_nodes/") &&
      new URL(response.url()).searchParams.get("search") === "drug-b",
  );
  await page.getByRole("textbox", { name: "Search vocabulary" }).fill("drug-b");
  await searched;
  await expect(
    page.getByRole("status").filter({ hasText: /vocabulary terms/ }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy name drug-b", exact: true })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Metadata / annotations" })).toBeVisible();
  const term = page.getByRole("button", { name: "Details for drug-b", exact: true });
  await term.click();
  await expect(
    page.getByRole("region", { name: "Record details" }),
  ).toContainText("drug");
  await page
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Search vocabulary" }),
  ).toHaveValue("drug-b");
  await page.getByRole("textbox", { name: "Search vocabulary" }).fill("blood measurement");
  await expect(page.getByRole("link", { name: "CMO:0000035 · blood measurement", exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("vocabulary-desktop.png") });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "Copy name blood measurement", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("vocabulary-mobile.png") });
});
