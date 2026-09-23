import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("draft changes, applied results and history stay separate", async ({
  page,
}) => {
  await page.goto("/data");
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  const before = page.url();
  await page.getByLabel("Open licence", { exact: true }).uncheck();
  await page.getByLabel("Closed licence", { exact: true }).uncheck();
  await expect(
    page
      .getByRole("form", { name: "Research filters" })
      .getByText("Changes not applied", { exact: true }),
  ).toBeVisible();
  expect(page.url()).toBe(before);
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /download/i })).toHaveCount(0);
  await expect(page.locator("a[download]")).toHaveCount(0);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "No results for this selection" }),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Studies 0", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Open licence", { exact: true })).toBeChecked();
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
});

test("all seven result tabs and independent table refinement", async ({
  page,
}) => {
  await page.goto("/data");
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  for (const name of [
    "Studies",
    "Groups",
    "Individuals",
    "Interventions",
    "Measurements",
    "Timecourses",
    "Scatter data",
  ]) {
    await page.getByRole("tab", { name: new RegExp(`^${name} `) }).click();
    await expect(page.getByRole("tabpanel")).not.toContainText(
      "Results could not be loaded",
    );
    await expect(page.locator(".results-area")).toHaveAttribute(
      "aria-busy",
      "false",
    );
  }
  await page.getByRole("tab", { name: "Studies 1", exact: true }).click();
  await expect(page).toHaveURL(/tab=studies/);
  await expect(
    page.getByText("1 studies in the applied selection"),
  ).toBeVisible();
  const before = page.url();
  await page
    .getByLabel("Search table", { exact: true })
    .fill("definitely-no-such-study");
  expect(page.url()).toBe(before);
  await page
    .getByRole("button", { name: "Apply table search", exact: true })
    .click();
  await expect(
    page.getByText("0 studies in this table refinement"),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByText("1 studies in the applied selection"),
  ).toBeVisible();
});

test("invalid shared criteria are actionable and never run an unfiltered search", async ({
  page,
}) => {
  const filterRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/filter/")) filterRequests.push(request.url());
  });
  await page.goto("/data?v=999&q=%7B%7D");
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "This search URL is invalid or unsupported" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Reset and search" }),
  ).toBeVisible();
  expect(filterRequests).toEqual([]);
});

test("research page accessibility and narrow filter focus", async ({
  page,
}) => {
  await page.goto("/data");
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".results-area")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(
      document
        .getAnimations()
        .filter((animation) =>
          Number.isFinite(
            Number(animation.effect?.getComputedTiming().endTime),
          ),
        )
        .map((animation) => animation.finished.catch(() => undefined)),
    );
  });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  const trigger = page.getByRole("button", { name: "Filters and Search" });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByRole("button", { name: "Close filters", exact: true })
    .click();
  await expect(trigger).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("keyboard tabs and study detail return preserve applied result location", async ({
  page,
}) => {
  await page.goto("/data");
  const studies = page.getByRole("tab", { name: "Studies 1", exact: true });
  await studies.focus();
  await studies.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Groups 1", exact: true }),
  ).toBeFocused();
  await page.getByRole("tab", { name: "Groups 1", exact: true }).press("Home");
  await expect(studies).toBeFocused();
  await page.getByLabel('Search table', { exact: true }).fill('FRONTEND_SCOPE')
  await page.getByRole('button', { name: 'Apply table search', exact: true }).click()
  await expect(page.getByText('1 studies in this table refinement')).toBeVisible()
  const row = page.getByRole("button", {
    name: "View FRONTEND_SCOPE",
    exact: true,
  });
  await expect(row).toBeVisible();
  await row.scrollIntoViewIfNeeded();
  const before = page.url();
  await row.click();
  await expect(
    page.getByRole("heading", { name: "Explore all data from this study" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Close details", exact: true })
    .click();
  await expect(page).toHaveURL(before);
  await expect(row).toBeFocused();
  await expect(page.getByLabel('Search table', { exact: true })).toHaveValue('FRONTEND_SCOPE');
  await expect(studies).toHaveAttribute("aria-selected", "true");
});

test("compound scientific criteria distinguish matching measurements from qualifying studies", async ({
  page,
}) => {
  const criteria = {
    filters: {
      interventions__route_sid__in: ["oral"],
      outputs__substance_sid__in: ["drug-b"],
    },
    subjects: { groups: true, individuals: true },
    licences: { open: true, closed: true },
    types: { output: true, timecourse: true, array: true },
  };
  const query = new URLSearchParams({
    v: "1",
    q: JSON.stringify(criteria),
    scope: "matching",
    tab: "measurements",
    page: "1",
    pageSize: "20",
  });
  await page.goto(`/data?${query}`);
  await expect(
    page.getByRole("tab", { name: "Studies 0", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Measurements 0", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "No results for this selection" }),
  ).toBeVisible();
  await page
    .getByRole("radio", {
      name: "All data from qualifying studies",
      exact: true,
    })
    .check();
  await expect(
    page.getByRole("tab", { name: "Measurements 0", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Measurements 2", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Measurements 2", exact: true }).click();
  await expect(page.getByRole("table")).toContainText("0.002125");
  await expect(page.getByRole("table")).toContainText("gram / liter");
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "Measurements 2", exact: true }),
  ).toBeVisible();
});

test("researcher constructs a combined query using live vocabulary suggestions", async ({
  page,
}) => {
  await page.goto("/data");
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  const before = page.url();
  await page
    .getByRole("combobox", { name: "Routes", exact: true })
    .fill("oral");
  await page.getByRole("option", { name: /^oral(?:\s|$)/ }).click();
  await page
    .getByRole("combobox", { name: "Measured substances", exact: true })
    .fill("drug-b");
  await page.getByRole("option", { name: "drug-b", exact: true }).click();
  expect(page.url()).toBe(before);
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page.getByRole("tab", { name: "Studies 0", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "No results for this selection" }),
  ).toBeVisible();
});

test("invalid manual identifiers remain editable and cannot broaden the applied query", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/data");
  await expect(
    page.getByRole("tab", { name: "Studies 1", exact: true }),
  ).toBeVisible();
  const requests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/filter/")) requests.push(request.url());
  });
  const creators = page.getByRole("combobox", {
    name: "Creators",
    exact: true,
  });
  await creators.fill("name__ambiguous");
  await creators.press("Enter");
  await creators.press("Escape");
  await expect(
    page.getByRole("form", { name: "Research filters" }),
  ).toContainText("Changes not applied");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: /invalid|unsupported/i })
      .first(),
  ).toBeVisible();
  expect(requests).toEqual([]);
  expect(errors).toEqual([]);
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await expect(creators).toBeEditable();
});

test("prototype-named criteria keys cannot bypass the filter allowlist", async ({
  page,
}) => {
  const filterRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/filter/")) filterRequests.push(request.url());
  });
  const q =
    '{"filters":{"__proto__":["x"]},"subjects":{"groups":true,"individuals":true},"licences":{"open":true,"closed":true},"types":{"output":true,"timecourse":true,"array":true}}';
  await page.goto(`/data?v=1&q=${encodeURIComponent(q)}`);
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: /invalid|unsupported/i })
      .first(),
  ).toBeVisible();
  expect(filterRequests).toEqual([]);
});
