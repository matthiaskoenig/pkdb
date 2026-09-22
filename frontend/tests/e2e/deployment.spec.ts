import { test, expect } from "@playwright/test";

const routes = [
  "/",
  "/data",
  "/data/FRONTEND_SCOPE",
  "/curation",
  "/invitation",
  "/account",
  "/verification/invalid-test-id",
  "/registration",
  "/request-password-reset",
  "/reset-password/invalid-test-id",
  "/404",
];
for (const route of routes) {
  test(`direct entry and refresh: ${route}`, async ({ page }) => {
    const response = await page.goto(route);
    expect(response?.status()).toBe(200);
    await expect(page.locator("#app")).not.toBeEmpty();
    await page.reload();
    await expect(page.locator("#app")).not.toBeEmpty();
    await expect(page.locator("body")).not.toContainText(
      "Failed to resolve component",
    );
  });
}

test("API and absent assets never fall through to HTML", async ({
  request,
}) => {
  const api = await request.get("/api/v1/filter/?format=json");
  expect(api.ok()).toBeTruthy();
  expect(api.headers()["content-type"]).toContain("application/json");
  expect((await api.json()).studies).toBeGreaterThan(0);
  for (const path of [
    "/assets/missing.js",
    "/missing.css",
    "/api/v1/nonexistent",
  ]) {
    const response = await request.get(path);
    expect(response.status()).toBe(404);
    expect(await response.text()).not.toContain('<div id="app">');
  }
});

test("same-origin session cookie and CSRF protect mutation", async ({
  request,
}) => {
  const csrf = await request.get("/api/v1/auth/csrf");
  expect(csrf.ok()).toBeTruthy();
  const { csrf_token: token } = await csrf.json();
  const denied = await request.post("/api/v1/auth/login", {
    data: { username: "reader", password: "Frontend-test-password-42!" },
  });
  expect(denied.status()).toBe(403);
  const login = await request.post("/api/v1/auth/login", {
    headers: { Origin: "http://127.0.0.1:18184", "X-CSRF-Token": token },
    data: { username: "reader", password: "Frontend-test-password-42!" },
  });
  expect(login.ok()).toBeTruthy();
  expect(login.headers()["set-cookie"]).toContain("HttpOnly");
  const me = await request.get("/api/v1/me");
  expect((await me.json()).username).toBe("reader");
});

test("built assets have correct MIME and immutable caching while HTML revalidates", async ({
  request,
}) => {
  const html = await request.get("/");
  expect(html.headers()["cache-control"]).toContain("no-cache");
  const document = await html.text();
  const script = document.match(/src="([^"]+\.js)"/);
  expect(script?.[1]).toBeTruthy();
  if (!script?.[1]) throw new Error("Production entry script missing");
  const asset = await request.get(script[1]);
  expect(asset.ok()).toBeTruthy();
  expect(asset.headers()["content-type"]).toMatch(/javascript/);
  expect(asset.headers()["cache-control"]).toContain("immutable");
});

test("API documentation routes reach the backend before SPA fallback", async ({
  request,
}) => {
  for (const path of ["/docs", "/redoc"]) {
    const response = await request.get(path);
    expect(response.ok()).toBeTruthy();
    expect(await response.text()).not.toContain('<div id="app">');
  }
  const schema = await request.get("/openapi.json");
  expect(schema.ok()).toBeTruthy();
  expect(schema.headers()["content-type"]).toContain("application/json");
  expect((await schema.json()).openapi).toMatch(/^3\./);
});
