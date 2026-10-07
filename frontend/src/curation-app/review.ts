/**
 * Filters, labels, targets and failed writes of the review items of the study page.
 */
import { isNoUser, isRevisionConflict, isValidationError } from "./api/client";
import type { ReviewItem, ReviewTarget, TableRow } from "./api/types";
import { plural, type Tone } from "./overview";
import { messageOf, userHint } from "./study";

export type ItemKind = ReviewItem["kind"];
export type ItemState = ReviewItem["state"];

/** An action on an existing item. */
export type ItemAction = "reply" | "resolve" | "dismiss" | "reopen";

/** The state chips above the items. */
export type StateFilter = ItemState | "all";

/** The kind filter: one kind, or all of them. */
export type KindFilter = ItemKind | "all";

export const STATE_CHIPS: readonly { value: StateFilter; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "resolved", label: "Resolved" },
  { value: "dismissed", label: "Dismissed" },
  { value: "all", label: "All" },
];

export const STATE_LABELS: Record<ItemState, string> = {
  open: "Open",
  resolved: "Resolved",
  dismissed: "Dismissed",
};

/** Open items are amber, as the rows that they target in the Tables section. */
export const STATE_TONES: Record<ItemState, Tone> = {
  open: "warning",
  resolved: "success",
  dismissed: undefined,
};

export const KIND_LABELS: Record<ItemKind, string> = {
  question: "Question",
  uncertainty: "Uncertainty",
  issue: "Issue",
};

const KIND_PLURALS: Record<ItemKind, string> = {
  question: "questions",
  uncertainty: "uncertainties",
  issue: "issues",
};

export const KIND_ICONS: Record<ItemKind, string> = {
  question: "fas fa-circle-question",
  uncertainty: "fas fa-scale-unbalanced",
  issue: "fas fa-triangle-exclamation",
};

export const KINDS: readonly ItemKind[] = ["question", "uncertainty", "issue"];

/** The items of the kind filter. */
export const KIND_FILTERS: readonly { title: string; value: KindFilter }[] = [
  { title: "All kinds", value: "all" },
  ...KINDS.map((kind) => ({ title: KIND_LABELS[kind], value: kind })),
];

function matches(item: ReviewItem, state: StateFilter, kind: KindFilter): boolean {
  return (state === "all" || item.state === state) && (kind === "all" || item.kind === kind);
}

/** The items of a state and a kind, in the order of review.json. */
export function filterItems(items: readonly ReviewItem[], state: StateFilter, kind: KindFilter): ReviewItem[] {
  return items.filter((item) => matches(item, state, kind));
}

/** The number of items of the kind behind each state chip. */
export function stateCounts(items: readonly ReviewItem[], kind: KindFilter): Record<StateFilter, number> {
  return Object.fromEntries(
    STATE_CHIPS.map(({ value }) => [value, filterItems(items, value, kind).length]),
  ) as Record<StateFilter, number>;
}

/** What the list says when the filters leave no item: `No open items.`, `No dismissed uncertainties.` */
export function emptyText(state: StateFilter, kind: KindFilter): string {
  if (state === "all" && kind === "all") return "No review items yet.";
  const noun = kind === "all" ? "items" : KIND_PLURALS[kind];
  return state === "all" ? `No ${noun}.` : `No ${STATE_LABELS[state].toLowerCase()} ${noun}.`;
}

/** `timecourses_Fig1.tsv · label = caf_plasma_D150 · column error_type`, or `Whole study` without a file. */
export function targetText(target: ReviewTarget | null | undefined): string {
  if (!target?.file) return "Whole study";
  const rows = Object.entries(target.rows ?? {})
    .map(([column, value]) => `${column} = ${value}`)
    .join(", ");
  return [target.file, rows, target.column ? `column ${target.column}` : ""].filter(Boolean).join(" · ");
}

/** A timecourse or scatter table of a figure, `timecourses_<Fig>.tsv` or `scatters_<Fig>.tsv`. */
const FIGURE_TABLE = /^(timecourses|scatters)_(Fig[A-Za-z0-9_-]+)\.tsv$/;

/** The column that names the series of a figure table, as the datasets of its digitization. */
const SERIES_COLUMNS: Record<string, string> = { timecourses: "label", scatters: "name" };

/**
 * The digitized series that a target names: the `label` rows of the timecourse table of a figure
 * and the `name` rows of its scatter table are series of the figure; null for any other target.
 */
export function seriesOfTarget(target: ReviewTarget | null | undefined): { source: string; series: string } | null {
  const match = target?.file ? FIGURE_TABLE.exec(target.file) : null;
  const series = match ? target?.rows?.[SERIES_COLUMNS[match[1]!]!] : undefined;
  return match && series ? { source: match[2]!, series } : null;
}

/** The rows whose cells, as printed in the TSV file, have every value of `filters`. */
export function matchingRows(header: readonly string[], rows: readonly TableRow[], filters: Record<string, string>): TableRow[] {
  const wanted = Object.entries(filters).map(([column, value]) => [header.indexOf(column), value] as const);
  return rows.filter((row) => wanted.every(([index, value]) => index >= 0 && (row.cells[index] ?? "") === value));
}

/** `Matches 2 of 3 rows.`, or `Matches none of 3 rows.` */
export function matchText(matched: number, total: number): string {
  return `Matches ${matched === 0 ? "none" : matched.toLocaleString("en-US")} of ${plural(total, "row")}.`;
}

/** The indices of the columns that have a value in one of `rows`, and of the columns in `keep`. */
export function shownColumns(header: readonly string[], rows: readonly TableRow[], keep: readonly string[]): number[] {
  if (rows.length === 0) return [];
  return header
    .map((column, index) => ({ column, index }))
    .filter(({ column, index }) => keep.includes(column) || rows.some((row) => (row.cells[index] ?? "") !== ""))
    .map(({ index }) => index);
}

// Failed writes

/** What a write over a stale revision of review.json says; the store has reloaded the items. */
export const REVIEW_CONFLICT = "review.json changed on disk; the items were reloaded. Repeat your action.";

/** Why a write of review.json failed: a stale revision, a missing user, or a refusal with its issues. */
export type ReviewFailure =
  | { kind: "conflict"; text: string }
  | { kind: "user"; text: string }
  | { kind: "error"; text: string; issues: string[] };

/** The failure of a write; `refused` says what did not happen, such as `The item was not resolved.` */
export function reviewFailure(caught: unknown, refused: string): ReviewFailure {
  if (isRevisionConflict(caught)) return { kind: "conflict", text: REVIEW_CONFLICT };
  if (isNoUser(caught)) return { kind: "user", text: userHint(caught) };
  if (isValidationError(caught) && caught.body.issues.length)
    return { kind: "error", text: refused, issues: caught.body.issues.map((issue) => issue.message) };
  return { kind: "error", text: `${refused} ${messageOf(caught)}`, issues: [] };
}
