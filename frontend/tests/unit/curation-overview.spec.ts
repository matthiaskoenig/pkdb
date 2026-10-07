import { describe, expect, it } from "vitest";
import type { StudyRow } from "../../src/curation-app/api/types";
import {
  activityLabel,
  chipCounts,
  filterStudies,
  formatTime,
  issueUrl,
  needsAttention,
  plural,
  problemLabels,
  REVIEW_LABELS,
  sortStudies,
  substancesOf,
  SYNC_LABELS,
  uploadBlocker,
  type StatusChip,
} from "../../src/curation-app/overview";
import { snapshot, studyRow } from "./curation-fixtures";

/** A row of `<substance>/<name>` with the given summary changes. */
function row(id: string, changes: Partial<StudyRow> = {}, summary: Partial<StudyRow["summary"]> = {}): StudyRow {
  const [substance = "", name = ""] = id.split("/");
  const base = studyRow();
  return studyRow({
    id,
    name,
    substance,
    path: `studies/${id}`,
    ...changes,
    summary: { ...base.summary, ...summary },
  });
}

const example = row("caffeine/Example", {}, { title: "Caffeine pharmacokinetics" });
const harder = row("caffeine/Harder1988", {}, {
  title: "Effect of smoking on caffeine",
  review_status: "in_review",
  open_items: 2,
});
const approved = row("codeine/Kirchheiner2007", {}, {
  title: "Codeine in CYP2D6 ultrarapid metabolizers",
  review_status: "approved",
});
const broken = row("caffeine/Broken1999", { status: "invalid", counts: { errors: 3, warnings: 0 } });
const conflict = row("midazolam/Conflict2001", { sync: { status: "conflict", changes: 0, conflicts: 2 } });
const rows = [example, harder, approved, broken, conflict];

function ids(result: StudyRow[]): string[] {
  return result.map((item) => item.id);
}

describe("filterStudies", () => {
  const all = { search: "", substance: "", chip: "all" as StatusChip };

  it("keeps every row without filters", () => {
    expect(ids(filterStudies(rows, all))).toEqual(ids(rows));
  });

  it("matches the identity and the title ignoring case", () => {
    expect(ids(filterStudies(rows, { ...all, search: "HARDER" }))).toEqual(["caffeine/Harder1988"]);
    expect(ids(filterStudies(rows, { ...all, search: "caffeine/ex" }))).toEqual(["caffeine/Example"]);
    expect(ids(filterStudies(rows, { ...all, search: "cyp2d6" }))).toEqual(["codeine/Kirchheiner2007"]);
    expect(ids(filterStudies(rows, { ...all, search: "  smoking " }))).toEqual(["caffeine/Harder1988"]);
    expect(filterStudies(rows, { ...all, search: "no such study" })).toEqual([]);
  });

  it("matches a row without a title by its identity", () => {
    const untitled = row("caffeine/Untitled", {}, { title: null });
    expect(ids(filterStudies([untitled], { ...all, search: "untitled" }))).toEqual(["caffeine/Untitled"]);
    expect(filterStudies([untitled], { ...all, search: "pharmacokinetics" })).toEqual([]);
  });

  it("keeps the rows of one substance", () => {
    expect(ids(filterStudies(rows, { ...all, substance: "codeine" }))).toEqual(["codeine/Kirchheiner2007"]);
  });

  it.each<[StatusChip, string[]]>([
    ["all", ids(rows)],
    ["attention", ["caffeine/Harder1988", "caffeine/Broken1999", "midazolam/Conflict2001"]],
    ["draft", ["caffeine/Example", "caffeine/Broken1999", "midazolam/Conflict2001"]],
    ["in_review", ["caffeine/Harder1988"]],
    ["approved", ["codeine/Kirchheiner2007"]],
  ])("keeps the rows of the chip %s", (chip, expected) => {
    expect(ids(filterStudies(rows, { ...all, chip }))).toEqual(expected);
  });

  it("combines the search, the substance and the chip", () => {
    expect(ids(filterStudies(rows, { search: "caffeine", substance: "caffeine", chip: "draft" }))).toEqual([
      "caffeine/Example",
      "caffeine/Broken1999",
    ]);
  });

  it("counts the rows of every chip", () => {
    expect(chipCounts(rows)).toEqual({ all: 5, attention: 3, draft: 3, in_review: 1, approved: 1 });
  });
});

describe("needsAttention", () => {
  it("is true for errors", () => {
    expect(needsAttention(row("a/b", { counts: { errors: 1, warnings: 0 } }))).toBe(true);
  });

  it("is true for a sync conflict", () => {
    expect(needsAttention(row("a/b", { sync: { status: "conflict", changes: 0, conflicts: 1 } }))).toBe(true);
  });

  it("is true for open items while in review", () => {
    expect(needsAttention(row("a/b", {}, { review_status: "in_review", open_items: 1 }))).toBe(true);
  });

  it("is false otherwise", () => {
    expect(needsAttention(row("a/b"))).toBe(false);
    expect(needsAttention(row("a/b", { counts: { errors: 0, warnings: 4 } }))).toBe(false);
    expect(needsAttention(row("a/b", {}, { review_status: "draft", open_items: 3 }))).toBe(false);
    expect(needsAttention(row("a/b", {}, { review_status: "in_review", open_items: 0 }))).toBe(false);
    expect(needsAttention(row("a/b", { sync: { status: "changed", changes: 2, conflicts: 0 } }))).toBe(false);
  });
});

describe("sortStudies", () => {
  it("sorts by identity in both directions", () => {
    expect(ids(sortStudies(rows, { key: "study", descending: false }))).toEqual([
      "caffeine/Broken1999",
      "caffeine/Example",
      "caffeine/Harder1988",
      "codeine/Kirchheiner2007",
      "midazolam/Conflict2001",
    ]);
    expect(ids(sortStudies(rows, { key: "study", descending: true }))[0]).toBe("midazolam/Conflict2001");
  });

  it("sorts numbers numerically and equal rows by identity", () => {
    const many = [
      row("a/x", {}, { open_items: 10 }),
      row("a/y", {}, { open_items: 9 }),
      row("a/w", {}, { open_items: 9 }),
    ];
    expect(ids(sortStudies(many, { key: "open_items", descending: false }))).toEqual(["a/w", "a/y", "a/x"]);
    expect(ids(sortStudies(many, { key: "open_items", descending: true }))).toEqual(["a/x", "a/w", "a/y"]);
  });

  it("weighs errors over warnings", () => {
    const sorted = sortStudies(
      [
        row("a/warnings", { counts: { errors: 0, warnings: 9 } }),
        row("a/error", { counts: { errors: 1, warnings: 0 } }),
        row("a/clean"),
      ],
      { key: "problems", descending: true },
    );
    expect(ids(sorted)).toEqual(["a/error", "a/warnings", "a/clean"]);
  });

  it("puts rows without a value last in both directions", () => {
    const released = row("a/released", {}, { release: { pkdb_id: "PKDB00198", date: "2026-09-28" } });
    const older = row("a/older", {}, { release: { pkdb_id: "PKDB00017", date: "2020-01-01" } });
    const unreleased = row("a/unreleased");
    expect(ids(sortStudies([unreleased, released, older], { key: "release", descending: false }))).toEqual([
      "a/older",
      "a/released",
      "a/unreleased",
    ]);
    expect(ids(sortStudies([unreleased, released, older], { key: "release", descending: true }))).toEqual([
      "a/released",
      "a/older",
      "a/unreleased",
    ]);
  });

  it("sorts the review status from draft to approved and does not change its input", () => {
    const input = [approved, harder, example];
    expect(ids(sortStudies(input, { key: "review", descending: false }))).toEqual([
      "caffeine/Example",
      "caffeine/Harder1988",
      "codeine/Kirchheiner2007",
    ]);
    expect(ids(input)).toEqual(["codeine/Kirchheiner2007", "caffeine/Harder1988", "caffeine/Example"]);
  });
});

describe("labels", () => {
  it("names the review states", () => {
    expect(REVIEW_LABELS).toEqual({ draft: "Draft", in_review: "In review", approved: "Approved" });
  });

  it("names every sync state", () => {
    expect(SYNC_LABELS).toEqual({
      in_sync: "In sync",
      workbook_open: "Workbook open",
      syncing: "Syncing",
      changed: "Changed",
      conflict: "Conflict",
      no_workbook: "No workbook",
      unknown: "Unknown",
      not_checked: "Not checked yet",
    });
  });

  it("counts errors and warnings, and calls a passed check valid", () => {
    const labels = (changes: Partial<StudyRow>) => problemLabels(row("a/b", changes)).map((item) => item.label);
    expect(labels({ counts: { errors: 2, warnings: 0 } })).toEqual(["2 errors"]);
    expect(labels({ counts: { errors: 0, warnings: 1 } })).toEqual(["1 warning"]);
    expect(labels({ counts: { errors: 1, warnings: 3 } })).toEqual(["1 error", "3 warnings"]);
    expect(labels({ status: "valid" })).toEqual(["valid"]);
    // No check has passed yet.
    expect(labels({ status: "discovered" })).toEqual([]);
    expect(labels({ status: "validating" })).toEqual([]);
  });

  it("tells what a study does until its check is finished", () => {
    expect(activityLabel(row("a/b", { status: "queued" }))).toBe("Queued");
    expect(activityLabel(row("a/b", { status: "discovered" }))).toBe("Not validated yet");
    expect(activityLabel(row("a/b", { status: "unknown" }))).toBe("Upload outcome unknown");
    expect(activityLabel(row("a/b", { status: "valid" }))).toBeNull();
    expect(activityLabel(row("a/b", { status: "invalid" }))).toBeNull();
  });

  it("writes counts with thousands separators", () => {
    expect(plural(1412, "folder")).toBe("1,412 folders");
    expect(plural(1, "folder")).toBe("1 folder");
    expect(plural(0, "error")).toBe("0 errors");
    expect(plural(2, "study", "studies")).toBe("2 studies");
    expect(plural(1, "study", "studies")).toBe("1 study");
  });

  it("writes a local date and time", () => {
    expect(formatTime("2026-10-01T12:00:00Z")).toMatch(/^2026-10-01 \d\d:\d\d$/);
    expect(formatTime("not a time")).toBe("not a time");
  });

  it("tells why uploads are not possible", () => {
    expect(uploadBlocker(snapshot({ can_upload: true }))).toBeNull();
    expect(uploadBlocker(snapshot({ offline: true }))).toBe(
      "Work offline is on. Turn it off in the settings to upload.",
    );
    expect(uploadBlocker(snapshot({ offline: false, authenticated: false }))).toBe(
      "Add your personal API key in the settings to upload.",
    );
    expect(uploadBlocker(snapshot({ offline: false, authenticated: true, connection: "error" }))).toBe(
      "The PK-DB server is not connected.",
    );
    expect(uploadBlocker(snapshot({ offline: false, authenticated: true, connection: "connected" }))).toBe(
      "Your PK-DB account cannot upload studies.",
    );
  });

  it("links an issue to GitHub, by default in the configured repository", () => {
    const issue = { number: 2158, state: "open", labels: [], assignees: [], url: "https://github.com/o/r/issues/2158" };
    expect(issueUrl(row("a/b", { issue }), "x/y")).toBe("https://github.com/o/r/issues/2158");
    expect(issueUrl(row("a/b", { issue: { ...issue, url: null } }), "matthiaskoenig/pkdb_data")).toBe(
      "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
    );
    expect(issueUrl(row("a/b", { issue: { ...issue, url: null } }), "")).toBeNull();
    expect(issueUrl(row("a/b"), "matthiaskoenig/pkdb_data")).toBeNull();
  });

  it("lists the substances in order", () => {
    expect(substancesOf(rows)).toEqual(["caffeine", "codeine", "midazolam"]);
  });
});
