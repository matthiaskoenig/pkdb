import type { LocationQuery, RouteRecordNameGeneric } from "vue-router";
import { hasSearch } from "../features/search/codec";

/** An entry of the main navigation (App.vue) that a study page can belong to. */
export type MainNavEntry = "studies" | "data";

/**
 * The entry of the main navigation that a study page (`/data/:substance/:name/:section?`, the route
 * StudyByName) belongs to, which vue-router cannot tell from its path: Explore data when the page
 * keeps the data search that opened it, Studies otherwise. Null for every other page, whose entry
 * vue-router marks itself.
 */
export function studyNavEntry(route: { name?: RouteRecordNameGeneric | null; query: LocationQuery }): MainNavEntry | null {
  if (route.name !== "StudyByName") return null;
  return hasSearch(route.query) ? "data" : "studies";
}
