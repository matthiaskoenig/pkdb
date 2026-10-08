import { describe, expect, it } from "vitest";
import type { RouteLocationNormalized, Router } from "vue-router";
import { makeRouter } from "../../src/curation-app/router";

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
    expect(scrollAfter("/studies/caffeine/Demo2020/sources", "/studies/caffeine/Demo2020/metadata")).toEqual({
      top: 0,
    });
  });

  it("shows the top of a study opened from the overview", () => {
    expect(scrollAfter("/", "/studies/caffeine/Demo2020/review")).toEqual({ top: 0 });
  });

  it("keeps the position when only the query changes, such as the table of the Tables section", () => {
    expect(
      scrollAfter("/studies/caffeine/Demo2020/tables?file=subjects.tsv", "/studies/caffeine/Demo2020/tables?file=outputs_Tab2.tsv"),
    ).toBe(false);
  });

  it("goes back to the saved position on back and forward", () => {
    const saved = { left: 0, top: 480 };
    expect(scrollAfter("/studies/caffeine/Demo2020/review", "/", saved)).toEqual(saved);
  });
});
