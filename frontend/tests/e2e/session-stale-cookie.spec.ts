import { test, expect } from "@playwright/test";

// The harness serves the API without secure cookies, so the session cookie
// has the development name that the login of the backend sets.
const sessionCookie = "pkdb_dev_session";

test("a stale session cookie costs one read and leaves an anonymous visitor", async ({
  page,
  context,
  baseURL,
}) => {
  test.info().annotations.push({ type: "issue", description: "#963" });
  await context.addCookies([
    {
      name: sessionCookie,
      value: "pkdb_session_stale-value-of-an-ended-session",
      url: baseURL!,
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
  const counts = { searches: 0, reads: 0 };
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (!path.startsWith("/api/")) return;
    counts.reads++;
    if (path === "/api/v1/filter/") counts.searches++;
  });
  await page.goto("/data");
  // A stale cookie once read again on every 401 without end; count the reads
  // of a fixed window after the page loaded.
  await page.waitForTimeout(3000);
  const measured = { ...counts };
  test.info().annotations.push({
    type: "requests",
    description: JSON.stringify(measured),
  });
  expect(measured.searches).toBeLessThanOrEqual(3);
  expect(measured.reads).toBeLessThanOrEqual(20);
  await expect(
    page.getByRole("tab", { name: "Studies 2", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Main navigation", exact: true })
      .locator(".account-avatar"),
  ).toHaveCount(0);
  const cookies = await context.cookies();
  expect(cookies.map((cookie) => cookie.name)).not.toContain(sessionCookie);
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "Studies 2", exact: true }),
  ).toBeVisible();
});
