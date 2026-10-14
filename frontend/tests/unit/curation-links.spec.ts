import { describe, expect, it } from "vitest";
import type { NameLines } from "../../src/curation-app/api/types";
import { cellParts, NAME_KINDS, namedKind } from "../../src/curation-app/links";

const DOSES: NameLines = { file: "interventions.tsv", lines: { D1: 1, D2: 2, "D 3": 3 } };
const link = (text: string, line: number) => ({ text, link: { file: "interventions.tsv", line } });
const plain = (text: string) => ({ text, link: null });

describe("the columns of names", () => {
  it("knows the columns that name subjects or interventions by their names", () => {
    expect(NAME_KINDS).toEqual(["subjects", "interventions"]);
    expect(["subjects", "parent", "x_subjects", "interventions", "x_interventions", "y_interventions"].map(namedKind)).toEqual([
      "subjects",
      "subjects",
      "subjects",
      "interventions",
      "interventions",
      "interventions",
    ]);
  });

  it("knows no names in the other columns, such as name of subjects.tsv", () => {
    expect(["name", "study", "source", "label", "subjects_count", "measurement", "A"].map(namedKind)).toEqual([
      null,
      null,
      null,
      null,
      null,
      null,
      null,
    ]);
  });
});

describe("the parts of a cell", () => {
  it("links a known name to its row", () => {
    expect(cellParts("D1", DOSES)).toEqual([link("D1", 1)]);
  });

  it("links each comma-separated name of its own, and keeps the commas and the spaces as text", () => {
    expect(cellParts("D1,D2", DOSES)).toEqual([link("D1", 1), plain(","), link("D2", 2)]);
    expect(cellParts(" D1 , D 3 ", DOSES)).toEqual([plain(" "), link("D1", 1), plain(" , "), link("D 3", 3), plain(" ")]);
    expect(cellParts(" D1 , D 3 ", DOSES).map((part) => part.text).join("")).toBe(" D1 , D 3 ");
  });

  it("leaves unknown names, empty names and an empty cell as text", () => {
    expect(cellParts("D9", DOSES)).toEqual([plain("D9")]);
    expect(cellParts("D1,D9", DOSES)).toEqual([link("D1", 1), plain(",D9")]);
    expect(cellParts("D1,,D2", DOSES)).toEqual([link("D1", 1), plain(",,"), link("D2", 2)]);
    expect(cellParts("", DOSES)).toEqual([]);
  });

  it("links only the names of the table, not the properties that every object has", () => {
    for (const name of ["constructor", "toString", "__proto__", "hasOwnProperty"])
      expect(cellParts(name, DOSES)).toEqual([plain(name)]);
    // As the study page arrives: JSON.parse makes `__proto__` a name of its own.
    const odd = JSON.parse('{"file": "subjects.tsv", "lines": {"__proto__": 4, "constructor": 5}}') as NameLines;
    expect(cellParts("__proto__,constructor", odd)).toEqual([
      { text: "__proto__", link: { file: "subjects.tsv", line: 4 } },
      plain(","),
      { text: "constructor", link: { file: "subjects.tsv", line: 5 } },
    ]);
  });
});
