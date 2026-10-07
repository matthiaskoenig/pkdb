import { describe, expect, it } from "vitest";
import { pathSegments, splitPath } from "../../src/curation-app/paths";

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

describe("pathSegments", () => {
  it.each([
    ["/work/pkdb_data", ["/", "work/", "pkdb_data"]],
    ["/work/a-long-name/", ["/", "work/", "a-long-name/"]],
    ["C:\\Users\\curator", ["C:\\", "Users\\", "curator"]],
    ["pkdb_data", ["pkdb_data"]],
  ])("splits %s after each separator", (path, segments) => {
    expect(pathSegments(path)).toEqual(segments);
    expect(pathSegments(path).join("")).toBe(path);
  });
});
