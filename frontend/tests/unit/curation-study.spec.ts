import { describe, expect, it } from "vitest";
import { ApiError } from "../../src/curation-app/api/client";
import type { ConflictData, ReviewItem, StudyDetail, TableEntry, TablesResult } from "../../src/curation-app/api/types";
import {
  actionFailure,
  approvalRefusal,
  dataTableFiles,
  defaultSection,
  duplicateFolders,
  duplicateHeading,
  findProfile,
  folderPath,
  isRawTable,
  rawTableFiles,
  isSection,
  issueLabel,
  knownProfiles,
  messageOf,
  newTable,
  openItems,
  profileMap,
  profileOf,
  provenanceLabel,
  railCounts,
  releaseLabel,
  sectionRoute,
  SECTIONS,
  tableFiles,
  tablesOutcome,
  userHint,
} from "../../src/curation-app/study";
import { profile, roster, studyDetail } from "./curation-fixtures";

function item(state: ReviewItem["state"], id: string = state): ReviewItem {
  return {
    id,
    kind: "question",
    state,
    text: "Is the mean read from the table?",
    author: "curator",
    created: "2026-10-05T10:12:00Z",
    thread: [],
  };
}

/** The Example detail with the review items `items` and the problem counts `counts`. */
function detail(items: ReviewItem[], counts = { errors: 0, warnings: 0 }, changes: Partial<StudyDetail> = {}) {
  return studyDetail({
    counts,
    review: { revision: "review-1", value: { status: "in_review", reviewers: [], items }, issues: [] },
    ...changes,
  });
}

describe("sections", () => {
  it("lists the six sections of the study page in the order of the rail", () => {
    expect(SECTIONS).toEqual(["metadata", "review", "problems", "sources", "tables", "activity"]);
    expect(isSection("review")).toBe(true);
    expect(isSection("figures")).toBe(false);
    expect(isSection(undefined)).toBe(false);
  });

  it("opens on Review when items are open, on Problems when there are errors, otherwise on Metadata", () => {
    expect(defaultSection(detail([item("open")], { errors: 2, warnings: 0 }))).toBe("review");
    expect(defaultSection(detail([item("resolved"), item("dismissed")], { errors: 2, warnings: 1 }))).toBe("problems");
    expect(defaultSection(detail([item("resolved")], { errors: 0, warnings: 3 }))).toBe("metadata");
    expect(defaultSection(studyDetail())).toBe("metadata");
  });

  it("routes to a section of a study, with a query when given", () => {
    expect(sectionRoute("caffeine/Example", "problems")).toEqual({
      name: "Study",
      params: { substance: "caffeine", name: "Example", section: "problems" },
    });
    expect(sectionRoute("caffeine/Example", "review", { item: "01JA" })).toEqual({
      name: "Study",
      params: { substance: "caffeine", name: "Example", section: "review" },
      query: { item: "01JA" },
    });
  });

  it("counts open items from the summary when review.json is invalid", () => {
    const invalid = studyDetail({
      summary: { ...studyDetail().summary, open_items: 2 },
      review: { revision: "review-1", value: null, issues: [] },
    });
    expect(openItems(invalid)).toBe(2);
    expect(defaultSection(invalid)).toBe("review");
  });
});

describe("railCounts", () => {
  it("counts open items, errors and warnings, sources, and table and raw table files", () => {
    const counts = railCounts(
      detail([item("open", "a"), item("open", "b"), item("resolved")], { errors: 2, warnings: 3 }),
    );
    // subjects, interventions, characteristica, outputs_Tab2, timecourses_Fig1 and the raw Example_Tab2.
    expect(counts).toEqual({ review: 2, problems: 5, sources: 2, tables: 6 });
  });

  it("counts zeros for an empty study", () => {
    expect(railCounts(studyDetail({ sources: [], files: ["study.json", "review.json"], tables: [] }))).toEqual({
      review: 0,
      problems: 0,
      sources: 0,
      tables: 0,
    });
  });
});

describe("tableFiles", () => {
  const tables: TableEntry[] = [
    { file: "subjects.tsv", kind: "subjects" },
    { file: "characteristica.tsv", kind: "characteristica" },
    { file: "outputs_Tab2.tsv", kind: "outputs" },
    { file: "outputs_Tab10.tsv", kind: "outputs" },
    { file: "scatters_Fig2.tsv", kind: "scatters" },
    { file: "Example_Tab2.tsv", kind: "raw" },
    { file: "Example_Tab10.tsv", kind: "raw" },
  ];

  it("keeps the tables in the order of the workbook sheets, as the server lists them", () => {
    expect(tableFiles({ tables })).toEqual([
      "subjects.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "outputs_Tab10.tsv",
      "scatters_Fig2.tsv",
      "Example_Tab2.tsv",
      "Example_Tab10.tsv",
    ]);
    expect(tableFiles({ tables: [] })).toEqual([]);
  });

  it("finds the raw tables by their kind", () => {
    expect(isRawTable({ tables }, "Example_Tab10.tsv")).toBe(true);
    expect(isRawTable({ tables }, "outputs_Tab10.tsv")).toBe(false);
    // A file that is no table of the study is no raw table.
    expect(isRawTable({ tables }, "Example_Tab3.tsv")).toBe(false);
    expect(isRawTable({ tables }, "study.json")).toBe(false);
    expect([...rawTableFiles({ tables })]).toEqual(["Example_Tab2.tsv", "Example_Tab10.tsv"]);
  });

  it("keeps the data tables, which the library loads as tables, without the raw tables", () => {
    expect([...dataTableFiles({ tables })]).toEqual([
      "subjects.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "outputs_Tab10.tsv",
      "scatters_Fig2.tsv",
    ]);
  });
});

describe("header labels", () => {
  it("names the release with its date", () => {
    expect(releaseLabel({ pkdb_id: "PKDB00198", date: "2026-09-28" })).toBe("PKDB00198 · released 2026-09-28");
  });

  it("names the issue with its labels", () => {
    const issue = { number: 2158, state: "open", labels: ["check"], assignees: [], url: null };
    expect(issueLabel(issue, 2158)).toBe("#2158 · check");
    expect(issueLabel({ ...issue, labels: ["check", "caffeine"] }, 2158)).toBe("#2158 · check, caffeine");
    expect(issueLabel({ ...issue, labels: [] }, 2158)).toBe("#2158");
    // Without the cached GitHub issue, the number of study.json.
    expect(issueLabel(null, 2158)).toBe("#2158");
    expect(issueLabel(null, null)).toBeNull();
  });

  it("names AI curation with its method", () => {
    expect(provenanceLabel({ provenance: { kind: "automatic_curation", method: "claude-opus-5-5" } })).toBe(
      "AI curated · claude-opus-5-5",
    );
    expect(provenanceLabel({ provenance: { kind: "automatic_curation" } })).toBe("AI curated");
    expect(provenanceLabel({ provenance: { kind: "data_import" } })).toBe("Data import");
    expect(provenanceLabel({ provenance: { kind: "manual_curation" } })).toBeNull();
    expect(provenanceLabel({})).toBeNull();
  });

  it("explains why approval was refused", () => {
    expect(approvalRefusal("1 review item is open")).toBe(
      "Approved needs zero open review items and zero validation errors. 1 review item is open.",
    );
    expect(approvalRefusal("Validation has 2 errors.")).toBe(
      "Approved needs zero open review items and zero validation errors. Validation has 2 errors.",
    );
  });
});

describe("paths", () => {
  it("joins the folder of a study to the workspace with its separator", () => {
    expect(folderPath("/work/pkdb_data", "caffeine/Example")).toBe("/work/pkdb_data/caffeine/Example");
    expect(folderPath("/work/pkdb_data/", "caffeine/Example")).toBe("/work/pkdb_data/caffeine/Example");
    expect(folderPath("C:\\work\\pkdb_data", "caffeine/Example")).toBe("C:\\work\\pkdb_data\\caffeine\\Example");
  });

  it("takes the folders of a duplicate identity from the 409 answer", () => {
    const paths = ["caffeine/Example", "archive, 2020/caffeine/Example"];
    expect(duplicateFolders({ error: "caffeine/Example is the identity of two folders", paths })).toEqual(paths);
    expect(duplicateFolders({ error: "Something else" })).toEqual([]);
    expect(duplicateFolders({ paths: ["a", 2, null] })).toEqual(["a"]);
  });

  it("counts the folders of a duplicate identity in the heading", () => {
    expect(duplicateHeading(2)).toBe("This identity belongs to two folders");
    expect(duplicateHeading(3)).toBe("This identity belongs to three folders");
    expect(duplicateHeading(12)).toBe("This identity belongs to 12 folders");
    expect(duplicateHeading(0)).toBe("This identity belongs to more than one folder");
  });
});

describe("newTable", () => {
  const example = studyDetail();

  it("previews the sheet, the file and the image of a data table", () => {
    expect(newTable(example, "outputs", "Tab3")).toEqual({
      sheet: "outputs_Tab3",
      file: "outputs_Tab3.tsv",
      image: "Example_Tab3.png",
      imageFound: false,
      payload: { table: "outputs_Tab3" },
      problem: null,
    });
    expect(newTable(example, "timecourses", " Fig1 ")).toMatchObject({
      sheet: "timecourses_Fig1",
      image: "Example_Fig1.png",
      imageFound: true,
    });
    // The text of the paper has no image.
    expect(newTable(example, "outputs", "Text")).toMatchObject({ image: null, problem: null });
  });

  it("names a raw table after the study folder", () => {
    expect(newTable(example, "raw", "Tab3")).toEqual({
      sheet: "Example_Tab3",
      file: "Example_Tab3.tsv",
      image: "Example_Tab3.png",
      imageFound: false,
      payload: { raw: "Tab3" },
      problem: null,
    });
  });

  it("explains why a table cannot be added", () => {
    expect(newTable(example, "outputs", "")).toBeNull();
    expect(newTable(example, "outputs", "3")?.problem).toBe(
      "Use a source such as Tab3, Fig2A or Text.",
    );
    expect(newTable(example, "raw", "Fig2")?.problem).toBe("A raw table needs a paper table source such as Tab3.");
    expect(newTable(example, "outputs", "tab2")?.problem).toBe("Use a source such as Tab3, Fig2A or Text.");
    expect(newTable(example, "outputs", "TAB2")?.problem).toBe("Use a source such as Tab3, Fig2A or Text.");
    expect(newTable(example, "outputs", "Tab2")?.problem).toBe("outputs_Tab2.tsv already exists.");
    expect(newTable(example, "raw", "Tab2")?.problem).toBe("Example_Tab2.tsv already exists.");
    expect(newTable(example, "timecourses", "Fig1_caffeine_plasma_D")?.problem).toBe(
      "The sheet timecourses_Fig1_caffeine_plasma_D has 34 characters. Excel allows 31.",
    );
  });
});

describe("people", () => {
  it("adds the people of the study who are not in the roster", () => {
    const outside = profile("jdoe", "Jane Doe", false);
    const people = { creator: profile("curator", "Someone else"), curators: [], collaborators: [outside] };
    const profiles = knownProfiles(roster(), people);
    expect([...profiles.keys()]).toEqual(["janekg", "mkoenig", "curator", "jdoe"]);
    // The roster wins for someone in both.
    expect(profiles.get("curator")?.display_name).toBe("Curator");
    expect(knownProfiles([], null).size).toBe(0);
  });

  it("names an unknown user by the user name", () => {
    const profiles = knownProfiles(roster(), null);
    expect(profileOf(profiles, "mkoenig").display_name).toBe("Matthias König");
    expect(profileOf(profiles, "agent-7")).toEqual({
      username: "agent-7",
      display_name: "agent-7",
      title: null,
      affiliation: null,
      avatar_url: null,
    });
  });

  it("matches a user name whatever its case, as the local server does, on every page", () => {
    // The overview keys the roster with profileMap, the study page with knownProfiles.
    for (const profiles of [profileMap(roster()), knownProfiles(roster(), null)]) {
      expect(findProfile(profiles, "MKoenig")?.username).toBe("mkoenig");
      expect(profileOf(profiles, "MKOENIG").display_name).toBe("Matthias König");
    }
    expect(findProfile(profileMap(roster()), "agent-7")).toBeUndefined();
  });
});

describe("failures", () => {
  it("names the message of a failure and what to do without a user", () => {
    expect(messageOf(new Error("Disk full"))).toBe("Disk full");
    expect(messageOf("refused")).toBe("refused");
    expect(userHint(new ApiError(403, { error: "no_user", message: "Set a user." }))).toBe(
      "Set your PK-DB user in Connection settings.",
    );
    expect(userHint(new ApiError(403, { error: "user_mismatch", message: "The key is of janekg." }))).toBe(
      "The key is of janekg.",
    );
  });

  it("lists three issues of a failed action and counts the others", () => {
    expect(actionFailure("Refused.", ["a", "b", "c", "d", "e"])).toEqual({
      text: "Refused.",
      issues: ["a", "b", "c"],
      more: 2,
      link: null,
    });
  });

  it("says what Open tables found: nothing for a clean sync, else the issues and the conflicts", () => {
    const result: TablesResult = {
      ok: true,
      workbook_action: "unchanged",
      changes: [],
      conflicts: [],
      issues: [],
      opened: true,
    };
    expect(tablesOutcome(result)).toBeNull();
    expect(tablesOutcome({ ...result, opened: false })).toEqual(actionFailure("The workbook could not be opened."));
    const conflict: ConflictData = {
      file: "outputs_Tab2.tsv",
      kind: "outputs",
      sheet: "outputs_Tab2",
      workbook_rows: [],
      table_lines: [],
      base_lines: [],
      kept: null,
      removed: null,
    };
    const conflicts = [conflict, conflict, { ...conflict, kept: "tables" as const }];
    expect(tablesOutcome({ ...result, ok: false, conflicts })).toEqual(
      actionFailure("The workbook opened, but the sync found problems.", ["2 sheets conflict with their tables."], {
        section: "tables",
        label: "Show the conflicts",
      }),
    );
  });
});
