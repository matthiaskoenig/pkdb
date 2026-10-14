import { describe, expect, it } from "vitest";
import { curationRoutes } from "../../src/curation-app/routes";
import { makeRouter } from "../../src/curation-app/router";

describe("the routes of the study views in the curation app", () => {
  it("name the routes of the hash router", () => {
    expect(curationRoutes.overview()).toEqual({ name: "Overview" });
    expect(curationRoutes.study("caffeine/Example")).toEqual({
      name: "Study",
      params: { substance: "caffeine", name: "Example" },
    });
    expect(curationRoutes.section("caffeine/Example", "problems")).toEqual({
      name: "Study",
      params: { substance: "caffeine", name: "Example", section: "problems" },
    });
    expect(curationRoutes.section("caffeine/Example", "review", { item: "01JA" })).toEqual({
      name: "Study",
      params: { substance: "caffeine", name: "Example", section: "review" },
      query: { item: "01JA" },
    });
    expect(curationRoutes.paper("caffeine/Example", "Example Supp.pdf")).toEqual({
      name: "Paper",
      params: { substance: "caffeine", name: "Example", file: "Example Supp.pdf" },
    });
  });

  it("resolve to the addresses of the app", () => {
    const router = makeRouter();
    expect(router.resolve(curationRoutes.overview()).href).toBe("#/");
    expect(router.resolve(curationRoutes.study("caffeine/Example")).href).toBe("#/studies/caffeine/Example");
    expect(router.resolve(curationRoutes.section("caffeine/Example", "data", { file: "subjects.tsv", line: "2" })).href).toBe(
      "#/studies/caffeine/Example/data?file=subjects.tsv&line=2",
    );
    expect(router.resolve(curationRoutes.paper("caffeine/Demo2020", "Demo2020 Supp.pdf")!).href).toBe(
      "#/studies/caffeine/Demo2020/paper/Demo2020%20Supp.pdf",
    );
  });

  it("know the study and the section of a route of the study page, and of no other route", async () => {
    const router = makeRouter();
    await router.push("/studies/caffeine/Example/review?item=01JA");
    expect(curationRoutes.current(router.currentRoute.value)).toEqual({ id: "caffeine/Example", section: "review" });
    await router.push("/studies/caffeine/Example");
    expect(curationRoutes.current(router.currentRoute.value)).toEqual({ id: "caffeine/Example", section: null });
    await router.push("/studies/caffeine/Example/paper/Example.pdf");
    expect(curationRoutes.current(router.currentRoute.value)).toBeNull();
    await router.push("/");
    expect(curationRoutes.current(router.currentRoute.value)).toBeNull();
  });

  it("give a section the query it asks for", () => {
    expect(curationRoutes.query({ notes: "subjects", file: "a.tsv" }, { file: "b.tsv" })).toEqual({ file: "b.tsv" });
  });
});
