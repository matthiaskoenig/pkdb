import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";

test("documentation branding and resource navigation work on desktop and mobile", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "PK-DB home" }).locator("img")).toHaveAttribute("src", "/assets/images/pkdb_logo.png");
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", "/assets/images/pkdb_logo.png");
  await page.getByRole("button", { name: "About PK-DB" }).click();
  const resources = page.getByRole("list", { name: "About PK-DB resources" });
  for (const name of ["About PK-DB", "Terms of use", "Contact", "REST API"]) {
    await expect(resources.getByRole("link", { name, exact: true })).toBeVisible();
  }
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobile = page.getByRole("navigation", { name: "Mobile navigation" });
  for (const name of ["About PK-DB", "Terms of use", "Contact", "REST API"]) {
    await expect(mobile.getByRole("link", { name, exact: true })).toBeVisible();
  }
  await mobile.getByRole("link", { name: "About PK-DB", exact: true }).click();
  await expect(mobile).not.toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("Pharmacokinetics database");
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
    const commit = footer.locator('a[href*="/commit/"]');
    await expect(commit).toHaveAttribute("href", /\/commit\/[a-f0-9]{40,64}$/i);
    await expect(commit).toHaveText(/^[a-f0-9]{8}$/i);
  }
});
