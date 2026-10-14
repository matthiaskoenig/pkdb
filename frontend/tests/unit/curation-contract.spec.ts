/**
 * The front-end side of the contract fixtures: real answers of the local API, written by
 * python/tests/test_curation_contract.py. Regenerate them there with PKDB_UPDATE_CONTRACT=1.
 */
import { describe, expect, it } from "vitest";
import type { TablePreview, TablesResult } from "../../src/curation-app/api/types";
import type {
  AcknowledgedWarning,
  ConflictData,
  Job,
  PaperFile,
  Problem,
  ReviewItem,
  SourceSummary,
  StudyRow,
  SourceView,
  StudyDetail,
  Suggestion,
  TableEntry,
  TableKindEntry,
  TableResponse,
  TargetMatch,
  ValidationIssue,
} from "../../src/study-views/types";
import { isTablePreview, isTablesResult } from "../../src/curation-app/api/types";
import { isSourceView, isTargetMatch } from "../../src/study-views/types";
import { filterStudies, problemLabels } from "../../src/curation-app/overview";
import { jobText, messageParts } from "../../src/curation-app/activity";
import { columnClass, columnCount, columnName, itemsWithoutRows, targetLines, targetMatch } from "../../src/curation-app/grid";
import { cellParts, namedKind } from "../../src/curation-app/links";
import { issueMessage } from "../../src/curation-app/metadata";
import { legendEntries, overlayTraces, plotTraces } from "../../src/curation-app/overlay";
import { ApiError } from "../../src/study-views/errors";
import { detailsOfBody } from "../../src/curation-app/failures";
import { acknowledgement, locationKey, openPlace, scopeText, suggestionView } from "../../src/curation-app/problems";
import {
  acknowledgeFailure,
  AMBIGUOUS_WARNING,
  NO_EXACT_TARGET,
  NO_SUCH_WARNING,
} from "../../src/curation-app/acknowledging";
import { matchText, targetText } from "../../src/curation-app/review";
import { beyondLimits, isLimitIssue, isRawTable, sectionCounts, tableFiles } from "../../src/curation-app/study";
import { addableKinds, kindLabel, noteKinds } from "../../src/curation-app/tableKinds";
import { conflictView } from "../../src/curation-app/tables";
import { defaultFile, fileForSource, sourceOfFile } from "../../src/curation-app/data";
import openTablesFixture from "../fixtures/curation-contract/open-tables.json";
import problemsFixture from "../fixtures/curation-contract/problems.json";
import errorsFixture from "../fixtures/curation-contract/errors.json";
import acknowledgementsFixture from "../fixtures/curation-contract/acknowledgements.json";
import messagesFixture from "../fixtures/curation-contract/messages.json";
import nameLinesFixture from "../fixtures/curation-contract/name-lines.json";
import rowsFixture from "../fixtures/curation-contract/rows.json";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";
import outputsSourceFixture from "../fixtures/curation-contract/source-outputs-fig2.json";
import sourcesFixture from "../fixtures/curation-contract/sources.json";
import tableContentFixture from "../fixtures/curation-contract/table-content.json";
import tablePreviewFixture from "../fixtures/curation-contract/table-preview.json";
import tablesFixture from "../fixtures/curation-contract/tables.json";
import targetsFixture from "../fixtures/curation-contract/targets.json";
import { BEYOND_LIMITS, reviewItem, studyDetail, SUBJECTS_COLUMNS } from "./curation-fixtures";

/** A fixture as the type of the app; the fixture is a real answer of the server. */
function contract<T>(value: unknown): T {
  return value as T;
}

describe("limits contract", () => {
  it("knows a study beyond each upload limit by the limit, its first problem", () => {
    expect(BEYOND_LIMITS.map((detail) => detail.problems[0]?.code)).toEqual(["file_limit", "row_limit"]);
    for (const detail of BEYOND_LIMITS) {
      expect(isLimitIssue(detail.problems[0]!)).toBe(true);
      expect(beyondLimits(detail)).toBe(true);
      // The limit is the one problem that the sections count.
      expect(sectionCounts(studyDetail({ ...detail, counts: { errors: 1, warnings: 0 } }))).toEqual({ review: 0, problems: 1 });
    }
  });
});

describe("tables contract", () => {
  const tables = contract<TableEntry[]>(tablesFixture.tables);
  const conflicts = contract<ConflictData[]>(tablesFixture.conflicts);
  const conflict = (kind: string) => conflicts.find((entry) => entry.kind === kind)!;

  it("lists the tables of a study in the order of the workbook sheets", () => {
    expect(tableFiles({ tables })).toEqual([
      "subjects.tsv",
      "characteristica.tsv",
      "interventions.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Demo2020_Tab2.tsv",
    ]);
    expect(isRawTable({ tables }, "Demo2020_Tab2.tsv")).toBe(true);
    expect(isRawTable({ tables }, "outputs_Tab2.tsv")).toBe(false);
  });

  it("names the class of information, the source and the data rows of each table", () => {
    expect(tables.map(({ file, kind, info, source, rows }) => [file, kind, info, source, rows])).toEqual([
      ["subjects.tsv", "subjects", "subjects", null, 1],
      ["characteristica.tsv", "characteristica", "subjects", null, 6],
      ["interventions.tsv", "interventions", "interventions", null, 3],
      ["outputs_Tab2.tsv", "outputs", "data", "Tab2", 8],
      ["timecourses_Fig1.tsv", "timecourses", "data", "Fig1", 18],
      ["Demo2020_Tab2.tsv", "raw", "raw", "Tab2", 6],
    ]);
  });

  it("describes every kind of table, and Add table adds the kinds that the library adds", () => {
    const kinds = contract<TableKindEntry[]>(tablesFixture.table_kinds);
    expect(kinds.map((entry) => [entry.kind, entry.label, entry.info, entry.per_source, entry.addable])).toEqual([
      ["subjects", "Subjects", "subjects", false, false],
      ["characteristica", "Characteristica", "subjects", false, false],
      ["interventions", "Interventions", "interventions", false, false],
      ["outputs", "Outputs", "data", true, true],
      ["timecourses", "Timecourses", "data", true, true],
      ["scatters", "Scatters", "data", true, true],
      ["raw", "Raw table", "raw", true, true],
    ]);
    expect(kinds.filter((entry) => entry.addable).map((entry) => entry.kind)).toEqual(tablePreviewFixture.kinds);
    const detail = { table_kinds: kinds };
    expect(noteKinds(detail)).toEqual(["subjects", "characteristica", "interventions", "outputs", "timecourses", "scatters"]);
    expect(addableKinds(detail)).toEqual([
      { value: "outputs", label: "Outputs" },
      { value: "timecourses", label: "Timecourses" },
      { value: "scatters", label: "Scatters" },
      { value: "raw", label: "Raw table" },
    ]);
    expect(kindLabel(detail, "characteristica")).toBe("Characteristica");
  });

  it("compares the rows that both sides changed", () => {
    const view = conflictView(conflict("subjects"), SUBJECTS_COLUMNS);
    expect(view.changed).toEqual(["count"]);
    expect([...view.labels.values()]).toEqual(["Last sync", "Workbook row 2", "Tables line 1"]);
    expect(view.note).toBeNull();
  });

  it("lists a table whose sheet was removed from its header", () => {
    const view = conflictView(conflict("outputs"), null);
    expect(view.note).toBe("The sheet has no rows in the workbook, but the table changed since the last sync.");
    expect(view.table.kind).toBe("table");
    expect(view.table.kind === "table" && view.table.header.slice(0, 3)).toEqual(["study", "source", "subjects"]);
  });

  it("keeps the first line of a raw table, which has no header", () => {
    const view = conflictView(conflict("raw"), null);
    expect(view.table.kind).toBe("raw");
    expect(view.table.rows[0]?.cells[0]).toBe("Parameter");
    expect(view.note).toBe("The sheet has no rows in the workbook, but the table changed since the last sync.");
  });
});

describe("table preview contract", () => {
  it("offers every kind of a new table that the library adds", () => {
    const detail = { table_kinds: contract<TableKindEntry[]>(tablesFixture.table_kinds) };
    expect(addableKinds(detail).map((kind) => kind.value)).toEqual(tablePreviewFixture.kinds);
  });

  it("accepts every preview answer", () => {
    for (const { response } of tablePreviewFixture.previews) expect(isTablePreview(contract<TablePreview>(response))).toBe(true);
  });
});

describe("targets contract", () => {
  const items = targetsFixture.items.map((entry) => reviewItem(contract<Partial<ReviewItem>>(entry)));
  const targets = contract<Record<string, TargetMatch>>(targetsFixture.targets);
  const about = (file: string) => items.find((item) => item.target?.file === file)!;

  it("colors the rows of open items only", () => {
    expect([...targetLines("interventions.tsv", items, targets)]).toEqual(targets[about("interventions.tsv").id]?.lines);
    // The item about subjects.tsv is resolved and the one about timecourses_Fig1.tsv dismissed.
    expect(targetLines("subjects.tsv", items, targets).size).toBe(0);
    expect(targetLines("timecourses_Fig1.tsv", items, targets).size).toBe(0);
    expect(itemsWithoutRows("outputs_Tab2.tsv", items, targets)).toEqual({ whole: 0, unmatched: 0 });
  });

  it("names the digitized series of a figure target", () => {
    expect(targetMatch(targets, about("timecourses_Fig1.tsv")).series).toEqual({
      source: "Fig1",
      series: "caf_plasma_100mg",
    });
  });

  it("counts the rows of a draft target as the server matched them", () => {
    const [point, , , none, raw] = targetsFixture.previews.map((entry) => contract<TargetMatch>(entry.response));
    // The count and the total come from one version of the table.
    expect(matchText(point?.lines?.length ?? -1, point?.total ?? -1)).toBe("Matches 1 of 18 rows.");
    expect(none?.lines).toEqual([]);
    expect(raw?.lines).toBeNull();
  });

  it("accepts every preview answer", () => {
    for (const { response } of targetsFixture.previews) expect(isTargetMatch(response)).toBe(true);
  });
});

describe("sources contract", () => {
  const sources = contract<SourceSummary[]>(sourcesFixture.sources);
  const tables = contract<TableEntry[]>(tablesFixture.tables);

  it("has the fields of a source summary", () => {
    const fields: (keyof SourceSummary)[] = [
      "source",
      "kind",
      "image",
      "image_url",
      "raw",
      "raw_kind",
      "tables",
      "missing_image",
      "missing_raw",
    ];
    for (const summary of sources) expect(Object.keys(summary).sort()).toEqual([...fields].sort());
  });

  it("names the URL of the image of a source, the one of its source view, and none without an image", () => {
    expect(sources.map((summary) => [summary.source, summary.image_url])).toEqual([
      ["Fig1", "/local/studies/caffeine/Demo2020/files/Demo2020_Fig1.png"],
      ["Tab2", "/local/studies/caffeine/Demo2020/files/Demo2020_Tab2.png"],
      ["Text", null],
    ]);
    expect(sources[0]!.image_url).toBe(contract<SourceView>(sourceFixture).image_url);
    for (const summary of sources) expect(summary.image_url === null).toBe(summary.image === null);
  });

  it("opens each source on its own table, a text on its first shared one, and a shared table beside the paper", () => {
    const papers = contract<PaperFile[]>(sourcesFixture.papers);
    const study = { sources, tables, papers, problems: [], review: studyDetail().review };
    expect(defaultFile(study)).toBe("subjects.tsv");
    expect(sourceOfFile(study, "subjects.tsv")).toBe("paper");
    expect(sourceOfFile(study, "Demo2020_Tab2.tsv")).toBe("Tab2");
    expect(sourceOfFile({ ...study, papers: [] }, "subjects.tsv")).toBe("Fig1");
    expect(sources.map((summary) => fileForSource(study, summary, null))).toEqual([
      "timecourses_Fig1.tsv",
      "outputs_Tab2.tsv",
      "subjects.tsv",
    ]);
  });
});

describe("source view contract", () => {
  const view = contract<SourceView>(sourceFixture);

  it("accepts the answer", () => {
    expect(isSourceView(sourceFixture)).toBe(true);
  });

  it("draws the digitized error bar ends in the color of their series", () => {
    const { traces } = overlayTraces(view);
    const trace = (meta: string) => traces.find((entry) => entry.meta === meta);
    for (const series of ["caf_plasma_100mg", "caf_plasma_200mg"]) {
      expect(trace(`raw ${series}`)).toBeDefined();
      expect(trace(`mapped ${series}`)).toBeDefined();
      expect(trace(`raw-bar ${series}`)?.marker?.color).toBe(trace(`raw ${series}`)?.marker?.color);
    }
  });

  it("lists each series once in the legend", () => {
    expect(legendEntries(view, "overlay", false).map((entry) => entry.series)).toEqual(["caf_plasma_100mg", "caf_plasma_200mg"]);
  });

  it("draws the error bar of every mapped row of Fig1 from its low to its high end, mirrored around its cross", () => {
    const rows = view.overlay.filter((point) => point.role === "mapped" && point.series === "caf_plasma_100mg");
    const bars = overlayTraces(view).traces.find((entry) => entry.meta === "error caf_plasma_100mg");
    expect(bars?.y).toEqual(rows.flatMap((point) => [point.error_low_px?.[1], point.error_high_px?.[1], null]));
    // The digitized error bar ends of Fig1 are of type sd: the bar reaches as far below the cross as above it.
    for (const point of rows) expect(point.error_low_px![1] - point.py).toBeCloseTo(point.py - point.error_high_px![1], 2);
    for (const point of view.points) expect(point.error_high! - point.y).toBeCloseTo(point.y - point.error_low!, 6);
  });
});

describe("messages contract", () => {
  const ITEM = "01M3A00000000000000000000Z";
  const QUESTION = "Is the 4 h point read from the figure?";
  const PART_C_ITEM = "01M2FC4AG038NKRKAYDXR834N3";

  it("shows each kind of suggestion", () => {
    const [term, name, hint] = contract<Suggestion[]>(messagesFixture.suggestions);
    expect(suggestionView(term!)).toEqual({ lead: "Did you mean:", candidates: expect.any(Array), note: term!.message });
    expect(suggestionView(term!).candidates).toContain("caffeine");
    expect(suggestionView(name!)).toEqual({ lead: "Did you mean:", candidates: ["all"], note: null });
    expect(suggestionView(hint!)).toEqual({ lead: hint!.message, candidates: ["mg/l", "g/l"], note: null });
  });

  it("links the review item of a change in the app, also in a job saved by part C", () => {
    const items = messagesFixture.items.map((entry) => reviewItem(contract<Partial<ReviewItem>>(entry)));
    const jobs = contract<Job[]>(messagesFixture.jobs);
    const added = jobs.find((job) => job.item === ITEM)!;
    expect(messageParts(added, items)).toEqual([{ text: "Added the " }, { text: `question “${QUESTION}”`, item: ITEM }]);
    // pkdb curate gave the job saved without its item the item of its message when it started.
    const saved = jobs.find((job) => job.message.endsWith(PART_C_ITEM))!;
    expect(saved.item).toBe(PART_C_ITEM);
    expect(messageParts(saved, items)[1]?.item).toBe(PART_C_ITEM);
    expect(jobText(jobs.find((job) => job.status === "canceled")!)).toBe("Canceled before it started");
  });

  it("shows the message of a field without the field", () => {
    const issues = contract<ValidationIssue[]>(messagesFixture.metadata_issues);
    expect(issues.map((issue) => issue.field)).toEqual(["reference", "creator"]);
    for (const issue of issues) {
      const text = issueMessage(issue);
      expect(text).not.toBe("");
      expect(text.startsWith(`${issue.field}:`)).toBe(false);
      expect(text.startsWith("Value error")).toBe(false);
    }
  });
});

describe("acknowledgements contract", () => {
  const warnings = contract<Problem[]>(acknowledgementsFixture.warnings);
  const entries = contract<AcknowledgedWarning[]>(acknowledgementsFixture.acknowledged);

  it("acknowledges each dataset of a WebPlotDigitizer project by its key", () => {
    expect(warnings.map(acknowledgement)).toEqual(acknowledgementsFixture.payloads);
    expect(new Set(warnings.map(locationKey)).size).toBe(warnings.length);
  });

  it("says which acknowledgements cover a whole file", () => {
    const legacy = entries.find((entry) => entry.scope === "file")!;
    expect(scopeText(legacy)).toBe("Covers every digitized_mismatch warning in timecourses_Fig1.tsv, also later ones.");
    expect(targetText(legacy.target)).toBe("timecourses_Fig1.tsv");
    const exact = entries.find((entry) => entry.scope === "key")!;
    expect(scopeText(exact)).toBeNull();
    expect(targetText(exact.target)).toBe("Demo2020_Fig1.wpd.json · legend");
  });

  it("says plainly why an acknowledgement was refused", () => {
    const { ambiguous, missing, inexact } = acknowledgementsFixture.refusals;
    const text = (refusal: { error: string; code: string }) =>
      acknowledgeFailure(new ApiError(422, { ...refusal, issues: [] })).text;
    expect(text(ambiguous)).toBe(AMBIGUOUS_WARNING);
    expect(text(missing)).toBe(NO_SUCH_WARNING);
    expect(text(inexact)).toBe(NO_EXACT_TARGET);
  });
});

describe("errors contract", () => {
  it("reads the error body of a failed Open tables", () => {
    const error = new ApiError(500, errorsFixture.open_failed);
    expect(error.message).toBe("Could not open the tables of caffeine/Demo2020.");
    expect([error.code, error.detail, error.action, error.requestId, error.traceback]).toEqual([
      "open_failed",
      "CalledProcessError: false exited with status 1",
      "Open tables (POST /local/studies/tables)",
      "3f9c2a71",
      null,
    ]);
    expect(error.activityId).toBe(errorsFixture.activity.id);
  });

  it("shows the failure in the activity with its detail", () => {
    const job = contract<Job>(errorsFixture.activity);
    expect(jobText(job)).toBe("Could not open the tables of caffeine/Demo2020.");
    expect(job.error && detailsOfBody(job.error)).toMatchObject({
      status: null,
      code: "open_failed",
      detail: "CalledProcessError: false exited with status 1",
    });
  });
});

describe("papers contract", () => {
  const papers = contract<PaperFile[]>(sourcesFixture.papers);

  it("lists the PDF of Demo2020 with the URL of the file route, its size and the version of its content", () => {
    expect(papers).toHaveLength(1);
    expect(papers[0]).toMatchObject({ file: "Demo2020.pdf", url: "/local/studies/caffeine/Demo2020/files/Demo2020.pdf" });
    expect(papers[0]!.bytes).toBeGreaterThan(0);
    expect(papers[0]!.version).toMatch(/^[0-9a-f]{16}$/);
    expect(Object.keys(papers[0]!).sort()).toEqual(["bytes", "file", "url", "version"]);
  });
});

describe("rows contract", () => {
  const rows = contract<StudyRow[]>(rowsFixture);

  it("has the counts of the problems of each study and no problem list, which the study page has", () => {
    expect(rows.every((row) => !("problems" in row))).toBe(true);
    expect(rows.every((row) => !("mode" in row))).toBe(true);
    const demo = rows.find((row) => row.id === "caffeine/Demo2020")!;
    expect(problemLabels(demo)).toEqual([{ label: "2 warnings", tone: "warning" }]);
  });

  it("is what the overview filters", () => {
    const { shown, counts } = filterStudies(rows, { search: "demo", substance: "", curator: "", chip: "all" });
    expect(shown.map((row) => row.id)).toEqual(["caffeine/Demo2020"]);
    expect(counts.all).toBe(1);
    // Each row names its substance folders, its own first.
    expect(rows.every((row) => row.substances[0] === row.substance)).toBe(true);
    const caffeine = filterStudies(rows, { search: "", substance: "caffeine", curator: "", chip: "all" });
    expect(caffeine.shown).toHaveLength(rows.length);
  });
});

describe("open tables contract", () => {
  it("accepts the answers of Open tables at a cell, and the notice of an open workbook", () => {
    const opened = contract<TablesResult>(openTablesFixture.opened);
    const open = contract<TablesResult>(openTablesFixture.already_open);
    expect(isTablesResult(opened)).toBe(true);
    expect(isTablesResult(open)).toBe(true);
    expect(opened.notice).toBeNull();
    expect(open.notice).toBe("The workbook is already open. Go to sheet timecourses_Fig1, cell O6.");
  });

  it("opens a problem of the validation at the place that the local server takes", () => {
    const mismatch = contract<Problem[]>(problemsFixture.validated).find((issue) => issue.code === "digitized_mismatch");
    expect(openPlace(mismatch!)).toEqual({ file: openTablesFixture.request.file, cell: openTablesFixture.request.cell });
  });
});

describe("table content contract", () => {
  const tables = contract<Record<string, TableResponse>>(tableContentFixture);
  /** The class of each column of `file` by its name. */
  const classes = (file: string) => {
    const table = tables[file]!;
    return Object.fromEntries(
      Array.from({ length: columnCount(table) }, (_, index) => [columnName(table, index), columnClass(table, index)]),
    );
  };

  it("classes the columns of a table of the data by what they name", () => {
    expect(classes("outputs_Tab2.tsv")).toMatchObject({
      study: "meta",
      source: "meta",
      subjects: "subjects",
      interventions: "interventions",
      measurement: "data",
      mean: "data",
      comment: "data",
    });
  });

  it("classes every column of the tables of the subjects and the interventions but study and source as the table", () => {
    for (const [file, info] of [
      ["subjects.tsv", "subjects"],
      ["characteristica.tsv", "subjects"],
      ["interventions.tsv", "interventions"],
    ] as const) {
      const { study, source, ...others } = classes(file);
      expect([study, source]).toEqual(["meta", "meta"]);
      expect(new Set(Object.values(others))).toEqual(new Set([info]));
    }
  });

  it("classes no column of a raw table", () => {
    expect(tables["Demo2020_Tab2.tsv"]!.kind).toBe("raw");
    expect(Object.values(classes("Demo2020_Tab2.tsv")).every((value) => value === null)).toBe(true);
  });
});

describe("name lines contract", () => {
  const names = contract<StudyDetail["name_lines"]>(nameLinesFixture.name_lines);
  const table = contract<TableResponse>(nameLinesFixture.table);

  it("links every subject and intervention that the cells of a table name to its row", () => {
    const header = table.kind === "table" ? table.header : [];
    const linked = header.flatMap((column, index) => {
      const kind = namedKind(column);
      return kind ? table.rows.flatMap((row) => cellParts(row.cells[index] ?? "", names[kind])) : [];
    });
    expect(linked.every((part) => part.link !== null)).toBe(true);
    expect(new Set(linked.map((part) => `${part.text} ${part.link!.file}:${part.link!.line}`))).toEqual(
      new Set(["all subjects.tsv:1", "D100 interventions.tsv:1", "D200 interventions.tsv:2"]),
    );
  });

  it("names no lines beyond the upload limits", () => {
    for (const detail of BEYOND_LIMITS)
      expect(detail.name_lines).toEqual({
        subjects: { file: "subjects.tsv", lines: {} },
        interventions: { file: "interventions.tsv", lines: {} },
      });
  });
});

describe("outputs source contract", () => {
  const view = contract<SourceView>(outputsSourceFixture);
  const PLASMA = "all · D150 · concentration · caffeine · plasma";
  const URINE = "all · D150 · concentration · caffeine · urine";

  it("accepts the answer", () => {
    expect(isSourceView(outputsSourceFixture)).toBe(true);
  });

  it("plots each series of the outputs with a time as lines and markers by time, beside the image", () => {
    const { traces, layout } = plotTraces(view);
    expect(traces.map((entry) => entry.meta)).toEqual([`plot ${PLASMA}`, `plot ${URINE}`]);
    const plasma = traces[0]!;
    expect(plasma).toEqual(expect.objectContaining({ mode: "lines+markers", x: [0.5, 1, 2, 4], y: [2.1, 3, 2.4, 1.2] }));
    expect(plasma.customdata?.map(([file, line]) => [file, line])).toEqual([
      ["outputs_Fig2.tsv", 2],
      ["outputs_Fig2.tsv", 3],
      ["outputs_Fig2.tsv", 4],
      ["outputs_Fig2.tsv", 5],
    ]);
    expect(layout.xaxis.title).toEqual({ text: "time (hr)", font: { size: 11 } });
    expect(layout.yaxis.title).toEqual({ text: "concentration (mg/l)", font: { size: 11 } });
    expect(legendEntries(view, "plot", false).map((entry) => entry.series)).toEqual([PLASMA, URINE]);
  });
});
