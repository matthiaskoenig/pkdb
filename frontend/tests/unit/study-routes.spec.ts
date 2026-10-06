import { describe, expect, it } from "vitest";
import { router } from "../../src/router";
import { detailPath } from "../../src/features/details/types";
import {
  studyApiPath,
  studyLocation,
  studyPath,
} from "../../src/features/details/studyPath";

function studyProps(path: string): unknown {
  const route = router.resolve(path);
  const props = route.matched[0]?.props.default;
  if (typeof props === "function")
    return props({ ...route, name: route.name ?? undefined });
  return props === true ? route.params : props;
}

describe("study routes", () => {
  it("serves a study format 2 study by substance and name", () => {
    const route = router.resolve("/data/caffeine/Harder1988");
    expect(route.name).toBe("StudyByName");
    expect(route.params).toEqual({ substance: "caffeine", name: "Harder1988" });
    expect(studyProps("/data/caffeine/Harder1988")).toEqual({
      sid: "caffeine/Harder1988",
    });
  });
  it("keeps the single segment for study format 1 sids and PKDB identifiers", () => {
    for (const sid of ["PKDB00198", "FRONTEND_SCOPE"]) {
      const route = router.resolve(`/data/${sid}`);
      expect(route.name).toBe("DataSingle");
      expect(studyProps(`/data/${sid}`)).toEqual({ sid });
    }
  });
  it("decodes names and ignores deeper paths", () => {
    expect(studyProps("/data/caffeine/Name%20(2)")).toEqual({
      sid: "caffeine/Name (2)",
    });
    expect(router.resolve("/data/caffeine/Name/extra").name).toBe("NotFound");
    expect(router.resolve("/data").name).toBe("Data");
  });
});

describe("study links", () => {
  it("split a canonical sid into two segments only when it has a substance", () => {
    expect(studyLocation("caffeine/Harder1988")).toBe(
      "/data/caffeine/Harder1988",
    );
    expect(studyLocation("PKDB00198")).toBe("/data/PKDB00198");
    expect(studyLocation("a b/c#d?")).toBe("/data/a%20b/c%23d%3F");
    expect(studyApiPath("caffeine/Harder1988")).toBe(
      "/api/v1/studies/caffeine/Harder1988/",
    );
    expect(studyApiPath("PKDB00198")).toBe("/api/v1/studies/PKDB00198/");
    expect(studyPath("caffeine/Harder1988")).toBe("caffeine/Harder1988");
  });
  it("resolve to the study page of the same sid", () => {
    for (const sid of ["caffeine/Harder1988", "PKDB00198", "a b/c#d?"]) {
      expect(studyProps(studyLocation(sid))).toEqual({ sid });
    }
  });
  it("are used to read a study record", () => {
    expect(detailPath("study", "caffeine/Harder1988")).toBe(
      "/api/v1/studies/caffeine/Harder1988/",
    );
    expect(detailPath("studies", "PKDB00198")).toBe(
      "/api/v1/studies/PKDB00198/",
    );
    expect(detailPath("groups", 4)).toBe("/api/v1/groups/4/");
  });
});
