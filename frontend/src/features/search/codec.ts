import { asRecord } from "../../api/contracts";
import { defaultCriteria, defaultView } from "./defaults";
import { fieldKeys } from "./fields";
import { tabs } from "./model";
import type { Criteria, SearchLocation, ResultTab } from "./model";
import { validOrder } from "../results/columns";
const fail = (): never => {
  throw new Error(
    "This search URL is invalid or unsupported. Check the link, or reset the search explicitly.",
  );
};
function booleans(
  value: unknown,
  keys: readonly string[],
): Record<string, boolean> {
  const r = asRecord(value);
  if (
    Object.keys(r).length !== keys.length ||
    keys.some((k) => typeof r[k] !== "boolean")
  )
    return fail();
  return Object.fromEntries(keys.map((k) => [k, r[k] === true]));
}
export function canonicalCriteria(criteria: Criteria): Criteria {
  const filters: Record<string, string[]> = {};
  for (const key of Object.keys(criteria.filters).sort()) {
    const values = criteria.filters[key] ?? [];
    if (
      !fieldKeys.has(key) ||
      values.some(
        (v) =>
          typeof v !== "string" ||
          !v.trim() ||
          v.includes("__") ||
          v.length > 300,
      )
    )
      return fail();
    if (values.length) filters[key] = [...new Set(values)].sort();
  }
  if (criteria.scope !== "matching" && criteria.scope !== "studies")
    return fail();
  return {
    ...criteria,
    filters,
    subjects: { ...criteria.subjects },
    licences: { ...criteria.licences },
    types: { ...criteria.types },
  };
}
export function criteriaKey(criteria: Criteria): string {
  return JSON.stringify(canonicalCriteria(criteria));
}
export function encodeLocation(
  location: SearchLocation,
): Record<string, string> {
  const c = canonicalCriteria(location.criteria),
    { scope, ...query } = c,
    v = location.view;
  return {
    v: "1",
    q: JSON.stringify(query),
    scope,
    tab: v.tab,
    page: String(v.page),
    pageSize: String(v.pageSize),
    ...(v.order ? { order: v.order } : {}),
    ...(v.tableSearch ? { tableSearch: v.tableSearch } : {}),
  };
}
export function decodeLocation(query: Record<string, unknown>): SearchLocation {
  if (!Object.keys(query).length)
    return { criteria: defaultCriteria(), view: defaultView() };
  const allowed = new Set([
    "v",
    "q",
    "scope",
    "tab",
    "page",
    "pageSize",
    "order",
    "tableSearch",
  ]);
  if (
    Object.keys(query).some(
      (k) => !allowed.has(k) || typeof query[k] !== "string",
    ) ||
    query.v !== "1"
  )
    return fail();
  let c = defaultCriteria();
  try {
    if (query.q !== undefined) {
      const raw: unknown = JSON.parse(String(query.q)),
        r = asRecord(raw);
      if (
        Object.keys(r).length !== 4 ||
        !["filters", "subjects", "licences", "types"].every((k) => k in r)
      )
        return fail();
      const f = asRecord(r.filters),
        filters: Record<string, string[]> = {};
      for (const [k, v] of Object.entries(f)) {
        if (
          !fieldKeys.has(k) ||
          !Array.isArray(v) ||
          !v.every((x) => typeof x === "string")
        )
          return fail();
        filters[k] = v;
      }
      const sub = booleans(r.subjects, ["groups", "individuals"]),
        lic = booleans(r.licences, ["open", "closed"]),
        types = booleans(r.types, ["output", "timecourse", "array"]);
      c = {
        ...c,
        filters,
        subjects: {
          groups: sub.groups === true,
          individuals: sub.individuals === true,
        },
        licences: { open: lic.open === true, closed: lic.closed === true },
        types: {
          output: types.output === true,
          timecourse: types.timecourse === true,
          array: types.array === true,
        },
      };
    }
  } catch {
    return fail();
  }
  const scope = query.scope ?? "matching";
  if (scope !== "matching" && scope !== "studies") return fail();
  c.scope = scope;
  const tab = query.tab ?? "studies";
  if (!tabs.some((t) => t === tab)) return fail();
  const resultTab = tab as ResultTab;
  const page = Number(query.page ?? 1),
    pageSize = Number(query.pageSize ?? 20),
    order = String(query.order ?? ""),
    tableSearch = String(query.tableSearch ?? "");
  if (
    !Number.isSafeInteger(page) ||
    page < 1 ||
    ![20, 50, 100].includes(pageSize) ||
    !validOrder(resultTab, order) ||
    tableSearch.length > 300
  )
    return fail();
  return {
    criteria: canonicalCriteria(c),
    view: { tab: resultTab, page, pageSize, order, tableSearch },
  };
}
