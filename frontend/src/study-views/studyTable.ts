/**
 * The rows of the study table of the overview: what each row shows besides the fields of its
 * study, which rows a window of the page renders, and the rows that size the columns.
 */
import type { Profile, StudyRow, StudySummary } from "./types";
import {
  activityLabel,
  issueUrl,
  problemLabels,
  REVIEW_LABELS,
  SYNC_LABELS,
  type Tone,
  webUrl,
} from "./overview";
import { findProfile } from "./study";

/** The circles of the curators of a row: avatars, or avatars and a count of the others. */
const CURATOR_SLOTS = 3;

export interface Curator {
  name: string;
  avatar: string | null;
  initials: string;
}

/** What a row shows besides the fields of its study row. */
export interface RowItem {
  row: StudyRow;
  curators: Curator[];
  /** The names of the curators that the count stands for. */
  others: string;
  /** How many curators the count stands for. */
  hidden: number;
  problems: { label: string; tone: Tone }[];
  activity: string | null;
  issue: { number: number; url: string } | null;
  upload: string | null;
}

function curatorOf(user: string, profiles: ReadonlyMap<string, Profile>): Curator {
  const profile = findProfile(profiles, user);
  const name = profile?.display_name ?? user;
  const words = name.split(/\s+/).filter(Boolean);
  const initials = (words.length > 1 ? `${words[0]![0]}${words.at(-1)![0]}` : name.slice(0, 1)).toUpperCase();
  return { name, avatar: profile?.avatar_url ?? null, initials };
}

/** The item of `row`; the study table builds it once per row object, so once per snapshot. */
export function rowItem(row: StudyRow, profiles: ReadonlyMap<string, Profile>, repository: string): RowItem {
  const people = (row.summary.curators ?? []).map((user) => curatorOf(user, profiles));
  // Beyond the slots, the last slot counts the curators that it hides.
  const cut = people.length > CURATOR_SLOTS ? CURATOR_SLOTS - 1 : people.length;
  const number = row.issue?.number ?? row.summary.issue ?? null;
  const url = issueUrl(row, repository);
  return {
    row,
    curators: people.slice(0, cut),
    others: people
      .slice(cut)
      .map((person) => person.name)
      .join(", "),
    hidden: people.length - cut,
    problems: problemLabels(row),
    activity: activityLabel(row),
    issue: number !== null && url !== null ? { number, url } : null,
    upload: webUrl(row.last_upload?.url),
  };
}

export function aiTitle(row: StudyRow): string {
  const method = row.summary.provenance?.method;
  return method ? `AI curated with ${method}` : "AI curated";
}

// The window of the body

/**
 * The height of a row in pixels at the default font size: every study keeps one line. StudyTable.vue
 * measures a rendered row, as a larger font makes rows taller, and takes this height until it can.
 */
export const ROW_HEIGHT = 24;
/** The rows rendered beyond each edge of the window, so that scrolling and Tab meet rendered rows. */
export const OVERSCAN = 10;

export interface BodyWindow {
  /** The rows of the body. */
  count: number;
  /** The distance of the top of the first row from the top of the window; negative once it scrolled above. */
  top: number;
  /** The height of the window. */
  height: number;
  /** A row that stays rendered wherever it is, as the row with the keyboard focus; null for none. */
  pinned: number | null;
}

/** A part of the body: a rendered row, or the space of rows that are not rendered. */
export type BodyPart = { kind: "row"; index: number } | { kind: "space"; rows: number; key: string };

/**
 * The parts of a body: the rows in the window and `overscan` rows beyond each edge, the pinned
 * row, and a space for each run of rows between them.
 */
export function bodyParts(
  { count, top, height, pinned }: BodyWindow,
  rowHeight = ROW_HEIGHT,
  overscan = OVERSCAN,
): BodyPart[] {
  const clamp = (value: number) => Math.min(count, Math.max(0, value));
  const first = clamp(Math.floor(-top / rowHeight) - overscan);
  const last = clamp(Math.ceil((height - top) / rowHeight) + overscan);
  const indices: number[] = [];
  for (let index = first; index < last; index++) indices.push(index);
  if (pinned !== null && pinned >= 0 && pinned < count && (pinned < first || pinned >= last)) {
    indices.push(pinned);
    indices.sort((a, b) => a - b);
  }
  const parts: BodyPart[] = [];
  let next = 0;
  for (const index of indices) {
    if (index > next) parts.push({ kind: "space", rows: index - next, key: `space-${next}` });
    parts.push({ kind: "row", index });
    next = index + 1;
  }
  if (count > next) parts.push({ kind: "space", rows: count - next, key: `space-${next}` });
  return parts;
}

/** Whether two lists of parts render the same rows and spaces. */
export function sameParts(a: readonly BodyPart[], b: readonly BodyPart[]): boolean {
  return (
    a.length === b.length &&
    a.every((part, place) => {
      const other = b[place]!;
      if (part.kind === "row") return other.kind === "row" && other.index === part.index;
      return other.kind === "space" && other.rows === part.rows && other.key === part.key;
    })
  );
}

// The rows that size the columns

/** The most rows that size the columns of the table. */
const SIZER_LIMIT = 12;

/** A column of the table as its sizer rows see it. */
interface SizedColumn {
  /** The class of the cells of the column, as in StudyTable.vue and StudyTableRow.vue. */
  cell: string;
  /** The text that the cell of `row` shows, as far as it decides the width of the column. */
  text: (row: StudyRow) => string;
  /** The fields of the row that the cell shows. */
  fields?: readonly (keyof StudyRow)[];
  /** The fields of the summary of the row that the cell shows. */
  summary?: readonly (keyof StudySummary)[];
}

/**
 * The columns after Study, in the order of the table (`columns` of StudyTable.vue). Study takes
 * the room that the other columns leave, so it needs no sizing.
 */
const SIZED_COLUMNS: readonly SizedColumn[] = [
  {
    cell: "cell-release",
    // Every release is `PKDB` and five tabular digits.
    text: (row) => (row.summary.release ? "release" : "-"),
    summary: ["release"],
  },
  {
    cell: "cell-issue",
    text: (row) => String(row.issue?.number ?? row.summary.issue ?? "-"),
    fields: ["issue"],
    summary: ["issue"],
  },
  {
    cell: "cell-curators",
    text: (row) => {
      const count = row.summary.curators?.length ?? 0;
      return count > CURATOR_SLOTS ? `${CURATOR_SLOTS - 1}+${count - CURATOR_SLOTS + 1}` : String(count);
    },
    summary: ["curators"],
  },
  {
    cell: "cell-review",
    text: (row) =>
      `${row.summary.review_status ? REVIEW_LABELS[row.summary.review_status] : "-"}${row.summary.ai ? " AI" : ""}`,
    summary: ["review_status", "ai", "provenance"],
  },
  {
    cell: "cell-open",
    // Tabular digits: the number of digits decides.
    text: (row) => String(row.summary.open_items ?? 0).replace(/\d/g, "0"),
    summary: ["open_items"],
  },
  {
    cell: "cell-problems",
    text: (row) =>
      [
        ...problemLabels(row).map(({ label }) => label),
        activityLabel(row) ?? "",
        row.message ?? "",
        row.status === "unknown" ? "Review" : "",
      ].join(" "),
    fields: ["status", "counts", "message"],
  },
  { cell: "cell-sync", text: (row) => SYNC_LABELS[row.sync.status], fields: ["sync"] },
  {
    cell: "cell-upload",
    // Every upload shows a date and time in tabular digits.
    text: (row) => (row.last_upload ? "upload" : "-"),
    fields: ["last_upload"],
  },
];

/** The cell classes of the sized columns, in the order of the table. */
export const SIZED_CELLS: readonly string[] = SIZED_COLUMNS.map((column) => column.cell);

/** `target` with the fields `keys` of `source`, without those that `source` leaves out. */
function withFields<T extends object>(target: T, source: T, keys: readonly (keyof T)[] = []): T {
  const result = { ...target };
  for (const key of keys) {
    if (key in source) result[key] = source[key];
    else delete (result as Partial<T>)[key];
  }
  return result;
}

/** `target` with the cell of `column` of `source`. */
function withCell(target: StudyRow, source: StudyRow, column: SizedColumn): StudyRow {
  const row = withFields(target, source, column.fields);
  return column.summary ? { ...row, summary: withFields(row.summary, source.summary, column.summary) } : row;
}

/**
 * Rows that together show every distinct cell of each column of `rows`, the longest first beyond
 * `limit`: hidden in the table, they give the columns the widths of all rows while only some
 * rows render. They have no identity, as they stand for no study.
 */
export function sizerRows(rows: readonly StudyRow[], limit = SIZER_LIMIT): StudyRow[] {
  const first = rows[0];
  if (!first) return [];
  const choices = SIZED_COLUMNS.map((column) => {
    const byText = new Map<string, StudyRow>();
    for (const row of rows) {
      const text = column.text(row);
      if (!byText.has(text)) byText.set(text, row);
    }
    return [...byText.entries()]
      .sort(([a], [b]) => b.length - a.length)
      .slice(0, limit)
      .map(([, row]) => row);
  });
  const count = Math.max(...choices.map((options) => options.length));
  return Array.from({ length: count }, (_, place) =>
    SIZED_COLUMNS.reduce<StudyRow>(
      (target, column, at) => {
        const options = choices[at]!;
        return withCell(target, options[Math.min(place, options.length - 1)]!, column);
      },
      { ...first, id: "", name: "", path: `sizer-${place}`, duplicate: false },
    ),
  );
}

/** The cells that a sizer row shows: the fields of the row and of its summary that the columns show. */
function shownCells(row: StudyRow): string {
  return JSON.stringify(
    SIZED_COLUMNS.flatMap((column) => [
      ...(column.fields ?? []).map((key) => row[key]),
      ...(column.summary ?? []).map((key) => row.summary[key]),
    ]),
  );
}

/**
 * `next` with the rows of `previous` that show the same cells at their places, or `previous` itself
 * when all of them do: a row that stays renders only once, also through the new objects of a poll.
 */
export function keepSizerRows(previous: readonly StudyRow[], next: readonly StudyRow[]): readonly StudyRow[] {
  const kept = next.map((row, place) => {
    const old = previous[place];
    return old && shownCells(old) === shownCells(row) ? old : row;
  });
  return kept.length === previous.length && kept.every((row, place) => row === previous[place]) ? previous : kept;
}
