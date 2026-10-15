import { describe, expect, it } from "vitest";
import { statusChips } from "../../src/study-views/overview";
import { shownColumns, sortableKeys, STUDY_COLUMNS } from "../../src/study-views/studyTable";

const PUBLIC = { curation: false, jobs: false };
const CURATOR = { curation: true, jobs: false };
const EVERYTHING = { curation: true, jobs: true };

describe("the columns of the study list by what the reader may see", () => {
  it("show Study, Release and Curators to everyone, the curation with curation and the jobs with jobs", () => {
    expect(shownColumns(PUBLIC).map((column) => column.label)).toEqual(["Study", "Release", "Curators"]);
    expect(shownColumns(CURATOR).map((column) => column.label)).toEqual([
      "Study",
      "Release",
      "Issue",
      "Curators",
      "Review",
      "Open items",
      "Problems",
    ]);
    expect(shownColumns(EVERYTHING)).toEqual(STUDY_COLUMNS);
  });

  it("sort only by the shown columns that sort, so an address cannot sort by a hidden one", () => {
    expect(sortableKeys(PUBLIC)).toEqual(["study", "release"]);
    expect(sortableKeys(CURATOR)).toEqual(["study", "release", "issue", "review", "open_items", "problems"]);
    expect(sortableKeys(EVERYTHING)).toEqual([
      "study",
      "release",
      "issue",
      "review",
      "open_items",
      "problems",
      "sync",
      "upload",
    ]);
  });

  it("offer the status chips only with the curation", () => {
    expect(statusChips(PUBLIC)).toEqual(["all"]);
    expect(statusChips(CURATOR)).toEqual(["all", "attention", "draft", "in_review", "approved"]);
  });
});
