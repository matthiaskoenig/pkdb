/**
 * The front-end side of the contract fixtures: real answers of the local API, written by
 * python/tests/test_curation_contract.py. Regenerate them there with PKDB_UPDATE_CONTRACT=1.
 */
import { describe, expect, it } from "vitest";
import type { ConflictData, TableEntry } from "../../src/curation-app/api/types";
import { isRawTable, railCounts, tableFiles } from "../../src/curation-app/study";
import { TABLE_KINDS } from "../../src/curation-app/tableKinds";
import { conflictView } from "../../src/curation-app/tables";
import tablesFixture from "../fixtures/curation-contract/tables.json";
import { studyDetail, SUBJECTS_COLUMNS } from "./curation-fixtures";

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

  it("has the notes of every table kind of the library", () => {
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
