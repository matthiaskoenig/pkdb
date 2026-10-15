import { describe, expect, it } from "vitest";
import type { Profile } from "../../src/study-views/types";
import { REVIEW_LABELS, SYNC_LABELS } from "../../src/study-views/overview";
import {
  bodyParts,
  keepSizerRows,
  OVERSCAN,
  ROW_HEIGHT,
  rowItem,
  sameParts,
  sizerRows,
} from "../../src/study-views/studyTable";
import { studyRow } from "./curation-fixtures";

const profiles = new Map<string, Profile>([
  [
    "mkoenig",
    { username: "mkoenig", display_name: "Matthias König", title: null, affiliation: null, avatar_url: "/a.webp" },
  ],
]);

describe("rowItem", () => {
  it("shows two curators and counts the others beyond three", () => {
    const row = studyRow({ summary: { ...studyRow().summary, curators: ["mkoenig", "janekg", "curator", "alice"] } });
    const item = rowItem(row, profiles, "matthiaskoenig/pkdb_data");
    expect(item.curators).toEqual([
      { name: "Matthias König", avatar: "/a.webp", initials: "MK" },
      { name: "janekg", avatar: null, initials: "J" },
    ]);
    expect(item.hidden).toBe(2);
    expect(item.others).toBe("curator, alice");
  });

  it("links the issue of the configured repository and only web pages of uploads", () => {
    const row = studyRow({
      summary: { ...studyRow().summary, issue: 12 },
      last_upload: { persistence: "replaced", at: "2026-10-01T12:00:00Z", endpoint: "x", url: "javascript:alert(1)" },
    });
    const item = rowItem(row, profiles, "matthiaskoenig/pkdb_data");
    expect(item.issue).toEqual({ number: 12, url: "https://github.com/matthiaskoenig/pkdb_data/issues/12" });
    expect(item.upload).toBeNull();
  });
});

describe("bodyParts", () => {
  it("renders the rows in the window and the overscan, and space for the others", () => {
    expect(bodyParts({ count: 1000, top: 0, height: 240, pinned: null }, 24, 2)).toEqual([
      ...Array.from({ length: 12 }, (_, index) => ({ kind: "row", index })),
      { kind: "space", rows: 988, key: "space-12" },
    ]);
  });

  it("follows the scrolled body with space above", () => {
    // The body scrolled 2,400 px above the window: rows 100 to 109 are in view.
    const parts = bodyParts({ count: 1000, top: -2400, height: 240, pinned: null }, 24, 2);
    expect(parts[0]).toEqual({ kind: "space", rows: 98, key: "space-0" });
    expect(parts.filter((part) => part.kind === "row").map((part) => part.index)).toEqual(
      Array.from({ length: 14 }, (_, index) => 98 + index),
    );
    expect(parts.at(-1)).toEqual({ kind: "space", rows: 888, key: "space-112" });
  });

  it("keeps a pinned row wherever it is, between spaces", () => {
    const parts = bodyParts({ count: 1000, top: -2400, height: 240, pinned: 3 }, 24, 2);
    expect(parts.slice(0, 3)).toEqual([
      { kind: "space", rows: 3, key: "space-0" },
      { kind: "row", index: 3 },
      { kind: "space", rows: 94, key: "space-4" },
    ]);
  });

  it("renders every row of a short table and no space after the last row", () => {
    const parts = bodyParts({ count: 3, top: 100, height: 800, pinned: null });
    expect(parts).toEqual([0, 1, 2].map((index) => ({ kind: "row", index })));
  });

  it("compares parts by their rows and spaces", () => {
    const window = { count: 100, top: 0, height: 250, pinned: null };
    expect(sameParts(bodyParts(window), bodyParts({ ...window, top: -5 }))).toBe(true);
    expect(sameParts(bodyParts(window), bodyParts({ ...window, top: -ROW_HEIGHT * (OVERSCAN + 1) }))).toBe(false);
  });
});

describe("sizerRows", () => {
  const draft = studyRow();
  const review = studyRow({ id: "a/r", path: "a/r", summary: { ...draft.summary, review_status: "in_review", ai: true } });
  const approved = studyRow({ id: "a/a", path: "a/a", summary: { ...draft.summary, review_status: "approved" } });
  const unchecked = studyRow({ id: "a/u", path: "a/u", sync: { status: "not_checked", changes: 0, conflicts: 0 } });
  const crowded = studyRow({ id: "a/c", path: "a/c", summary: { ...draft.summary, curators: ["a", "b", "c", "d", "e"] } });

  it("has no rows without rows", () => {
    expect(sizerRows([])).toEqual([]);
  });

  it("shows every distinct cell of each column in one of its rows, without an identity", () => {
    const sizers = sizerRows([draft, review, approved, unchecked, crowded]);
    expect(new Set(sizers.map((row) => REVIEW_LABELS[row.summary.review_status!]))).toEqual(
      new Set(["Draft", "In review", "Approved"]),
    );
    expect(sizers.some((row) => row.summary.ai)).toBe(true);
    expect(new Set(sizers.map((row) => SYNC_LABELS[row.sync!.status]))).toEqual(
      new Set([SYNC_LABELS[draft.sync!.status], "Not checked yet"]),
    );
    expect(sizers.some((row) => row.summary.curators?.length === 5)).toBe(true);
    expect(sizers.every((row) => row.id === "" && !row.duplicate)).toBe(true);
    expect(new Set(sizers.map((row) => row.path)).size).toBe(sizers.length);
  });

  it("keeps the rows of the last sizing that show the same cells, so that they render once", () => {
    const rows = [draft, review, approved, unchecked, crowded];
    const before = sizerRows(rows);
    // A search that keeps a row of every cell, and a poll that brings new objects of the same rows.
    expect(keepSizerRows(before, sizerRows([crowded, unchecked, approved, review]))).toBe(before);
    expect(keepSizerRows(before, sizerRows(rows.map((row) => structuredClone(row))))).toBe(before);
    // A longer message changes the cell of one row; the other rows stay.
    const message = studyRow({ id: "a/m", path: "a/m", message: "The connection closed" });
    const after = keepSizerRows(before, sizerRows([...rows, message]));
    expect(after).not.toBe(before);
    expect(after.filter((row) => row.message === message.message)).toHaveLength(1);
    expect(after.filter((row) => before.includes(row)).length).toBe(before.length - 1);
  });

  it("sizes the cells of the curation of the rows that the reader may write, also after a row of the website without it", () => {
    const other = studyRow({ id: "a/o", path: "a/o", curator: false });
    delete other.summary.issue;
    delete other.sync;
    const written = studyRow({ id: "a/w", path: "a/w", curator: true, summary: { ...draft.summary, issue: 2158 } });
    const sizers = sizerRows([other, written]);
    expect(sizers.every((row) => !("curator" in row))).toBe(true);
    expect(sizers.some((row) => row.summary.issue === 2158)).toBe(true);
  });

  it("takes the longest cells first beyond the limit", () => {
    const many = Array.from({ length: 20 }, (_, index) =>
      studyRow({ id: `a/${index}`, path: `a/${index}`, message: "m".repeat(index + 1) }),
    );
    const sizers = sizerRows(many, 3);
    expect(sizers).toHaveLength(3);
    expect(sizers.map((row) => row.message?.length)).toEqual([20, 19, 18]);
  });
});
