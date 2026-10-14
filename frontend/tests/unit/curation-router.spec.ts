import { describe, expect, it } from "vitest";
import type { RouteLocationNormalized, Router } from "vue-router";
import { makeRouter } from "../../src/curation-app/router";
import { curationRoutes } from "../../src/curation-app/routes";

/** The route of `path` as a navigation sees it; every route of the app has a name. */
function route(router: Router, path: string): RouteLocationNormalized {
  const resolved = router.resolve(path);
  const name = resolved.name;
  if (name === null || name === undefined) throw new Error(`${path} has no named route`);
  return { ...resolved, name };
}

/** Where the router scrolls the window after a navigation from `from` to `to`. */
function scrollAfter(from: string, to: string, saved: { left: number; top: number } | null = null): unknown {
  const router = makeRouter();
  const behavior = router.options.scrollBehavior;
  if (!behavior) throw new Error("The router has no scroll behavior");
  return behavior(route(router, to), route(router, from), saved);
}

describe("the scroll behavior of the router", () => {
  it("shows the top of another section", () => {
    expect(scrollAfter("/studies/caffeine/Demo2020/data", "/studies/caffeine/Demo2020/metadata")).toEqual({
      top: 0,
    });
  });

  it("shows the top of a study opened from the overview", () => {
    expect(scrollAfter("/", "/studies/caffeine/Demo2020/review")).toEqual({ top: 0 });
  });

  it("keeps the position when only the query changes, such as the row of the Data section", () => {
    expect(
      scrollAfter("/studies/caffeine/Demo2020/data?file=subjects.tsv", "/studies/caffeine/Demo2020/data?file=subjects.tsv&line=3"),
    ).toBe(false);
  });

  it("goes back to the saved position on back and forward", () => {
    const saved = { left: 0, top: 480 };
    expect(scrollAfter("/studies/caffeine/Demo2020/review", "/", saved)).toEqual(saved);
  });
});

describe("the old addresses of the Sources and Tables sections", () => {
  it.each([
    ["/studies/caffeine/Demo2020/tables?file=outputs_Tab2.tsv&line=3&column=mean", { file: "outputs_Tab2.tsv", line: "3", column: "mean" }],
    ["/studies/caffeine/Demo2020/sources?source=Fig1", { source: "Fig1" }],
    ["/studies/caffeine/Demo2020/tables", {}],
  ])("redirects %s to the Data section with its query", async (path, query) => {
    const router = makeRouter();
    await router.push(path);
    expect(router.currentRoute.value.name).toBe("Study");
    expect(router.currentRoute.value.params).toEqual({ substance: "caffeine", name: "Demo2020", section: "data" });
    expect(router.currentRoute.value.query).toEqual(query);
  });

  it("leaves the other sections alone", async () => {
    const router = makeRouter();
    await router.push("/studies/caffeine/Demo2020/review?item=01JA");
    expect(router.currentRoute.value.fullPath).toBe("/studies/caffeine/Demo2020/review?item=01JA");
  });
});

describe("the route of a paper in a tab of its own", () => {
  it("names the study and the file, and shows no app bar", () => {
    const route = makeRouter().resolve(curationRoutes.paper("caffeine/Demo2020", "Demo2020 Supp.pdf")!);
    expect(route.href).toBe("#/studies/caffeine/Demo2020/paper/Demo2020%20Supp.pdf");
    expect(route.name).toBe("Paper");
    expect(route.params).toEqual({ substance: "caffeine", name: "Demo2020", file: "Demo2020 Supp.pdf" });
    expect(route.meta.bare).toBe(true);
  });
});
