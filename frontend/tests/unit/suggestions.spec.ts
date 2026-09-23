import { describe, it, expect, vi, beforeEach } from "vitest";
import { suggestions } from "../../src/api/search";
import { fields } from "../../src/features/search/fields";
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({ api: { get: mocks.get } }));
const page = (items: unknown[]) => ({
  data: {
    current_page: 1,
    last_page: 1,
    data: { count: items.length, data: items },
  },
});
beforeEach(() => mocks.get.mockReset());
describe("supported remote filter suggestions", () => {
  it("uses the supported abstract-type exclusion and preserves stable identifiers", async () => {
    const field = fields.find(
      (f) => f.key === "outputs__measurement_type_sid__in",
    );
    if (!field) throw new Error("Missing field");
    mocks.get.mockResolvedValue(page([{ sid: "thalf", name: "Half-life" }]));
    expect(
      await suggestions(field, "half", new AbortController().signal),
    ).toEqual([{ id: "thalf", title: "Half-life", description: "" }]);
    const url = String(mocks.get.mock.calls[0]?.[0]);
    expect(url).toContain("dtype__exclude=abstract");
    expect(url).not.toContain("exclude_abstract");
  });
  it("uses only public visible-study profiles for curator suggestions", async () => {
    const field = fields.find((f) => f.key === "studies__curators__in");
    if (!field) throw new Error("Missing field");
    mocks.get.mockResolvedValue(
      page([
        {
          curators: [
            { username: "researcher" },
            { username: "researcher" },
            { username: "someone" },
          ],
        },
      ]),
    );
    const result = await suggestions(
      field,
      "research",
      new AbortController().signal,
    );
    expect(result.map((r) => r.id)).toEqual(["researcher"]);
    expect(mocks.get.mock.calls[0]?.[0]).toBe("/api/v1/studies/?page_size=30");
  });
});
