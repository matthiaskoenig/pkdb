import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test("lean landing page and API navigation work on desktop and mobile", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "PK-DB home" }).locator("img")).toHaveAttribute("src", "/assets/images/pkdb_logo.png");
  await expect(page.getByRole("heading", { name: "Pharmacokinetics Database", level: 1, exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Our mission", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Our vision", exact: true })).toBeVisible();
  await expect(page.locator(".statistic-grid a")).toHaveCount(7);
  await expect(page.getByRole("heading", { name: "Example study", exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "How to cite", exact: true })).toHaveCount(0);
  const desktop = page.getByRole("navigation", { name: "Main navigation", exact: true });
  await expect(desktop.getByRole("link", { name: "API", exact: true })).toHaveAttribute("href", "/docs");
  await page.screenshot({ path: testInfo.outputPath("landing-desktop.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await page.screenshot({ path: testInfo.outputPath("landing-dark.png"), fullPage: true });
  await page.getByRole("button", { name: "Toggle color theme" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobile = page.getByRole("navigation", { name: "Mobile navigation" });
  for (const name of ["Explore data", "Vocabulary", "Documentation", "API", "Account"]) {
    await expect(mobile.getByRole("link", { name, exact: true })).toBeVisible();
  }
  await expect(mobile.getByRole("link", { name: "API", exact: true })).toHaveAttribute("href", "/docs");
  await mobile.getByRole("link", { name: "Vocabulary", exact: true }).click();
  await expect(mobile).not.toBeVisible();
  await page.getByRole("link", { name: "PK-DB home" }).click();
  await expect(page.locator(".statistic-grid a")).toHaveCount(7);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
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
  for (const path of ["/", "/data", "/data/PKDB00057", "/curation", "/account", "/invitation", "/registration", "/verification/example", "/request-password-reset", "/reset-password/example", "/not-a-page"]) {
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
