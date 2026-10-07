import { describe, expect, it } from "vitest";
import { splitPath } from "../../src/curation-app/paths";

describe("splitPath", () => {
  it.each([
    ["/work/pkdb_data", { name: "pkdb_data", parent: "/work" }],
    ["/work/pkdb_data/", { name: "pkdb_data", parent: "/work" }],
    ["/work", { name: "work", parent: "/" }],
    ["/", { name: "/", parent: "" }],
    ["C:\\Users\\curator\\pkdb_data", { name: "pkdb_data", parent: "C:\\Users\\curator" }],
    ["pkdb_data", { name: "pkdb_data", parent: "" }],
  ])("splits %s", (path, parts) => {
    expect(splitPath(path)).toEqual(parts);
  });
});
