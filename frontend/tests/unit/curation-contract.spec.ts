/**
 * The front-end side of the contract fixtures: real answers of the local API, written by
 * python/tests/test_curation_contract.py. Regenerate them there with PKDB_UPDATE_CONTRACT=1.
 */
import { describe, expect, it } from "vitest";
import type { ConflictData, ReviewItem, TableEntry, TablePreview, TargetMatch } from "../../src/curation-app/api/types";
import { isTablePreview, isTargetMatch } from "../../src/curation-app/api/types";
import { itemsWithoutRows, targetLines, targetMatch } from "../../src/curation-app/grid";
import { matchText } from "../../src/curation-app/review";
import { isRawTable, railCounts, tableFiles } from "../../src/curation-app/study";
import { NEW_TABLE_KINDS, TABLE_KINDS } from "../../src/curation-app/tableKinds";
import { conflictView } from "../../src/curation-app/tables";
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
