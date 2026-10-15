/**
 * The address of the Studies page (#963): its search, Substance and Curator filters, status chip
 * and order, with the defaults left out, so that a list can be linked and Back returns to it. A
 * status or an order that the reader does not see reads as the default (`statusChips`,
 * `sortableKeys`), and the page then replaces the address.
 */
import type { LocationQuery } from "vue-router";
import type { StudyCapabilities } from "../../study-views/context";
import { statusChips, type StatusChip, type StudySort } from "../../study-views/overview";
import { sortableKeys } from "../../study-views/studyTable";

export interface ListState {
  search: string;
  substance: string;
  curator: string;
  chip: StatusChip;
  sort: StudySort;
}

export const DEFAULT_SORT: StudySort = { key: "study", descending: false };

/** The first text of a value of the query, or "". */
function single(value: LocationQuery[string] | undefined): string {
  const first = Array.isArray(value) ? value[0] : value;
  return typeof first === "string" ? first : "";
}

export function readListQuery(query: LocationQuery, capabilities: Pick<StudyCapabilities, "curation" | "jobs">): ListState {
  const status = single(query.status);
  const sortKey = single(query.sort);
  const key = sortableKeys(capabilities).find((value) => value === sortKey);
  return {
    search: single(query.search),
    substance: single(query.substance),
    curator: single(query.curator),
    chip: statusChips(capabilities).find((value) => value === status) ?? "all",
    sort: key ? { key, descending: single(query.order) === "desc" } : DEFAULT_SORT,
  };
}

export function listQuery(state: ListState): Record<string, string> {
  const query: Record<string, string> = {};
  if (state.search) query.search = state.search;
  if (state.substance) query.substance = state.substance;
  if (state.curator) query.curator = state.curator;
  if (state.chip !== "all") query.status = state.chip;
  if (state.sort.key !== DEFAULT_SORT.key || state.sort.descending) query.sort = state.sort.key;
  if (state.sort.descending) query.order = "desc";
  return query;
}

/** Whether the address has exactly the keys and values of `query`. */
export function sameQuery(current: LocationQuery, query: Record<string, string>): boolean {
  const keys = Object.keys(query);
  return Object.keys(current).length === keys.length && keys.every((key) => current[key] === query[key]);
}
