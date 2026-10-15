import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test("lean landing page and API navigation work on desktop and mobile", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "PK-DB home" }).locator("img")).toHaveAttribute("src", "/assets/images/pkdb_logo.png");
  await expect(page.getByRole("heading", { name: "Pharmacokinetics Database", level: 1, exact: true })).toBeVisible();
  const heroLogo = page.locator(".home-hero").getByRole("img", { name: "PK-DB", exact: true });
  await expect(heroLogo).toBeVisible();
  await expect.poll(() => heroLogo.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  expect((await heroLogo.boundingBox())!.width).toBeGreaterThanOrEqual(200);
  await expect(page.getByRole("heading", { name: "Our mission", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Our vision", exact: true })).toBeVisible();
  await expect(page.locator(".statistic-grid a")).toHaveCount(7);
  await expect(page.getByRole("heading", { name: "Example study", exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "How to cite", exact: true })).toHaveCount(0);
  const desktop = page.getByRole("navigation", { name: "Main navigation", exact: true });
  await expect(desktop.getByRole("link", { name: "API", exact: true })).toHaveAttribute("href", "/docs");
  // Studies comes first, before Explore data.
  expect((await desktop.getByRole("link").allInnerTexts()).slice(0, 2)).toEqual(["Studies", "Explore data"]);
  await page.screenshot({ path: testInfo.outputPath("landing-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await expect(heroLogo).toHaveCSS("background-color", "rgb(255, 255, 255)");
  await expect(page.locator(".v-application")).not.toHaveCSS("background-color", "rgb(255, 255, 255)");
  await expect(page.getByRole("heading", { level: 1 })).toHaveCSS("color", /^(rgb\(255, 255, 255\)|color\(srgb 1 1 1\))$/);
  await page.screenshot({ path: testInfo.outputPath("landing-dark.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobile = page.getByRole("navigation", { name: "Mobile navigation" });
  const names = ["Studies", "Explore data", "Vocabulary", "Documentation", "API", "Account"];
  for (const name of names) {
    await expect(mobile.getByRole("link", { name, exact: true })).toBeVisible();
  }
  expect((await mobile.getByRole("link").allInnerTexts()).map((text) => text.trim())).toEqual(names);
  await expect(mobile.getByRole("link", { name: "API", exact: true })).toHaveAttribute("href", "/docs");
  await mobile.getByRole("link", { name: "Vocabulary", exact: true }).click();
  await expect(mobile).not.toBeVisible();
  await page.getByRole("link", { name: "PK-DB home" }).click();
  await expect(page.locator(".statistic-grid a")).toHaveCount(7);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(heroLogo).toBeVisible();
  expect((await heroLogo.boundingBox())!.width).toBeGreaterThanOrEqual(160);
  await page.screenshot({ path: testInfo.outputPath("landing-mobile.png"), fullPage: true });
});

test("login avatar appears in both navigation layouts and clears on logout", async ({ page }, testInfo) => {
  test.info().annotations.push({ type: "issue", description: "#796" });
  const username = `reader-${testInfo.project.name}`;
  await page.goto("/account");
  await page.getByRole("textbox", { name: "Username", exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("Frontend-test-password-42!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Account settings", exact: true })).toBeVisible();
  const desktop = page.getByRole("navigation", { name: "Main navigation", exact: true });
  await expect(desktop.locator(".account-avatar")).toBeVisible();
  const originalAvatar = await desktop.locator(".account-avatar").getAttribute("src");
  await page.getByLabel("Choose photo", { exact: true }).setInputFiles(fileURLToPath(new URL("../../public/assets/images/pkdb_logo.png", import.meta.url)));
  await page.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(desktop.locator(".account-avatar")).not.toHaveAttribute("src", originalAvatar!);
  await expect.poll(() => desktop.locator(".account-avatar").evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0);
  await page.reload();
  await expect(desktop.locator(".account-avatar")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobile = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(mobile.locator(".account-avatar")).toBeVisible();
  await mobile.getByRole("link", { name: username, exact: true }).click();
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.getByRole("button", { name: "Remove photo", exact: true }).click();
  await expect(desktop.locator(".account-avatar")).toHaveAttribute("src", originalAvatar!);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(desktop.getByRole("link", { name: "Account", exact: true })).toBeVisible();
  await expect(desktop.locator(".account-avatar")).toHaveCount(0);
});

test("release and copyright footer is shared by all page types", async ({ page }) => {
  for (const path of ["/", "/studies", "/data", "/data/PKDB00057", "/curation", "/account", "/invitation", "/registration", "/verification/example", "/request-password-reset", "/reset-password/example", "/not-a-page"]) {
    await page.goto(path);
    const footer = page.getByRole("contentinfo");
    await expect(footer).toHaveCount(1);
    await footer.scrollIntoViewIfNeeded();
    await expect(footer).toBeVisible();
    await expect(footer).toContainText(/Release \d+\.\d+\.\d+/);
    await expect(footer).toContainText(`© 2017–${new Date().getFullYear()} Matthias König`);
    await expect(footer.getByRole("link", { name: "Systems Medicine of the Liver" })).toHaveAttribute("href", "https://livermetabolism.com");
    await expect(footer.getByRole("link", { name: "Contact Matthias König" })).toHaveAttribute("href", "mailto:koenigmx@hu-berlin.de");
    await expect(footer.getByRole("link", { name: "Report an issue" })).toHaveAttribute("href", "https://github.com/matthiaskoenig/pkdb/issues/new");
    await expect(footer.getByRole("link", { name: "How to cite" })).toHaveAttribute("href", "https://matthiaskoenig.github.io/pkdb/citation/");
    await expect(footer.getByRole("link", { name: "Terms of use", exact: true })).toHaveAttribute("href", "https://matthiaskoenig.github.io/pkdb/terms-of-use/");
    const commit = footer.locator('a[href*="/commit/"]');
    await expect(commit).toHaveAttribute("href", /\/commit\/[a-f0-9]{40,64}$/i);
    await expect(commit).toHaveText(/^[a-f0-9]{8}$/i);
  }
});

test("the skip link is hidden, also from full-page screenshots, until it has focus", async ({ page }) => {
  await page.goto("/data");
  const skip = page.getByRole("link", { name: "Skip to main content", exact: true });
  const unfocused = await skip.boundingBox();
  expect(unfocused!.width).toBeLessThanOrEqual(1);
  await expect(skip).toHaveCSS("clip-path", /inset\(50%\)/);
  await page.keyboard.press("Tab");
  await expect(skip).toBeFocused();
  const focused = await skip.boundingBox();
  expect(focused!.width).toBeGreaterThan(100);
  expect(focused!.y).toBeGreaterThanOrEqual(0);
  await expect(skip).not.toHaveCSS("clip-path", /inset\(50%\)/);
  await page.keyboard.press("Tab");
  await expect(skip).toHaveCSS("clip-path", /inset\(50%\)/);
});

test("text, also in Vuetify's typography classes, is set in the bundled Inter", async ({ page }) => {
  await page.goto("/request-password-reset");
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toHaveClass(/(^| )text-h5( |$)/);
  const font = await heading.evaluate(async (element) => {
    await document.fonts.ready;
    const inter = [...document.fonts].filter((face) => face.family.replaceAll('"', "") === "Inter Variable");
    return {
      body: getComputedStyle(document.body).fontFamily,
      heading: getComputedStyle(element).fontFamily,
      loaded: inter.some((face) => face.status === "loaded"),
    };
  });
  // WebKit leaves out the quotes around the name of the family.
  expect(font.body).toMatch(/^"?Inter Variable"?,/);
  expect(font.heading).toMatch(/^"?Inter Variable"?,/);
  expect(font.loaded).toBe(true);
  // The license of the font is served beside it.
  const license = await page.request.get("/assets/Inter-LICENSE.txt");
  expect(license.status()).toBe(200);
  expect(await license.text()).toContain("SIL OPEN FONT LICENSE");
});

test("Vuetify's cascade layers keep Vuetify's order, so its components win against its reset", async ({ page }) => {
  // The production build links the styles of shared chunks before the main file; the page names the order of the layers first.
  await page.goto("/");
  const declared = await page.evaluate(() => {
    const first = document.styleSheets[0]?.cssRules[0];
    return first instanceof CSSLayerStatementRule ? [...new Set(first.nameList.map((name) => name.split(".")[0]))] : [];
  });
  expect(declared.slice(0, 5)).toEqual(["vuetify-core", "vuetify-components", "vuetify-overrides", "vuetify-utilities", "vuetify-final"]);
  // Vuetify's reset `button { font: inherit }` would give buttons the weight and the size of the text around them.
  await expect(page.getByRole("button", { name: "Toggle color theme" })).toHaveCSS("font-weight", "500");
  await page.goto("/account");
  const signIn = page.getByRole("button", { name: "Sign in", exact: true });
  await expect(signIn).toHaveCSS("font-weight", "500");
  await expect(signIn).toHaveCSS("line-height", "normal");
  const root = await page.evaluate(() => Number.parseFloat(getComputedStyle(document.documentElement).fontSize));
  await expect(signIn).toHaveCSS("font-size", `${0.875 * root}px`);
});
