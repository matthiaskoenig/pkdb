import { beforeEach, expect, it, vi } from "vitest";
import { adminApi } from "../../src/api/admin";
const mocks = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn() }));
vi.mock("../../src/api/client", () => ({
  api: { get: mocks.get, put: mocks.put },
}));
const access = {
  access: "public",
  licence: "open",
  creator_id: 1,
  curator_ids: [2],
};
beforeEach(() => {
  mocks.get.mockReset().mockResolvedValue({ data: access });
  mocks.put.mockReset().mockResolvedValue({});
});
it("addresses the access of a study by its two path segments", async () => {
  await adminApi.access("caffeine/Harder1988", new AbortController().signal);
  expect(mocks.get.mock.calls[0]?.[0]).toBe(
    "/api/v1/admin/studies/caffeine/Harder1988/access",
  );
  await adminApi.saveAccess("caffeine/Harder1988", {
    access: "public",
    licence: "open",
    creator_id: 1,
    curator_ids: [2],
  });
  expect(mocks.put.mock.calls[0]?.[0]).toBe(
    "/api/v1/admin/studies/caffeine/Harder1988/access",
  );
});
it("keeps one segment for a study format 1 sid", async () => {
  await adminApi.access("PKDB00198", new AbortController().signal);
  expect(mocks.get.mock.calls[0]?.[0]).toBe(
    "/api/v1/admin/studies/PKDB00198/access",
  );
});
