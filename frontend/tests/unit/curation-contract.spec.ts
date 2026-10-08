/**
 * The front-end side of the contract fixtures: real answers of the local API, written by
 * python/tests/test_curation_contract.py. Regenerate them there with PKDB_UPDATE_CONTRACT=1.
 */
import { describe, expect, it } from "vitest";
import type {
  AcknowledgedWarning,
  ConflictData,
  Job,
  ReviewItem,
  SourceView,
  Suggestion,
  TableEntry,
  TablePreview,
  TargetMatch,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { isSourceView, isTablePreview, isTargetMatch } from "../../src/curation-app/api/types";
import { jobText, messageParts } from "../../src/curation-app/activity";
import { itemsWithoutRows, targetLines, targetMatch } from "../../src/curation-app/grid";
import { issueMessage } from "../../src/curation-app/metadata";
import { legendEntries, overlayTraces } from "../../src/curation-app/overlay";
import { ApiError } from "../../src/curation-app/api/client";
import {
  acknowledgeFailure,
  acknowledgement,
  AMBIGUOUS_WARNING,
  locationKey,
  NO_EXACT_TARGET,
  NO_SUCH_WARNING,
  scopeText,
  suggestionView,
} from "../../src/curation-app/problems";
import { matchText, targetText } from "../../src/curation-app/review";
import { isRawTable, railCounts, tableFiles } from "../../src/curation-app/study";
import { NEW_TABLE_KINDS, TABLE_KINDS } from "../../src/curation-app/tableKinds";
import { conflictView } from "../../src/curation-app/tables";
import acknowledgementsFixture from "../fixtures/curation-contract/acknowledgements.json";
import messagesFixture from "../fixtures/curation-contract/messages.json";
import sourceFixture from "../fixtures/curation-contract/source-fig1.json";
import tablePreviewFixture from "../fixtures/curation-contract/table-preview.json";
import tablesFixture from "../fixtures/curation-contract/tables.json";
import targetsFixture from "../fixtures/curation-contract/targets.json";
import { reviewItem, studyDetail, SUBJECTS_COLUMNS } from "./curation-fixtures";

/** A fixture as the type of the app; the fixture is a real answer of the server. */
function contract<T>(value: unknown): T {
  return value as T;
}

describe("tables contract", () => {
  const tables = contract<TableEntry[]>(tablesFixture.tables);
  const conflicts = contract<ConflictData[]>(tablesFixture.conflicts);
  const conflict = (kind: string) => conflicts.find((entry) => entry.kind === kind)!;

  it("lists the tables of a study in the order of the workbook sheets", () => {
    expect(tableFiles({ tables })).toEqual([
      "subjects.tsv",
      "interventions.tsv",
      "characteristica.tsv",
      "outputs_Tab2.tsv",
      "timecourses_Fig1.tsv",
      "Demo2020_Tab2.tsv",
    ]);
    expect(isRawTable({ tables }, "Demo2020_Tab2.tsv")).toBe(true);
    expect(isRawTable({ tables }, "outputs_Tab2.tsv")).toBe(false);
    expect(railCounts(studyDetail({ tables })).tables).toBe(6);
  });

  it("lists every table kind of the library", () => {
    expect([...TABLE_KINDS]).toEqual(tablesFixture.table_kinds);
  });

  it("compares the rows that both sides changed", () => {
    const view = conflictView(conflict("subjects"), SUBJECTS_COLUMNS);
    expect(view.changed).toEqual(["count"]);
    expect([...view.labels.values()]).toEqual(["Last sync", "Workbook row 2", "Tables line 2"]);
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
    expect(NEW_TABLE_KINDS.map((kind) => kind.value)).toEqual(tablePreviewFixture.kinds);
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
  const warnings = contract<ValidationIssue[]>(acknowledgementsFixture.warnings);
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
