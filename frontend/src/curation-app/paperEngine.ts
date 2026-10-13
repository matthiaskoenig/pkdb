/**
 * The viewer of PDF.js behind `OpenPaper` (paper.ts), in a chunk of its own with the stylesheet
 * of PDF.js. Its options keep to the Content Security Policy of the local server, which allows
 * no WebAssembly and no eval, and change nothing about it:
 *
 * - `useWasm: false`: JPEG 2000, JBIG2 and CCITT images decode with the JavaScript decoders in
 *   `pdfjs/wasm/`, PostScript functions are interpreted, and ICC colors are not managed. With
 *   WebAssembly, the worker would try to compile it first: a violation that the page never sees.
 * - PDF.js 6 has no eval (no `isEvalSupported`), and runs no script of a PDF without a
 *   scripting manager, which the viewer does not get.
 * - The PDF loads in ranges of 64 kB as its pages need them: `disableAutoFetch` with
 *   `disableStream`, without which PDF.js would read the whole file in the background.
 * - The worker, the character maps, the standard fonts and the decoders come from `pdfjs/`
 *   beside the app, which the build copies (vite.curation.config.ts).
 * - Aborting the opening stops the loading with its worker and its range requests, and the viewer
 *   of PDF.js stops watching the pane: a PDF that is no longer wanted never draws into it.
 *
 * pdf_viewer.mjs reads `globalThis.pdfjsLib` when it loads, which pdfjs-dist sets: it comes first.
 */
import * as pdfjs from "pdfjs-dist";
import {
  EventBus,
  FindState,
  LinkTarget,
  PDFFindController,
  PDFLinkService,
  PDFViewer,
} from "pdfjs-dist/web/pdf_viewer.mjs";
import "pdfjs-dist/web/pdf_viewer.css";
import "./paper.css";
import { isAbort } from "./api/client";
import { FITS, type Fit, type FindResult, type OpenPaper, type PaperSession } from "./paper";

/** The URL of a file of PDF.js in `pdfjs/` beside index.html. */
export function pdfjsAsset(path: string): string {
  return new URL(`pdfjs/${path}`, document.baseURI).href;
}

pdfjs.GlobalWorkerOptions.workerSrc = pdfjsAsset("pdf.worker.min.mjs");

/**
 * PDF.js 6.4.299 cancels the request of a range twice when a PDF closes while the range loads:
 * once when its worker ends and once when it cancels all requests. The second cancel rejects with
 * the AbortError of the first, which nothing handles, so the browser would report an error for a
 * PDF that was closed on purpose. While a PDF is being destroyed, and for one task after that, as
 * the browser reports a rejection that nothing handled after the task that made it, an AbortError
 * that nothing handled is not reported. Any other time it is: an unhandled AbortError of the app
 * is a bug.
 */
function quietAbort(event: Event & { reason?: unknown }): void {
  if (isAbort(event.reason)) event.preventDefault();
}

/**
 * The errors that the viewer of PDF.js 6.4.299 logs for a page that it still loads when its PDF
 * closes, by their label and the message of their reason: the page fails with "Transport
 * destroyed", and the viewer then draws the page view without its page.
 */
const CLOSING_ERRORS = new Map([
  ["Unable to get page for page view", "Transport destroyed"],
  ["renderView:", "pdfPage is not loaded"],
]);

/** `console.error` of the page, while `quietConsole` stands in for it. */
let logError: typeof console.error = console.error;

/** `console.error`, which leaves out the errors of a page that was loading as its PDF closed. */
function quietConsole(...data: unknown[]): void {
  const [label, reason] = data;
  if (typeof label === "string" && reason instanceof Error && CLOSING_ERRORS.get(label) === reason.message) return;
  logError(...data);
}

/** How many PDFs are being destroyed. */
let destroying = 0;

/**
 * `destroyed`, during which and one task after which a cancelled request is not reported and the
 * errors of a page that was loading are not logged.
 */
function quietWhile(destroyed: Promise<void>): Promise<void> {
  if (destroying++ === 0) {
    window.addEventListener("unhandledrejection", quietAbort);
    logError = console.error;
    console.error = quietConsole;
  }
  return destroyed.finally(() =>
    setTimeout(() => {
      if (--destroying === 0) {
        window.removeEventListener("unhandledrejection", quietAbort);
        console.error = logError;
      }
    }, 0),
  );
}

/** The fit of a scale value of PDF.js; null for the scale of a zoom step. */
function fitOf(value: string): Fit | null {
  return FITS.find((fit) => fit === value) ?? null;
}

/** The matches of a find, as PDF.js counts them. */
interface MatchesCount {
  current: number;
  total: number;
}

/** A find without a count yet. */
const PENDING: FindResult = { status: "pending", current: 0, total: 0 };

/** The find of `count`: at a match of its matches, or still without one. */
function counted({ current, total }: MatchesCount): FindResult {
  return total > 0 ? { status: "found", current, total } : PENDING;
}

/**
 * The options of the viewer of PDF.js with `abortSignal`, an option at run time that the typings
 * of pdfjs-dist 6.4.299 lack: once it aborts, the viewer stops watching the size and the scrolling
 * of its container.
 */
type ViewerOptions = ConstructorParameters<typeof PDFViewer>[0] & { abortSignal: AbortSignal };

/** How long a closing PDF may take to destroy its task before its worker goes all the same. */
const DESTROY_MS = 2000;

/** A promise that resolves after `ms`. */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** `promise`, unless `signal` aborts first: then the reason of the abort. */
function unlessAborted<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const abort = (): void => reject(signal.reason);
    signal.addEventListener("abort", abort, { once: true });
    void promise.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

export const openPaper: OpenPaper = async (container, url, events, start, signal) => {
  signal.throwIfAborted();
  const eventBus = new EventBus();
  const linkService = new PDFLinkService({ eventBus, externalLinkTarget: LinkTarget.BLANK });
  const findController = new PDFFindController({ eventBus, linkService });
  const options: ViewerOptions = {
    container,
    eventBus,
    linkService,
    findController,
    // Links work; forms and editing do not.
    annotationMode: pdfjs.AnnotationMode.ENABLE,
    annotationEditorMode: pdfjs.AnnotationEditorType.DISABLE,
    abortSignal: signal,
  };
  const viewer = new PDFViewer(options);
  linkService.setViewer(viewer);

  // A hidden pane (`display: none`, as the Data section hides the paper while another source
  // shows) has no size, and the browser forgets how far it was scrolled. A fit to no size would
  // give the pages a scale below 0 and scroll a page that has no place: the fit and the first page
  // wait until the pane shows, and then the pages come back where they were.
  const sized = (): boolean => container.clientWidth > 0 && container.clientHeight > 0;
  let hidden = !sized();
  let scrolled = { top: 0, left: 0 };
  container.addEventListener(
    "scroll",
    () => {
      if (!hidden && sized()) scrolled = { top: container.scrollTop, left: container.scrollLeft };
    },
    { signal },
  );

  // PDF.js reports no page for the first one: the page in view is reported once the pages exist.
  let started = false;
  function begin(): void {
    started = true;
    viewer.currentScaleValue = start.fit ?? String(start.scale);
    if (start.page > 1) viewer.currentPageNumber = Math.min(start.page, viewer.pagesCount);
    events.page(viewer.currentPageNumber);
  }
  let initialized = false;
  eventBus.on("pagesinit", () => {
    initialized = true;
    if (sized()) begin();
  });
  eventBus.on("pagechanging", ({ pageNumber }: { pageNumber: number }) => events.page(pageNumber));
  eventBus.on("scalechanging", ({ scale }: { scale: number }) => events.scale(scale, fitOf(viewer.currentScaleValue)));
  // A find reports its state, first without matches, then the counts while it goes through the
  // pages. PDF.js reports a pending find with the counts of the match that it selected last.
  let find: FindResult = PENDING;
  function report(result: FindResult): void {
    find = result;
    events.found(result);
  }
  eventBus.on("updatefindcontrolstate", ({ state, matchesCount }: { state: number; matchesCount: MatchesCount }) => {
    if (state === FindState.NOT_FOUND) report({ status: "missing", current: 0, total: 0 });
    else report(state === FindState.PENDING ? PENDING : counted(matchesCount));
  });
  eventBus.on("updatefindmatchescount", ({ matchesCount }: { matchesCount: MatchesCount }) =>
    report(find.status === "missing" && matchesCount.total === 0 ? find : counted(matchesCount)),
  );

  // PDF.js keeps a fit only until the size changes: the fit follows the pane, as in a PDF program.
  let frame = 0;
  const resized = new ResizeObserver(() => {
    if (!sized()) {
      hidden = true;
      return;
    }
    if (hidden) {
      hidden = false;
      container.scrollTop = scrolled.top;
      container.scrollLeft = scrolled.left;
    }
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (!sized()) return;
      if (!started) {
        if (initialized) begin();
        return;
      }
      const value = viewer.currentScaleValue;
      if (value === "page-width" || value === "page-fit") viewer.currentScaleValue = value;
      viewer.update();
    });
  });
  resized.observe(container);
  function stop(): void {
    resized.disconnect();
    cancelAnimationFrame(frame);
  }

  // A worker of its own, which goes with the PDF also when PDF.js does not finish destroying it.
  const worker = new pdfjs.PDFWorker();
  const task = pdfjs.getDocument({
    url,
    worker,
    cMapUrl: pdfjsAsset("cmaps/"),
    cMapPacked: true,
    standardFontDataUrl: pdfjsAsset("standard_fonts/"),
    wasmUrl: pdfjsAsset("wasm/"),
    useWasm: false,
    disableAutoFetch: true,
    disableStream: true,
    enableXfa: false,
  });
  // The task goes once, whoever ends it first, and its worker with it. PDF.js 6.4.299 can wait
  // forever for a page whose ranges it cancelled when it destroys the task; the worker goes
  // after DESTROY_MS then, which stops whatever it still does.
  let destroyed: Promise<void> | null = null;
  function destroy(): Promise<void> {
    destroyed ??= quietWhile(
      Promise.race([task.destroy().catch(() => undefined), delay(DESTROY_MS)]).then(() => worker.destroy()),
    );
    return destroyed;
  }
  // Aborted while it loads, the loading stops at once with its worker and its range requests.
  // A PDF that opened is closed by its session.
  const cancel = (): void => {
    stop();
    void destroy();
  };
  signal.addEventListener("abort", cancel, { once: true });
  let pdf: Awaited<typeof task.promise>;
  try {
    pdf = await unlessAborted(task.promise, signal);
    // A PDF that loaded just as its viewer aborted never comes into the container.
    signal.throwIfAborted();
  } catch (error) {
    stop();
    await destroy();
    throw error;
  }
  signal.removeEventListener("abort", cancel);
  signal.addEventListener("abort", stop, { once: true });
  viewer.setDocument(pdf);
  linkService.setDocument(pdf, null);
  events.opened(pdf.numPages);

  const session: PaperSession = {
    goTo(page) {
      viewer.currentPageNumber = page;
    },
    zoom(step) {
      if (step > 0) viewer.increaseScale();
      else viewer.decreaseScale();
    },
    fit(fit) {
      viewer.currentScaleValue = fit;
    },
    find(query, { again, previous }) {
      if (!query) {
        eventBus.dispatch("findbarclose", { source: session });
        return;
      }
      eventBus.dispatch("find", {
        source: session,
        type: again ? "again" : "",
        query,
        caseSensitive: false,
        entireWord: false,
        highlightAll: true,
        findPrevious: previous,
        matchDiacritics: false,
      });
      // A new query has no count yet, though PDF.js keeps the one of the last query until it has.
      if (!again) report(PENDING);
    },
    async close() {
      stop();
      viewer.setDocument(null);
      linkService.setDocument(null);
      await destroy();
    },
  };
  return session;
};
