import { describe, expect, it } from "vitest";
import { ApiError } from "../../src/study-views/errors";
import type { TablesResult } from "../../src/curation-app/api/types";
import { drawsOnImage, plottedSeries } from "../../src/study-views/overlay";
import type { ConflictData, Problem, ReviewItem, SourceView, StudyDetail, TableEntry } from "../../src/study-views/types";
import {
  actionFailure,
  beyondLimits,
  defaultSection,
  failureOf,
  findProfile,
  isLimitIssue,
  isRawTable,
  rawTableFiles,
  isSection,
  issueLabel,
  knownProfiles,
  messageOf,
  openItems,
  profileMap,
  profileOf,
  provenanceLabel,
  releaseLabel,
  sectionCounts,
  SECTION_LABELS,
  SECTIONS,
  tableFiles,
  viewWithoutFiles,
  visibleSections,
  withoutFiles,
} from "../../src/study-views/study";
import {
  approvalRefusal,
  duplicateFolders,
  duplicateHeading,
  folderPath,
  lastUploadUrl,
  tablesOutcome,
  userHint,
} from "../../src/curation-app/local";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";
import { beyondLimitsDetail, paperFile, profile, roster, studyDetail, tableEntry } from "./curation-fixtures";

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
  it("lists the five sections of the study page in the order of the work on a study", () => {
    expect(SECTIONS).toEqual(["metadata", "data", "problems", "review", "activity"]);
    expect(SECTIONS.map((section) => SECTION_LABELS[section])).toEqual([
      "Metadata",
      "Data",
      "Problems",
      "Review",
      "Activity",
    ]);
    expect(isSection("data")).toBe(true);
    expect(isSection("tables")).toBe(false);
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

  it("counts open items from the summary when review.json is invalid", () => {
    const invalid = studyDetail({
      summary: { ...studyDetail().summary, open_items: 2 },
      review: { revision: "review-1", value: null, issues: [] },
    });
    expect(openItems(invalid)).toBe(2);
    expect(defaultSection(invalid)).toBe("review");
  });
});

describe("sectionCounts", () => {
  it("counts open items, and errors plus warnings; the Data section has no count", () => {
    const counts = sectionCounts(
      detail([item("open", "a"), item("open", "b"), item("resolved")], { errors: 2, warnings: 3 }),
    );
    expect(counts).toEqual({ review: 2, problems: 5 });
  });

  it("counts zeros for an empty study", () => {
    expect(sectionCounts(studyDetail({ sources: [], files: ["study.json", "review.json"], tables: [] }))).toEqual({
      review: 0,
      problems: 0,
    });
  });

  it("counts the limit of a study beyond the upload limits as a problem", () => {
    const review = { revision: "review-1", value: { status: "in_review" as const, reviewers: [], items: [item("open")] }, issues: [] };
    expect(sectionCounts(beyondLimitsDetail({ review }))).toEqual({ review: 1, problems: 1 });
  });
});

describe("beyondLimits", () => {
  it("knows a study beyond the upload limits by its problems, not by its empty lists", () => {
    expect(beyondLimits(beyondLimitsDetail())).toBe(true);
    expect(beyondLimits(studyDetail({ sources: [], tables: [], files: [] }))).toBe(false);
    const unit: Problem = { code: "unit_dimension", severity: "error", message: "mg is no concentration", acknowledgeable: false };
    expect(isLimitIssue(unit)).toBe(false);
    expect(beyondLimits(studyDetail({ problems: [unit] }))).toBe(false);
  });
});

describe("tableFiles", () => {
  const tables: TableEntry[] = [
    tableEntry("subjects.tsv", "subjects"),
    tableEntry("characteristica.tsv", "characteristica"),
    tableEntry("outputs_Tab2.tsv", "outputs"),
    tableEntry("outputs_Tab10.tsv", "outputs"),
    tableEntry("scatters_Fig2.tsv", "scatters"),
    tableEntry("Example_Tab2.tsv", "raw"),
    tableEntry("Example_Tab10.tsv", "raw"),
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
      details: null,
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
        section: "data",
        label: "Show the conflicts",
      }),
    );
  });

  it("takes the details of the local server into a failure, after a lead for a refusal only", () => {
    const failed = new ApiError(500, {
      error: "Could not read reference.json of caffeine/Example.",
      code: "invalid_request",
      detail: "JSONDecodeError: Expecting value",
      action: "Read reference.json (POST /local/reference/read)",
      request_id: "3f9c2a71",
      time: "2026-10-12T14:03:11+02:00",
    });
    const failure = failureOf(failed, "reference.json could not be read.");
    expect(failure.text).toBe("Could not read reference.json of caffeine/Example.");
    expect(failure.details?.detail).toBe("JSONDecodeError: Expecting value");
    const refused = new ApiError(400, {
      error: "Reference preview expired; preview again",
      code: "reference_refused",
      detail: null,
      action: "Save reference.json (POST /local/reference/save)",
      request_id: "0badc0de",
      time: "2026-10-12T14:03:11+02:00",
    });
    expect(failureOf(refused, "reference.json was not saved.").text).toBe(
      "reference.json was not saved. Reference preview expired; preview again",
    );
    expect(failureOf(new Error("Disk full"))).toEqual(actionFailure("Disk full"));
  });
});

describe("lastUploadUrl", () => {
  const upload = { at: "2026-10-01T10:12:00Z", url: "https://beta.pk-db.com/data/Example" };

  it("is the page of the last upload on the web", () => {
    expect(lastUploadUrl(studyDetail({ last_upload: upload } as Partial<StudyDetail>))).toBe(
      "https://beta.pk-db.com/data/Example",
    );
  });

  it("is null without an upload and for a URL that is not a web page", () => {
    expect(lastUploadUrl(studyDetail())).toBeNull();
    expect(lastUploadUrl(studyDetail({ last_upload: { ...upload, url: "javascript:alert(1)" } } as Partial<StudyDetail>))).toBeNull();
  });
});

describe("what a reader sees of a study", () => {
  it("shows Problems and Review only with the curation, and Activity only with the jobs", () => {
    expect(visibleSections({ curation: false, jobs: false })).toEqual(["metadata", "data"]);
    expect(visibleSections({ curation: true, jobs: false })).toEqual(["metadata", "data", "problems", "review"]);
    expect(visibleSections({ curation: true, jobs: true })).toEqual(["metadata", "data", "problems", "review", "activity"]);
  });

  it("leaves out the PDFs, the raw tables and the images of the sources without the files", () => {
    const shown = withoutFiles(studyDetail({ papers: [paperFile("Example.pdf")] }));
    expect(shown.papers).toEqual([]);
    expect(shown.tables.map((table) => table.file)).not.toContain("Example_Tab2.tsv");
    expect(shown.sources.map((source) => source.image_url)).toEqual([null, null]);
    expect(shown.sources.map((source) => source.image)).toEqual(["Example_Fig1.png", "Example_Tab2.png"]);
  });

  it("plots every series of a digitized figure without the files, as it has no image to draw them on", () => {
    const figure = sourceFixture as unknown as SourceView;
    expect(plottedSeries(figure)).toEqual([]);
    const shown = viewWithoutFiles({ ...figure, raw_grid: [["x", "y"]] });
    expect([shown.image_url, shown.image_size, shown.raw_grid]).toEqual([null, null, null]);
    expect(shown.image).toBe("Demo2020_Fig1.png");
    expect(drawsOnImage(shown)).toBe(false);
    expect(plottedSeries(shown)).toEqual(["caf_plasma_100mg", "caf_plasma_200mg"]);
  });
});
