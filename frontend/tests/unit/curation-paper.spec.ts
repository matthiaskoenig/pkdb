import { describe, expect, it, vi } from "vitest";
import { ApiError, NO_SESSION, SessionMissing } from "../../src/study-views/errors";
import {
  findText,
  formatBytes,
  mainPaper,
  paperAnswer,
  paperFailure,
  PaperImportFailed,
  paperLine,
  paperName,
  paperRoute,
  shownPaper,
  zoomText,
} from "../../src/curation-app/paper";
import { paperFile, studyDetail } from "./curation-fixtures";

const URL_A = "/local/studies/caffeine/Example/files/Example.pdf";

/** The error of PDF.js for an error status of the local server, which carries no answer. */
function responseError(status: number): Error {
  return Object.assign(new Error(`Unexpected server response (${status}) while retrieving PDF.`), {
    name: "ResponseException",
    status,
    missing: status === 404,
  });
}

/** The answer of the local server to the file route, as `checkFile` throws it. */
function answer(status: number, code: string, detail: string | null): ApiError {
  return new ApiError(status, {
    error: "Could not read Example.pdf of caffeine/Example.",
    code,
    detail,
    action: `Read a file (GET ${URL_A})`,
    request_id: "0a1b2c3d",
    time: "2026-10-12T10:00:00+02:00",
  });
}

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("the paper of a study", () => {
  it("finds the PDF named after the study, with its suffix in any case, among the PDFs of the folder", () => {
    const supplement = paperFile("Example_Supp.pdf");
    expect(mainPaper(studyDetail({ papers: [paperFile("Example.PDF"), supplement] }))?.file).toBe("Example.PDF");
    expect(mainPaper(studyDetail({ papers: [supplement] }))).toBeNull();
    expect(mainPaper(studyDetail())).toBeNull();
  });

  it("names the PDF of the study, and says in the navigator which PDF the paper shows first", () => {
    expect(paperName(studyDetail())).toBe("Example.pdf");
    expect(paperLine(studyDetail())).toBe("No Example.pdf");
    expect(paperLine(studyDetail({ papers: [paperFile("Example.pdf")] }))).toBe("Example.pdf");
    expect(paperLine(studyDetail({ papers: [paperFile("Example.pdf"), paperFile("a.pdf"), paperFile("b.pdf")] }))).toBe(
      "Example.pdf",
    );
  });

  it("finds the PDF that the paper shows: the chosen one while the folder has it, else the first", () => {
    const papers = [paperFile("Example.pdf"), paperFile("a.pdf")];
    expect(shownPaper(papers, "a.pdf")?.file).toBe("a.pdf");
    expect(shownPaper(papers, null)?.file).toBe("Example.pdf");
    expect(shownPaper(papers, "gone.pdf")?.file).toBe("Example.pdf");
    expect(shownPaper([], "a.pdf")).toBeNull();
  });

  it("routes a PDF to a tab of its own", () => {
    expect(paperRoute("caffeine/Example", "Example Supp.pdf")).toEqual({
      name: "Paper",
      params: { substance: "caffeine", name: "Example", file: "Example Supp.pdf" },
    });
  });

  it.each([
    [840, "840 B"],
    [19_507, "20 kB"],
    [999_499, "999 kB"],
    [999_600, "1.0 MB"],
    [4_590_032, "4.6 MB"],
    [88_026_279, "88 MB"],
  ])("writes %d bytes as %s", (bytes, text) => {
    expect(formatBytes(bytes)).toBe(text);
  });

  it("counts the matches of a find, and shows the scale of a zoom step", () => {
    expect(findText(null, "the")).toBe("");
    expect(findText({ status: "found", current: 1, total: 3 }, "")).toBe("");
    expect(findText({ status: "found", current: 1, total: 3 }, "   ")).toBe("");
    expect(findText({ status: "pending", current: 0, total: 0 }, "the")).toBe("Finding…");
    expect(findText({ status: "found", current: 3, total: 12 }, "the")).toBe("3 of 12");
    expect(findText({ status: "found", current: 0, total: 12 }, "the")).toBe("12 matches");
    expect(findText({ status: "missing", current: 0, total: 0 }, "the")).toBe("No matches");
    expect(zoomText(1.25)).toBe("125 %");
  });

  it.each([
    [
      Object.assign(new Error("Invalid PDF structure."), { name: "InvalidPDFException" }),
      "Example.pdf is damaged or not a PDF.",
      "pdf_damaged",
      null,
    ],
    [
      Object.assign(new Error("No password given"), { name: "PasswordException", code: 1 }),
      "Example.pdf is protected by a password. Open it in the PDF program.",
      "pdf_password",
      null,
    ],
    // Without the answer of the local server, a 404 does not say that the PDF is gone: the
    // server answers it for a file that it cannot read too.
    [responseError(404), "Could not read Example.pdf: the local server answered 404.", "pdf_unreadable", 404],
    [responseError(500), "Could not read Example.pdf: the local server answered 500.", "pdf_unreadable", 500],
    [
      new PaperImportFailed(new TypeError("Failed to fetch dynamically imported module")),
      "The PDF viewer could not be loaded.",
      "viewer_unavailable",
      null,
    ],
    [new TypeError("Failed to fetch"), "Could not show Example.pdf.", "pdf_failed", null],
  ])("explains %s for the alert of a failed action", (error, text, code, status) => {
    const failure = paperFailure(error, "Example.pdf", URL_A);
    expect(failure.text).toBe(text);
    expect(failure.details).toEqual({
      status,
      code,
      detail: `${error.name}: ${error.message}`,
      action: `Show the paper (GET ${URL_A})`,
      requestId: null,
      time: null,
      traceback: null,
      activityId: null,
    });
  });

  it("explains an error status of the local server by its answer: a PDF that is gone, or one that it cannot read", () => {
    const gone = paperFailure(responseError(404), "Example.pdf", URL_A, answer(404, "not_found", null));
    expect(gone.text).toBe("Example.pdf is no longer in the study folder.");
    expect(gone.details).toEqual({
      status: 404,
      code: "not_found",
      detail: `ResponseException: ${responseError(404).message}`,
      action: `Show the paper (GET ${URL_A})`,
      requestId: "0a1b2c3d",
      time: "2026-10-12T10:00:00+02:00",
      traceback: null,
      activityId: null,
    });
    const denied = "PermissionError: [Errno 13] Permission denied: '/work/caffeine/Example/Example.pdf'";
    const unreadable = paperFailure(responseError(400), "Example.pdf", URL_A, answer(400, "file_error", denied));
    expect(unreadable.text).toBe("Could not read Example.pdf: the local server answered 400.");
    expect(unreadable.details).toMatchObject({
      status: 400,
      code: "file_error",
      detail: denied,
      requestId: "0a1b2c3d",
    });
  });

  it("explains a lost session as the app does, without the status", () => {
    const failure = paperFailure(
      responseError(401),
      "Example.pdf",
      URL_A,
      new SessionMissing("Open the launch URL printed in your terminal"),
    );
    expect(failure).toEqual({ text: NO_SESSION, issues: [], more: 0, link: null, details: null });
    expect(NO_SESSION).toBe("This page has no session. Open the link that pkdb curate printed.");
  });

  it("has the lost session as the answer of the local server to a 401", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ error: "Open the launch URL printed in your terminal" }, 401));
    await expect(paperAnswer(responseError(401), URL_A)).resolves.toBeInstanceOf(SessionMissing);
  });

  it("asks the local server again for its answer after an error status, for one byte of the PDF", async () => {
    const fetch = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(json({ error: "Could not read Example.pdf.", code: "file_error", detail: "PermissionError" }, 400));
    const answered = await paperAnswer(responseError(400), URL_A);
    expect(answered).toBeInstanceOf(ApiError);
    expect(answered instanceof ApiError && [answered.status, answered.code, answered.detail]).toEqual([
      400,
      "file_error",
      "PermissionError",
    ]);
    expect(fetch).toHaveBeenCalledTimes(1);
    const [input, init] = fetch.mock.calls[0]!;
    expect(String(input)).toBe(URL_A);
    expect(new Headers(init?.headers).get("Range")).toBe("bytes=0-0");
    expect(init?.credentials).toBe("same-origin");
  });

  it("has no answer of the local server for another failure, nor when it serves the PDF or cannot be reached", async () => {
    const fetch = vi.spyOn(globalThis, "fetch");
    await expect(paperAnswer(new TypeError("Failed to fetch"), URL_A)).resolves.toBeNull();
    await expect(
      paperAnswer(Object.assign(new Error("Invalid PDF structure."), { name: "InvalidPDFException" }), URL_A),
    ).resolves.toBeNull();
    expect(fetch).not.toHaveBeenCalled();
    fetch.mockResolvedValueOnce(new Response("%", { status: 206, headers: { "Content-Range": "bytes 0-0/19507" } }));
    await expect(paperAnswer(responseError(404), URL_A)).resolves.toBeNull();
    fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(paperAnswer(responseError(404), URL_A)).resolves.toBeNull();
  });
});
