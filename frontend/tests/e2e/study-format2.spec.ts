import AxeBuilder from "@axe-core/playwright";
import { expect, test, type BrowserContext, type Page } from "@playwright/test";

test.use({ screenshot: "off" });
const password = "Frontend-test-password-42!";
const sid = "drug/Format2Fixture";
const address = "/data/drug/Format2Fixture";

async function login(page: Page, username: string) {
  await page.goto("/account");
  await page
    .getByRole("textbox", { name: "Username", exact: true })
    .fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Account settings", exact: true }),
  ).toBeVisible();
}
async function category(page: Page, name: string) {
  const select = page.getByRole("combobox", { name: "Study data category" });
  await select.focus();
  await select.press("ArrowDown");
  await page.getByRole("option", { name, exact: true }).click();
}

// The login of an account is throttled, so the curator signs in once per browser.
test.describe("a curator reads the study format 2 study", () => {
  test.describe.configure({ mode: "serial" });
  let context: BrowserContext;
  let page: Page;
  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    await login(page, "curator");
  });
  test.afterAll(async () => {
    await context.close();
  });

  test("a study is served by substance and name with its release, issue and review", async () => {
    await page.goto(address);
    await expect(
      page.getByRole("heading", { name: "Format2Fixture", exact: true }),
    ).toBeVisible();
    const status = page.getByRole("region", { name: "Study status" });
    await expect(status).toContainText(sid);
    await expect(status).toContainText("PKDB identifier");
    await expect(status).toContainText("PKDB09901");
    await expect(status).toContainText("2026-09-28");
    await expect(status).toContainText("In review · 1 open item");
    const issue = status.getByRole("link", { name: "#2158", exact: true });
    await expect(issue).toHaveAttribute(
      "href",
      "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    );
    await expect(issue).toHaveAttribute("rel", /noopener/);
    const record = page.getByRole("region", { name: "Record details" });
    // The heading takes focus without a ring across the page; the count agrees.
    await expect(
      page.getByRole("heading", { name: "Format2Fixture", exact: true }),
    ).toHaveCSS("outline-style", "none");
    await expect(
      page.getByRole("region", { name: "Whole-study data" }),
    ).toContainText("1 record");
    await expect(
      page.getByRole("region", { name: "Whole-study data" }),
    ).not.toContainText("1 records");
    await expect(
      record.getByRole("region", { name: "Study status" }).getByText(sid),
    ).toBeVisible();
    for (const raw of ["Pkdb id", "Release date", "Review status"])
      await expect(record.getByText(raw, { exact: true })).toHaveCount(0);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
    await page.screenshot({ path: test.info().outputPath("study-status.png") });
  });

  test("the PKDB identifier of a released study follows the API redirect", async () => {
    const redirected = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/api/v1/studies/${sid}/`) &&
        response.request().redirectedFrom() !== null,
    );
    await page.goto("/data");
    await page.goto("/data/PKDB09901");
    await redirected;
    await expect(page).toHaveURL(new RegExp(`${address}$`));
    await expect(
      page.getByRole("region", { name: "Study status" }),
    ).toContainText("PKDB09901");
    // The identifier is replaced, not kept as a history entry.
    await page.goBack();
    await expect(page).toHaveURL(/\/data$/);
  });

  test("schedules read as a person would say them and statistics keep their kind", async () => {
    await page.goto(address);
    await category(page, "Interventions");
    const list = page.getByRole("region", { name: "Whole-study data" });
    await expect(list).toContainText("every 24 h, 7 doses from 0 h");
    await expect(list).toContainText("0, 12, 40 h");
    await list.getByRole("button", { name: /^D1/ }).click();
    const schedule = page.getByRole("region", { name: "Schedule" });
    await expect(schedule).toContainText("every 24 h, 7 doses from 0 h");
    const record = page.getByRole("region", { name: "Record details" });
    for (const raw of ["Time", "Interval", "Doses", "Time unit"])
      await expect(record.getByText(raw, { exact: true })).toHaveCount(0);
    await expect(record.getByText("Mean", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Back to previous record" }).click();
    await category(page, "Interventions");
    await list.getByRole("button", { name: /^D2/ }).click();
    await expect(page.getByRole("region", { name: "Schedule" })).toContainText(
      "0, 12, 40 h",
    );
    await page.getByRole("button", { name: "Back to previous record" }).click();
    await category(page, "Measurements");
    await expect(list.getByRole("listitem").first()).toBeVisible();
    await list
      .getByRole("button", { name: /^concentration/i })
      .first()
      .click();
    await expect(
      page.getByRole("region", { name: "Record details" }),
    ).toBeVisible();
  });

  test("search tables show the geometric statistics, sort by them and open the study by name", async () => {
    await page.goto("/data");
    await expect(page.getByRole("tab", { name: /^Studies 2$/ })).toBeVisible();
    await page.getByRole("tab", { name: /^Measurements / }).click();
    // One value column replaces the statistic columns; names match exactly.
    await expect(page.getByRole("columnheader")).toHaveCount(8);
    for (const title of [
      "Explore",
      "Measurement",
      "Substance",
      "Unit",
      "Value",
      "Subject",
      "Related interventions",
      "Study",
    ])
      await expect(
        page.getByRole("columnheader", { name: title, exact: true }),
      ).toHaveCount(1);
    // Unit, subject and study are visible without scrolling the table.
    await page.setViewportSize({ width: 1440, height: 900 });
    const scroll = page.locator(".table-scroll");
    await expect(scroll).toBeVisible();
    expect(
      await scroll.evaluate(
        (element) => element.scrollWidth <= element.clientWidth,
      ),
    ).toBe(true);
    const table = page.getByRole("table");
    const nb = "\u00a0";
    await expect(table).toContainText(`0.004${nb}×/÷${nb}1.5${nb}(GSD)`);
    await expect(table).toContainText(`0.009${nb}±${nb}0.001${nb}(SD)`);
    await expect(table).toContainText("drug/Format2Fixture");
    // A study identifier stays on one line while the table has room.
    const lines = await page.locator("td.identifier").evaluateAll((cells) =>
      cells.map((cell) => {
        const range = document.createRange();
        range.selectNodeContents(cell);
        return new Set(
          [...range.getClientRects()]
            .filter((rect) => rect.height > 0)
            .map((rect) => Math.round(rect.top)),
        ).size;
      }),
    );
    expect(lines.length).toBeGreaterThan(5);
    expect(Math.max(...lines)).toBe(1);
    await expect(table).not.toContainText("Not reported");
    const sorted = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/outputs/") &&
        new URL(response.url()).searchParams.get("ordering") ===
          "central_value",
    );
    await page.getByRole("button", { name: "Value", exact: true }).click();
    expect((await sorted).status()).toBe(200);
    await expect(
      page.getByRole("columnheader", { name: "Value", exact: true }),
    ).toHaveAttribute("aria-sort", "ascending");
    // Rows with a mean and rows with a geometric mean share one order.
    const valueOrder = async () =>
      (await page.locator("tbody tr td:nth-child(5)").allTextContents())
        .map((text) => Number.parseFloat(text.replace(/^[^\d-]+/u, "")))
        .filter((value) => !Number.isNaN(value));
    await expect
      .poll(async () => {
        const values = await valueOrder();
        return (
          values.length > 5 && values.every((v, i) => !i || values[i - 1]! <= v)
        );
      })
      .toBe(true);
    await page.getByRole("tab", { name: /^Interventions / }).click();
    await expect(
      page.getByRole("columnheader", { name: "Schedule", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("table")).toContainText(
      "every 24 h, 7 doses from 0 h",
    );
    await expect(page.getByRole("table")).toContainText("0, 12, 40 h");
    await page.getByRole("tab", { name: /^Groups / }).click();
    await expect(page.getByRole("table")).toContainText("species homo sapiens");
    await page.getByRole("tab", { name: /^Studies / }).click();
    await page.getByLabel("Search table", { exact: true }).fill("PKDB09901");
    await page
      .getByRole("button", { name: "Apply table search", exact: true })
      .click();
    await expect(
      page.getByText("1 study in this table refinement"),
    ).toBeVisible();
    await page
      .getByRole("button", { name: `View ${sid}`, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`${address}\\?`));
    // The study heading, not the skip link, takes focus after the navigation.
    await expect(
      page.getByRole("heading", { name: "Format2Fixture", exact: true }),
    ).toBeFocused();
    await expect(
      page.getByRole("region", { name: "Study status" }),
    ).toContainText("PKDB09901");
    await page
      .getByRole("button", { name: "Close details", exact: true })
      .click();
    await expect(page).toHaveURL(/\/data\?/);
  });

  test("a PKDB identifier filter selects the released study", async () => {
    const criteria = {
      filters: { studies__pkdb_id__in: ["PKDB09901"] },
      subjects: { groups: true, individuals: true },
      licences: { open: true, closed: true },
      types: { output: true, timecourse: true, array: true },
    };
    const query = new URLSearchParams({
      v: "1",
      q: JSON.stringify(criteria),
      scope: "studies",
      tab: "studies",
      page: "1",
      pageSize: "20",
    });
    await page.goto(`/data?${query}`);
    await expect(page.getByRole("tab", { name: /^Studies 1$/ })).toBeVisible();
    await expect(
      page.getByRole("button", { name: `View ${sid}`, exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: "PKDB identifiers", exact: true }),
    ).toBeVisible();
  });

  test("timecourse traces carry the timecourse label and the geometric SD is a multiplicative band", async () => {
    await page.goto(address);
    await category(page, "Timecourses");
    await page
      .getByRole("button", { name: /Plasma after 10 mg daily \(geometric\)/ })
      .click();
    await page
      .getByRole("button", { name: "Show timecourse plot", exact: true })
      .click();
    await expect(page.locator(".plot .main-svg").first()).toBeVisible();
    const trace = await page.locator(".plot").evaluate((element) => {
      const data: unknown = Reflect.get(element, "data");
      if (!Array.isArray(data)) throw new Error("Rendered data is missing");
      const first: unknown = data[0];
      if (typeof first !== "object" || first === null)
        throw new Error("Rendered trace is invalid");
      return JSON.parse(JSON.stringify(first));
    });
    expect(trace.name).toBe("Plasma after 10 mg daily (geometric)");
    expect(trace.x).toEqual([1, 2, 4]);
    expect(trace.error_y.symmetric).toBe(false);
    const expected: [number, number][] = [
      [0.008, 2],
      [0.004, 1.5],
      [0.002, 1.25],
    ];
    for (const [index, [mean, gsd]] of expected.entries()) {
      expect(trace.y[index]).toBeCloseTo(mean, 12);
      expect(trace.error_y.array[index]).toBeCloseTo(mean * (gsd - 1), 12);
      expect(trace.error_y.arrayminus[index]).toBeCloseTo(
        mean * (1 - 1 / gsd),
        12,
      );
    }
    await expect(page.locator(".legend .legendtext")).toHaveText(
      "Plasma after 10 mg daily (geometric)",
    );
    await expect(
      page.getByText(
        "Y error bars: geometric mean divided and multiplied by the geometric SD.",
        { exact: true },
      ),
    ).toBeVisible();
    // Hover labels show four significant digits; the chart follows the theme.
    const layout = () =>
      page.locator(".plot").evaluate((element) => {
        const value: unknown = Reflect.get(element, "layout");
        if (typeof value !== "object" || value === null)
          throw new Error("Rendered layout is missing");
        return JSON.parse(JSON.stringify(value));
      });
    const light = await layout();
    expect(light.yaxis.hoverformat).toBe(".4~g");
    expect(light.xaxis.hoverformat).toBe(".4~g");
    expect(light.paper_bgcolor).toBe("#ffffff");
    await page.screenshot({
      path: test.info().outputPath("timecourse-geometric.png"),
    });
    await page.getByRole("button", { name: "Toggle color theme" }).click();
    await expect
      .poll(async () => (await layout()).paper_bgcolor)
      .toBe("#192b31");
    expect((await layout()).font.color).not.toBe(light.font.color);
    await page.screenshot({
      path: test.info().outputPath("timecourse-geometric-dark.png"),
    });
    await page.getByRole("button", { name: "Toggle color theme" }).click();
    await expect
      .poll(async () => (await layout()).paper_bgcolor)
      .toBe("#ffffff");
    await page
      .getByText("Accessible plot data and uncertainty", { exact: true })
      .click();
    const table = page.getByRole("table", {
      name: "Point values and their uncertainty; missing values are shown as -",
    });
    for (const title of ["Geometric mean", "Geometric SD", "Geometric CV"])
      await expect(
        table.getByRole("columnheader", { name: title, exact: true }),
      ).toBeVisible();
    await expect(table).toContainText("0.008");
    // Coefficients of variation are fractions in the data, percent on screen.
    await expect(table).toContainText("22.6 %");
    await expect(table).toContainText("78.54 %");
    await expect(table).not.toContainText("0.2259");
    await page.getByRole("button", { name: "Back to previous record" }).click();
    await category(page, "Timecourses");
    await page
      .getByRole("button", { name: /Plasma after 10 mg daily \(arithmetic\)/ })
      .click();
    await page
      .getByRole("button", { name: "Show timecourse plot", exact: true })
      .click();
    await expect(page.locator(".plot .main-svg").first()).toBeVisible();
    const arithmetic = await page.locator(".plot").evaluate((element) => {
      const data: unknown = Reflect.get(element, "data");
      if (!Array.isArray(data)) throw new Error("Rendered data is missing");
      return JSON.parse(JSON.stringify(data[0]));
    });
    expect(arithmetic.name).toBe("Plasma after 10 mg daily (arithmetic)");
    expect(arithmetic.error_y.symmetric).toBeUndefined();
    expect(arithmetic.error_y.array).toHaveLength(3);
  });

  test("assigned studies link to the study by its two segments", async () => {
    await page.goto("/account");
    await page
      .getByRole("tab", { name: "Assigned studies", exact: true })
      .click();
    const link = page.getByRole("link", { name: /Format2Fixture/ });
    await expect(link).toHaveAttribute("href", address);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`${address}$`));
    await expect(
      page.getByRole("heading", { name: "Format2Fixture", exact: true }),
    ).toBeVisible();
  });
});

test("a private study and its PKDB identifier stay hidden from visitors", async ({
  page,
}) => {
  for (const path of [address, "/data/PKDB09901"]) {
    await page.goto(path);
    await expect(
      page.getByRole("button", { name: "Retry details" }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toContainText("Not found");
    await expect(
      page.getByRole("region", { name: "Study status" }),
    ).toHaveCount(0);
    // The identifier is not resolved to the sid of the private study.
    await expect(page).toHaveURL(new RegExp(`${path}$`));
    if (path !== address)
      await expect(page.locator("main")).not.toContainText("Format2Fixture");
  }
});

test("administration addresses the access of a study by its two segments", async ({
  page,
}) => {
  await login(page, "administrator");
  await page.getByRole("tab", { name: "Administration", exact: true }).click();
  await page.getByLabel("Study identifier", { exact: true }).fill(sid);
  await page
    .getByRole("button", { name: "Load study access", exact: true })
    .click();
  await expect(
    page.getByLabel("Assigned curator account IDs", { exact: true }),
  ).toBeVisible();
});
