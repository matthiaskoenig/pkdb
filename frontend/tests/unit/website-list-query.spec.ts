import { describe, expect, it } from "vitest";
import { DEFAULT_SORT, listQuery, readListQuery, sameQuery } from "../../src/features/studies/listQuery";

const PUBLIC = { curation: false, jobs: false };
const CURATOR = { curation: true, jobs: false };

describe("the address of the Studies page", () => {
  it("reads the search, the filters, the status and the order that the reader sees", () => {
    expect(
      readListQuery({ search: "caf", substance: "drug", curator: "curator", status: "attention", sort: "review", order: "desc" }, CURATOR),
    ).toEqual({
      search: "caf",
      substance: "drug",
      curator: "curator",
      chip: "attention",
      sort: { key: "review", descending: true },
    });
  });

  it("reads a status or an order of the curation as the default for a reader without the curation", () => {
    const state = readListQuery({ status: "attention", sort: "review", order: "desc", search: "caf" }, PUBLIC);
    expect(state.chip).toBe("all");
    expect(state.sort).toEqual(DEFAULT_SORT);
    expect(listQuery(state)).toEqual({ search: "caf" });
  });

  it("never sorts by the jobs of a local server, and reads unknown values as the defaults", () => {
    expect(readListQuery({ sort: "sync" }, CURATOR).sort).toEqual(DEFAULT_SORT);
    expect(readListQuery({ status: "nonsense", sort: "nonsense" }, CURATOR)).toMatchObject({ chip: "all", sort: DEFAULT_SORT });
    expect(readListQuery({ search: ["a", "b"] }, CURATOR).search).toBe("a");
  });

  it("writes only what differs from the defaults, and the order of a descending study sort", () => {
    expect(listQuery(readListQuery({}, PUBLIC))).toEqual({});
    expect(listQuery({ ...readListQuery({}, PUBLIC), sort: { key: "study", descending: true } })).toEqual({ sort: "study", order: "desc" });
    expect(listQuery({ ...readListQuery({}, CURATOR), chip: "in_review", sort: { key: "release", descending: false } })).toEqual({
      status: "in_review",
      sort: "release",
    });
  });

  it("compares an address with a query by its keys and values, in any order", () => {
    expect(sameQuery({ sort: "review", search: "caf" }, { search: "caf", sort: "review" })).toBe(true);
    expect(sameQuery({ sort: "review", status: "attention" }, { sort: "review" })).toBe(false);
    expect(sameQuery({ search: ["caf", "x"] }, { search: "caf" })).toBe(false);
  });
});
