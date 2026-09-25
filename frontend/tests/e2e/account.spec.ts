import { test, expect, type Page } from "@playwright/test";
test.use({ screenshot: "off" });
const password = "Frontend-test-password-42!";
async function login(page: Page, username: string) {
  await page.goto("/account");
  await page
    .getByRole("textbox", { name: "Username", exact: true })
    .fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
}
async function confirmPassword(page: Page) {
  const dialog = page
    .getByRole("dialog")
    .filter({ hasText: "Confirm your identity" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("Password", { exact: true }).fill(password);
  await dialog.getByRole("button", { name: "Continue", exact: true }).click();
}
test("cookie-session account profile, private credentials and explicit sign-out", async ({
  page,
}, testInfo) => {
  const username = `reader-${testInfo.project.name}`;
  await login(page, username);
  await expect(
    page.getByRole("heading", { name: "Account settings", exact: true }),
  ).toBeVisible();
  const display = page.getByLabel("Display name", { exact: true }),
    original = await display.inputValue();
  const github = page.getByLabel("GitHub handle (optional)", { exact: true });
  const orcid = page.getByLabel("ORCID iD (optional)", { exact: true });
  const originalGithub = await github.inputValue();
  const originalOrcid = await orcid.inputValue();
  await expect(github).toBeEditable();
  await expect(orcid).toBeEditable();
  await github.fill("frontend-researcher");
  await orcid.fill("0000-0002-1825-0097");
  await display.fill("Frontend researcher");
  await page
    .getByLabel("Show GitHub on my public profile", { exact: true })
    .uncheck();
  await page.getByRole("button", { name: "Save profile", exact: true }).click();
  await expect(page.getByText("Profile saved.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(display).toHaveValue("Frontend researcher");
  await expect(github).toHaveValue("frontend-researcher");
  await expect(orcid).toHaveValue("0000-0002-1825-0097");
  await expect(
    page.getByLabel("Show GitHub on my public profile", { exact: true }),
  ).not.toBeChecked();
  // Restore the fixture profile; every browser project uses the same isolated data.
  await display.fill(original);
  await github.fill(originalGithub);
  await orcid.fill(originalOrcid);
  await page
    .getByLabel("Show GitHub on my public profile", { exact: true })
    .check();
  await page.getByRole("button", { name: "Save profile", exact: true }).click();
  await expect(page.getByText("Profile saved.", { exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Email addresses", exact: true }).click();
  await expect(
    page.getByText(`${username}@example.invalid`, { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Primary · Verified", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "API keys", exact: true }).click();
  await expect(
    page.getByLabel("Allow study uploads and edits within my permissions"),
  ).not.toBeVisible();
  const name = `browser-${testInfo.project.name}-${Date.now()}`;
  await page.getByLabel("Key name", { exact: true }).fill(name);
  await page.getByRole("button", { name: "Create key", exact: true }).click();
  await confirmPassword(page);
  const secretDialog = page
    .getByRole("dialog")
    .filter({ hasText: "Save your API key" });
  await expect(secretDialog).toBeVisible();
  // Never put the secret in test output, traces, or screenshots.
  expect(
    (
      await secretDialog.getByLabel("API key", { exact: true }).inputValue()
    ).startsWith("pkdb_live_"),
  ).toBe(true);
  await secretDialog
    .getByRole("button", { name: "I have saved the key", exact: true })
    .click();
  await expect(secretDialog).not.toBeVisible();
  const keys = page.locator(".credential-row").filter({ hasText: name });
  await keys.getByRole("button", { name: "Rotate", exact: true }).click();
  await expect(secretDialog).toBeVisible();
  await expect(
    secretDialog.getByText(/previous key remains valid/),
  ).toBeVisible();
  await secretDialog
    .getByRole("button", { name: "I have saved the key", exact: true })
    .click();
  await expect(keys).toHaveCount(2);
  for (let index = 0; index < 2; index++) {
    await keys
      .getByRole("button", { name: "Revoke", exact: true })
      .first()
      .click();
    await expect(
      page.getByText("API key revoked.", { exact: true }),
    ).toBeVisible();
  }
  await expect(
    keys.getByRole("button", { name: "Revoke", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("tab", { name: "Sessions", exact: true }).click();
  const current = page
    .locator(".credential-row")
    .filter({ hasText: "This browser" });
  await current.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to PK-DB", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "API keys", exact: true }),
  ).not.toBeVisible();
  await login(page, username);
  await expect(
    page.getByRole("heading", { name: "Account settings", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to PK-DB", exact: true }),
  ).toBeVisible();
});
for (const role of ["curator", "reviewer"]) {
  test(`${role} account retains permitted key scopes and assignment exploration`, async ({
    page,
  }) => {
    await login(page, role);
    await expect(
      page.getByRole("heading", { name: "Account settings", exact: true }),
    ).toBeVisible();
    await page.getByRole("tab", { name: "API keys", exact: true }).click();
    await expect(
      page.getByLabel("Allow study uploads and edits within my permissions"),
    ).toBeChecked();
    await page
      .getByRole("tab", { name: "Assigned studies", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Assigned studies", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("tab", { name: "Security history", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Security history", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("tab", { name: "Administration", exact: true }),
    ).not.toBeVisible();
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Sign in to PK-DB", exact: true }),
    ).toBeVisible();
  });
}
test("administrator password login grants administration using real permissions", async ({
  page,
}) => {
  await login(page, "administrator");
  await expect(
    page.getByRole("heading", { name: "Account settings", exact: true }),
  ).toBeVisible();
  const response = await page.request.get("/api/v1/admin/users");
  expect(response.status()).toBe(200);
  await page.getByRole("tab", { name: "Administration", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "User administration", exact: true }),
  ).toBeVisible();
  const reader = page.getByRole("row").filter({ hasText: /@reader · ID/ });
  await expect(reader).toBeVisible();
  await page
    .getByLabel("Study identifier", { exact: true })
    .fill("FRONTEND_SCOPE");
  await page
    .getByRole("button", { name: "Load study access", exact: true })
    .click();
  await expect(
    page.getByLabel("Assigned curator account IDs", { exact: true }),
  ).toBeVisible();
  const grants = await page
    .getByLabel("Assigned curator account IDs", { exact: true })
    .inputValue();
  await page
    .getByRole("button", { name: "Save study access", exact: true })
    .click();
  await expect(
    page.getByText("Study access updated.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Assigned curator account IDs", { exact: true }),
  ).toHaveValue(grants);
  await page.getByRole("button", { name: "Load events", exact: true }).click();
  await expect(
    page.getByRole("cell", { name: "study.access", exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to PK-DB", exact: true }),
  ).toBeVisible();
});
