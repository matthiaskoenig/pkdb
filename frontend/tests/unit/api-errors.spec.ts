import { describe, expect, it, vi } from "vitest";
import { errorMessage } from "../../src/api/errors";

function quota(retry?: string | number) {
  return { isAxiosError: true, response: { status: 429, headers: { "retry-after": retry }, data: { detail: "Request quota exceeded" } } };
}

describe("quota feedback", () => {
  it("shows the server retry delay instead of the raw error", () => {
    expect(errorMessage(quota("50"))).toBe("Too many requests. Please wait 50 seconds before trying again.");
    expect(errorMessage(quota(1))).toContain("1 second before");
  });
  it("handles missing, invalid, and HTTP-date retry headers", () => {
    vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-09-24T12:00:00Z"));
    try {
      expect(errorMessage(quota("Thu, 24 Sep 2026 12:00:30 GMT"))).toContain("30 seconds");
      for (const value of [undefined, "invalid", "-1"]) expect(errorMessage(quota(value))).toContain("a moment");
    } finally { vi.restoreAllMocks(); }
  });
});
