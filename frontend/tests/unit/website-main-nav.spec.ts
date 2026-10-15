import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { routes } from "../../src/router";
import { studyNavEntry } from "../../src/router/mainNav";

const SEARCH = "v=1&q={}&scope=all&tab=studies&page=1&pageSize=20";
const router = createRouter({ history: createMemoryHistory(), routes });

const entryAt = (path: string) => studyNavEntry(router.resolve(path));

describe("the entry of the main navigation of a study page", () => {
  it("is Studies for a study page without the data search, on every section", () => {
    expect(entryAt("/data/drug/Format2Fixture")).toBe("studies");
    expect(entryAt("/data/drug/Format2Fixture/data?source=paper")).toBe("studies");
    expect(entryAt("/data/drug/Format2Fixture/review")).toBe("studies");
  });

  it("is Explore data for a study page that keeps the data search that opened it", () => {
    expect(entryAt(`/data/drug/Format2Fixture?${SEARCH}`)).toBe("data");
    expect(entryAt(`/data/drug/Format2Fixture/data?${SEARCH}&file=outputs_Tab2.tsv`)).toBe("data");
  });

  it("leaves every other page to vue-router", () => {
    for (const path of ["/", "/studies", "/data", `/data?${SEARCH}`, "/data/PKDB00001", "/curation", "/account"]) {
      expect(entryAt(path), path).toBeNull();
    }
  });
});
