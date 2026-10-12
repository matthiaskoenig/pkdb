/**
 * The paper of a study: the PDFs of its folder, the words of the viewer and its failures, and
 * the import of PDF.js. Nothing here imports PDF.js: `paperEngine.ts` drives it and loads with
 * the first paper as a chunk of its own, as Plotly does.
 */
import { reactive } from "vue";
import type { RouteLocationRaw } from "vue-router";
import { ApiError, checkFile, NO_SESSION, SessionMissing } from "./api/client";
import type { PaperFile, StudyDetail } from "./api/types";
import type { FailureDetails } from "./failures";
import { actionFailure, studyName, type ActionFailure } from "./study";

/** How the pages fit into the viewer: its width, a whole page, or their size in print. */
export type Fit = "page-width" | "page-fit" | "1";

/** The fits of the zoom select, in its order. */
export const FITS: readonly Fit[] = ["page-width", "page-fit", "1"];

export const FIT_LABELS: Record<Fit, string> = { "page-width": "Fit width", "page-fit": "Fit page", "1": "100 %" };

/**
 * The smallest and the largest zoom of PDF.js 6.4.299, 10 % and 2500 %: its `MIN_SCALE` and
 * `MAX_SCALE` (web/ui_utils.js), which pdf_viewer.mjs does not export.
 */
export const MIN_SCALE = 0.1;
export const MAX_SCALE = 25;

/** Where a find stands: running, at a match of its matches, or without any. */
export interface FindResult {
  status: "pending" | "found" | "missing";
  /** The selected match, from 1; 0 before one is selected. */
  current: number;
  total: number;
}

/** What the viewer reports while it shows a PDF. */
export interface PaperEvents {
  /** The PDF opened with `pages` pages. */
  opened(pages: number): void;
  /** The page in view, from 1. */
  page(page: number): void;
  /** The zoom: the scale, 1 for 100 %, and its fit; null after a zoom step. */
  scale(scale: number, fit: Fit | null): void;
  found(result: FindResult): void;
}

/** Where a PDF opens: its page, and its fit, else its scale. */
export interface PaperStart {
  page: number;
  fit: Fit | null;
  scale: number;
}

/**
 * Where the viewer stands in the PDF at `url`. The viewer opens that PDF there again when it
 * changed on disk, and when it mounts again with the place that its parent kept.
 */
export interface PaperPlace extends PaperStart {
  url: string;
}

/** A PDF open in the viewer. */
export interface PaperSession {
  goTo(page: number): void;
  /** Zoom in (1) or out (-1) by one step. */
  zoom(step: 1 | -1): void;
  fit(fit: Fit): void;
  /**
   * Find `query` from the page in view; `again` goes to the next match, or the previous one with
   * `previous`. An empty query ends the find and its highlights.
   */
  find(query: string, options: { again: boolean; previous: boolean }): void;
  /**
   * Close the PDF: it leaves the container at once, before `close` returns, and the promise
   * resolves when its worker has gone.
   */
  close(): Promise<void>;
}

/**
 * Open the PDF at `url` in `container`, an absolutely positioned element with an empty
 * `div.pdfViewer` inside. Aborting `signal` stops the loading, with its worker and its requests,
 * and rejects with its reason: an aborted PDF never comes into the container. A PDF that opened
 * is closed with `close` of its session; aborting then ends the listeners of PDF.js on the
 * container.
 */
export type OpenPaper = (
  container: HTMLDivElement,
  url: string,
  events: PaperEvents,
  start: PaperStart,
  signal: AbortSignal,
) => Promise<PaperSession>;

/**
 * The import of PDF.js, shared by the viewers of the page. `failed again` is a failure after a
 * retry: Chrome keeps a failed import of a module until the page reloads. `attempt` counts the
 * retries, which every viewer follows by opening its PDF again.
 */
export const paperImport = reactive<{ state: "idle" | "loaded" | "failed" | "failed again"; attempt: number }>({
  state: "idle",
  attempt: 0,
});
let retried = false;

/** A failed import of PDF.js, with its cause. */
export class PaperImportFailed extends Error {
  constructor(cause: unknown) {
    super(cause instanceof Error ? cause.message : String(cause), { cause });
    this.name = "PaperImportFailed";
  }
}

/** Open the PDF again in every viewer, and import PDF.js again when its import failed. */
export function retryPaper(): void {
  if (paperImport.state !== "loaded") retried = true;
  paperImport.attempt += 1;
}

/** The viewer of PDF.js, which its first call imports with its stylesheet. */
export async function loadPaperEngine(): Promise<{ openPaper: OpenPaper }> {
  try {
    const engine = await import("./paperEngine");
    paperImport.state = "loaded";
    retried = false;
    return engine;
  } catch (caught) {
    paperImport.state = retried ? "failed again" : "failed";
    throw new PaperImportFailed(caught);
  }
}

/** The PDF named after the study, `<name>.pdf`, which Open PDF of the study header opens too. */
export function paperName(study: Pick<StudyDetail, "id">): string {
  return `${studyName(study)}.pdf`;
}

/**
 * The PDF named after the study among the PDFs of its folder: `<name>.pdf`, with its suffix in
 * any case, which the local server lists first; null when the folder lacks it.
 */
export function mainPaper(study: Pick<StudyDetail, "id" | "papers">): PaperFile | null {
  const stem = studyName(study);
  return study.papers.find((paper) => paper.file.startsWith(stem) && paper.file.toLowerCase() === `${stem.toLowerCase()}.pdf`) ?? null;
}

/** The line below Paper in the navigator: the PDF that the paper shows first, or the PDF that the folder lacks. */
export function paperLine(study: Pick<StudyDetail, "id" | "papers">): string {
  return study.papers[0]?.file ?? `No ${paperName(study)}`;
}

/** The route of a PDF of the study `id` in a tab of its own. */
export function paperRoute(id: string, file: string): RouteLocationRaw {
  return { name: "Paper", params: { substance: id.slice(0, id.indexOf("/")), name: studyName({ id }), file } };
}

/** A size as the pane head shows it: 840 B, 20 kB, 4.6 MB, 88 MB. */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return `${bytes} B`;
  const kilobytes = Math.round(bytes / 1000);
  if (kilobytes < 1000) return `${kilobytes} kB`;
  const megabytes = bytes / 1_000_000;
  return megabytes < 9.95 ? `${megabytes.toFixed(1)} MB` : `${Math.round(megabytes)} MB`;
}

/** The scale of a zoom that no fit set, as the zoom select shows it: 125 %. */
export function zoomText(scale: number): string {
  return `${Math.round(scale * 100)} %`;
}

/** What the count beside the find field says: 3 of 12, or that nothing matches; nothing without a query. */
export function findText(result: FindResult | null, query: string): string {
  if (!query.trim() || result === null) return "";
  if (result.status === "missing") return "No matches";
  if (result.status === "pending" || result.total === 0) return "Finding…";
  return result.current > 0 ? `${result.current} of ${result.total}` : `${result.total} matches`;
}

/** What the local server answered to a PDF that it did not serve: its error, or that the page has no session. */
export type PaperAnswer = ApiError | SessionMissing;

/**
 * Why the local server did not serve the PDF at `url`, which PDF.js reports by the status alone:
 * the error of the server when it is asked again, for one byte of the PDF, or SessionMissing. Null
 * for another failure of PDF.js, and when the server serves the PDF now or cannot be reached.
 */
export async function paperAnswer(caught: unknown, url: string): Promise<PaperAnswer | null> {
  if (!(caught instanceof Error) || caught.name !== "ResponseException") return null;
  try {
    await checkFile(url);
  } catch (error) {
    if (error instanceof SessionMissing) return error;
    // ServerStopped is an ApiError of status 0, which says nothing about the PDF.
    if (error instanceof ApiError && error.status > 0) return error;
  }
  return null;
}

/**
 * The words and the code of a failure to show the PDF `file`, by the error of PDF.js and the
 * code of the answer of the local server, which tells a PDF that is gone (`not_found`) from one
 * that it cannot read: both may be a 404 to PDF.js.
 */
function failureWords(error: Error, status: number | null, answerCode: string | null, file: string): [string, string] {
  if (error instanceof PaperImportFailed)
    return [
      paperImport.state === "failed again"
        ? "The PDF viewer could not be loaded again. Reload the page to try again."
        : "The PDF viewer could not be loaded.",
      "viewer_unavailable",
    ];
  switch (error.name) {
    case "PasswordException":
      return [`${file} is protected by a password. Open it in the PDF program.`, "pdf_password"];
    case "InvalidPDFException":
      return [`${file} is damaged or not a PDF.`, "pdf_damaged"];
    case "ResponseException":
      return answerCode === "not_found"
        ? [`${file} is no longer in the study folder.`, "not_found"]
        : [`Could not read ${file}: the local server answered ${status ?? "nothing"}.`, answerCode ?? "pdf_unreadable"];
    default:
      return [`Could not show ${file}.`, "pdf_failed"];
  }
}

/**
 * The failure of a PDF that the viewer could not show, for the alert of a failed action: what
 * went wrong in words, and in its details the error of PDF.js with the request, or the answer
 * of the local server (`paperAnswer`) with its status, its code, its reason and its request id.
 * A lost session says what the status banner of the app says, without details.
 */
export function paperFailure(
  caught: unknown,
  file: string,
  url: string,
  answer: PaperAnswer | null = null,
): ActionFailure {
  if (answer instanceof SessionMissing) return actionFailure(NO_SESSION);
  const error = caught instanceof Error ? caught : new Error(String(caught));
  const status = answer?.status ?? ("status" in error && typeof error.status === "number" ? error.status : null);
  const [text, code] = failureWords(error, status, answer?.code ?? null, file);
  const details: FailureDetails = {
    status,
    code,
    detail: answer?.detail ?? `${error.name}: ${error.message}`,
    action: `Show the paper (GET ${url})`,
    requestId: answer?.requestId ?? null,
    time: answer?.time ?? null,
    traceback: answer?.traceback ?? null,
    activityId: answer?.activityId ?? null,
  };
  return actionFailure(text, [], null, details);
}
