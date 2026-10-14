import type { Page } from "@playwright/test";
import { expect, expectAccessible, setAutomaticActions, test } from "./fixtures.ts";
import { pixelStats } from "./pixels.ts";

type Theme = "light" | "dark";

/** The teal of the app bar in each theme, the theme color app-bar of themes.ts. */
const BAR: Record<Theme, readonly [number, number, number]> = { light: [23, 107, 112], dark: [19, 87, 91] };

function expectColor(actual: readonly number[], expected: readonly number[], what: string): void {
  for (const [index, value] of actual.entries())
    expect(Math.abs(value - expected[index]!), `${what}: ${actual.join(",")} is near ${expected.join(",")}`).toBeLessThanOrEqual(2);
}

/** Follow the theme of the system, as the app does until the curator chooses one, and wait until it shows. */
async function showTheme(page: Page, theme: Theme): Promise<void> {
  await page.emulateMedia({ colorScheme: theme });
  await expect(page.locator(".v-application")).toHaveClass(new RegExp(`(^| )v-theme--${theme}( |$)`));
}

for (const theme of ["light", "dark"] as const) {
  test(`the app bar is teal with white text and the logo on a white tile in the ${theme} theme, at 1280 and 1440 px`, async ({
    app,
    page,
  }, testInfo) => {
    await page.emulateMedia({ colorScheme: theme });
    await app.open();
    await showTheme(page, theme);
    const bar = page.locator(".app-header");
    await expect(page).toHaveTitle("Curation · PK-DB");
    const brand = bar.getByRole("link", { name: "PK-DB Curation", exact: true });
    await expect(brand).toHaveCSS("color", "rgb(255, 255, 255)");
    const logo = brand.getByRole("img", { name: "PK-DB" });
    await expect(logo).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(logo).toHaveCSS("border-radius", "6px");
    expect(await logo.boundingBox()).toMatchObject({ width: 24, height: 24 });
    // A state without a warning or an error: white text on translucent white.
    await expect(bar.getByRole("button", { name: "Connection: Offline" }).locator(".bar-chip")).toHaveCSS(
      "color",
      "rgb(255, 255, 255)",
    );
    // No rule below the bar.
    await expect(bar).toHaveCSS("border-bottom-width", "0px");
    for (const width of [1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      // The labels of the controls show from 1280 px on.
      await expect(bar.getByText("File watching", { exact: true })).toBeVisible();
      expectColor((await pixelStats(bar)).dominant, BAR[theme], `app bar at ${width} px`);
      await expectAccessible(page);
      const name = `app-bar-${theme}-${width}.png`;
      await testInfo.attach(name, { body: await page.screenshot({ path: testInfo.outputPath(name) }), contentType: "image/png" });
    }
  });
}

test("a paused File watching is an amber chip with dark text on the bar, readable in both themes", async ({ app, page }, testInfo) => {
  await app.open();
  await setAutomaticActions(page, true);
  try {
    const chip = page.getByRole("button", { name: "File watching: Paused" }).locator(".bar-chip");
    await expect(chip).toHaveCSS("background-color", "rgb(255, 208, 138)");
    await expect(chip).toHaveCSS("color", "rgb(46, 26, 0)");
    for (const theme of ["light", "dark"] as const) {
      await showTheme(page, theme);
      await expectAccessible(page);
      const name = `app-bar-paused-${theme}.png`;
      const shot = await page.locator(".app-header").screenshot({ path: testInfo.outputPath(name) });
      await testInfo.attach(name, { body: shot, contentType: "image/png" });
    }
  } finally {
    await setAutomaticActions(page, false);
  }
});

test("a control of the app bar shows a white focus ring inside the bar, and darkens under its white text when hovered", async ({
  app,
  page,
}) => {
  await app.open();
  const bar = (await page.locator(".app-header").boundingBox())!;
  const watching = page.getByRole("button", { name: "File watching: Active" });
  await page.getByRole("button", { name: /^Workspace: / }).focus();
  // A key moves the focus, so that the ring shows (:focus-visible).
  await page.keyboard.press("Tab");
  await expect(watching).toBeFocused();
  await expect(watching).toHaveCSS("outline-color", "rgb(255, 255, 255)");
  await expect(watching).toHaveCSS("outline-width", "2px");
  await expect(watching).toHaveCSS("outline-offset", "1px");
  // The ring, 3 px around the button, stays inside the 36 px bar, which cuts off what stands out of it.
  const box = (await watching.boundingBox())!;
  expect(box.y - 3).toBeGreaterThanOrEqual(bar.y);
  expect(box.y + box.height + 3).toBeLessThanOrEqual(bar.y + bar.height);
  // Hovered, the button darkens under its label, which stays white above the layer.
  await watching.hover();
  await expect(watching.locator(".v-btn__overlay")).toHaveCSS("background-color", "rgb(0, 0, 0)");
  await expect(watching.locator(".v-btn__content")).toHaveCSS("position", "relative");
  await expect(watching.locator(".header-control-label")).toHaveCSS("color", "rgb(255, 255, 255)");
});
