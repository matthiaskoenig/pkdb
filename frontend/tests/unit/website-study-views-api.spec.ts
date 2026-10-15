import { beforeEach, describe, expect, it, vi } from "vitest";
import { CanceledError } from "axios";
import {
  readError,
  sourceView,
  studyRows,
  studyView,
  studyViewsApi,
  tableView,
  viewPath,
} from "../../src/features/studies/api";
import { ApiError, isAbort, SessionMissing } from "../../src/study-views/errors";
import { filterStudies } from "../../src/study-views/overview";
import { isSourceView, isStudyDetail, isTableResponse } from "../../src/study-views/types";
import { httpError } from "../components/website-api";
import rowsCurator from "../fixtures/website-views/study-rows-curator.json";
import rowsPublic from "../fixtures/website-views/study-rows-public.json";
import sourceCurator from "../fixtures/website-views/source-curator.json";
import sourcePublic from "../fixtures/website-views/source-public.json";
import studyCurator from "../fixtures/website-views/study-curator.json";
import studyPublic from "../fixtures/website-views/study-public.json";
import tableCurator from "../fixtures/website-views/table-curator.json";

const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({ api: { get: mocks.get }, apiBase: "https://pk-db.example" }));

const BASE = "https://pk-db.example";
const SID = "drug/Format2Fixture";

beforeEach(() => mocks.get.mockReset());

describe("the rows of the Studies page", () => {
  it("are study rows of the shared list with the curation of a curator and no local state", () => {
    const { rows, profiles } = studyRows(rowsCurator, "GET /api/v2/study-rows");
    expect(rows.map((row) => row.id)).toEqual([SID]);
    const [row] = rows;
    expect(row).toMatchObject({ id: SID, path: SID, duplicate: false, status: "valid", curator: true, substance: "drug" });
    expect("sync" in row!).toBe(false);
    expect(row!.issue?.number).toBe(2158);
    expect(row!.summary.review_status).toBe("in_review");
    expect(filterStudies(rows, { search: "", substance: "", curator: "", chip: "all" }, { jobs: false }).counts.in_review).toBe(1);
    expect(profiles.map((profile) => profile.username)).toContain("curator");
    expect(profiles.every((profile) => profile.avatar_url === null || profile.avatar_url.startsWith(BASE))).toBe(true);
  });

  it("are the public rows without the curation for a reader who may not write", () => {
    const [row] = studyRows(rowsPublic, "GET /api/v2/study-rows").rows;
    expect(row).toMatchObject({ curator: false, issue: null });
    expect("review_status" in row!.summary).toBe(false);
  });

  it("refuse an answer that is not a list of rows", () => {
    expect(() => studyRows({ rows: [{ id: SID }], profiles: {} }, "GET /api/v2/study-rows")).toThrow(
      "PK-DB sent an unexpected answer to GET /api/v2/study-rows.",
    );
  });
});

describe("the study page", () => {
  it("is the study detail of the shared views, with the files of a curator on the API", () => {
    const { audience, detail } = studyView(studyCurator, `GET ${viewPath(SID)}`);
    expect(audience).toBe("curator");
    expect(isStudyDetail(detail)).toBe(true);
    expect(detail).toMatchObject({ id: SID, path: SID, status: "valid", jobs: [], conflicts: [], message: null, last_upload: null });
    expect(detail.metadata).toMatchObject({ revision: null, issues: [] });
    expect(detail.metadata.value?.release?.pkdb_id).toBe("PKDB09901");
    expect(detail.review.value?.status).toBe("in_review");
    expect(detail.papers.map((paper) => paper.url)).toEqual([`${BASE}/api/v2/studies/drug/Format2Fixture/view/files/Format2Fixture.pdf`]);
    expect(detail.sources.find((source) => source.source === "Tab1")?.image_url).toBe(
      `${BASE}/api/v2/studies/drug/Format2Fixture/view/files/Format2Fixture_Tab1.png`,
    );
    expect(detail.tables.some((table) => table.kind === "raw")).toBe(true);
    expect(detail.issue?.number).toBe(2158);
    expect(detail.people.curators.map((curator) => curator.user)).toEqual(["curator"]);
  });

  it("is the public view without review, files and issue for a reader who may not write", () => {
    const { audience, detail } = studyView(studyPublic, `GET ${viewPath(SID)}`);
    expect(audience).toBe("public");
    expect(detail.review.value).toBeNull();
    expect(detail.papers).toEqual([]);
    expect(detail.issue).toBeNull();
    expect(detail.problems).toEqual([]);
    expect(detail.tables.some((table) => table.kind === "raw")).toBe(false);
    expect(detail.sources.every((source) => source.image_url === null)).toBe(true);
  });

  it("refuses an answer without an audience", () => {
    expect(() => studyView({ ...studyCurator, audience: "admin" }, "GET view")).toThrow("unexpected answer");
  });

  it("reads tables and sources as the shared views know them, the image of a source on the API", () => {
    expect(isTableResponse(tableView(tableCurator, "GET table"))).toBe(true);
    const curator = sourceView(sourceCurator, "GET source");
    expect(isSourceView(curator)).toBe(true);
    expect(curator.image_url).toBe(`${BASE}/api/v2/studies/drug/Format2Fixture/view/files/Format2Fixture_Fig1.png`);
    const visitor = sourceView(sourcePublic, "GET source");
    expect(visitor).toMatchObject({ image: null, image_url: null, raw_grid: null, layout: "side_by_side" });
  });
});

describe("the requests", () => {
  it("name a study by its substance and name, each part encoded", () => {
    expect(viewPath("drug/Name (2)", "tables", "a b.tsv")).toBe("/api/v2/studies/drug/Name%20(2)/view/tables/a%20b.tsv");
  });

  it("read a study with the signal of the page", async () => {
    mocks.get.mockResolvedValue({ data: studyCurator });
    const signal = new AbortController().signal;
    await studyViewsApi.study(SID, signal);
    expect(mocks.get).toHaveBeenCalledWith("/api/v2/studies/drug/Format2Fixture/view", { signal });
  });

  it("reject a study without a view with the 404 of an ApiError, and a cancelled read as an AbortError", async () => {
    mocks.get.mockRejectedValueOnce(httpError(404));
    const missing = await studyViewsApi.study(SID).catch((error: unknown) => error);
    expect(missing).toBeInstanceOf(ApiError);
    expect(missing).toMatchObject({ status: 404, code: "not_found", action: "GET /api/v2/studies/drug/Format2Fixture/view" });
    mocks.get.mockRejectedValueOnce(new CanceledError());
    expect(isAbort(await studyViewsApi.rows().catch((error: unknown) => error))).toBe(true);
    expect(readError(httpError(500, { detail: "Database unavailable" }), "GET x")).toMatchObject({
      status: 500,
      message: "Database unavailable",
    });
  });

  it("check one byte of a file and tell an ended session", async () => {
    mocks.get.mockResolvedValueOnce({ data: new ArrayBuffer(1) });
    await studyViewsApi.checkFile(`${BASE}/api/v2/studies/drug/Format2Fixture/view/files/Format2Fixture.pdf`);
    expect(mocks.get.mock.calls[0]?.[1]).toMatchObject({ headers: { Range: "bytes=0-0" } });
    mocks.get.mockRejectedValueOnce(httpError(401));
    await expect(studyViewsApi.checkFile("/x.pdf")).rejects.toBeInstanceOf(SessionMissing);
  });
});
