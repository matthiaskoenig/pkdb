import { describe, it, expect } from "vitest";
import {
  encodeLocation,
  decodeLocation,
  criteriaKey,
} from "../../src/features/search/codec";
import {
  defaultCriteria,
  defaultView,
  cloneCriteria,
} from "../../src/features/search/defaults";
import { serializeCriteria } from "../../src/features/search/serialize";
import { reactive } from "vue";
describe("durable applied searches", () => {
  it("round trips every selection without display labels or backend UUID", () => {
    const criteria = defaultCriteria();
    criteria.filters = {
      outputs__substance_sid__in: ["β compound", "caffeine", "caffeine"],
    };
    criteria.scope = "studies";
    criteria.subjects.groups = false;
    const location = {
      criteria,
      view: {
        ...defaultView(),
        tab: "measurements" as const,
        page: 2,
        pageSize: 50,
        order: "-value",
        tableSearch: "zero & precision",
      },
    };
    const encoded = encodeLocation(location),
      decoded = decodeLocation(encoded);
    expect(criteriaKey(decoded.criteria)).toBe(criteriaKey(criteria));
    expect(decoded.view).toEqual(location.view);
    expect(encoded).not.toHaveProperty("uuid");
  });
  it.each([
    { v: "2" },
    { v: "1", q: "{" },
    { v: "1", surprise: "yes" },
    { v: "1", page: "0" },
    { v: "1", page: "1.5" },
    { v: "1", pageSize: "1000" },
    { v: "1", tab: "missing" },
    { v: "1", order: "password" },
    { v: ["1", "1"] },
  ])("rejects invalid URLs without silently broadening (%j)", (query) => {
    expect(() => decodeLocation(query)).toThrow();
  });
  it("keeps defaults independent and can copy reactive store criteria", () => {
    const a = defaultCriteria(),
      b = defaultCriteria();
    a.licences.open = false;
    expect(b.licences.open).toBe(true);
    expect(cloneCriteria(reactive(a))).toEqual(a);
  });
  it("excludes disabled subject branches and represents all-off licences correctly", () => {
    const c = defaultCriteria();
    c.subjects.groups = false;
    c.licences = { open: false, closed: false };
    c.types = { output: false, timecourse: false, array: false };
    c.filters = { subjects__choice_sid__in: ["healthy"] };
    const p = serializeCriteria(c);
    expect(p.get("groups__id__in")).toBe("0");
    expect(p.has("groups__choice_sid__in")).toBe(false);
    expect(p.get("individuals__choice_sid__in")).toBe("healthy");
    expect(p.get("studies__licence__in")).toBe("0");
    expect(p.has("licence__in")).toBe(false);
    expect(p.get("outputs__output_type__in")).toBe("0");
  });
  it("rejects identifiers ambiguous in the backend separator format", () => {
    const c = defaultCriteria();
    c.filters = { studies__sid__in: ["A__B"] };
    expect(() => serializeCriteria(c)).toThrow();
  });
});

it("rejects prototype-shaped own filter keys without broadening the query", () => {
  const q =
    '{"filters":{"__proto__":["x"]},"subjects":{"groups":true,"individuals":true},"licences":{"open":true,"closed":true},"types":{"output":true,"timecourse":true,"array":true}}';
  expect(() => decodeLocation({ v: "1", q })).toThrow();
});
