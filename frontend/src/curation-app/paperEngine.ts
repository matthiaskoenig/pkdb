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
import { FITS, type Fit, type FindResult, type OpenPaper, type PaperSession } from "./paper";

/** The URL of a file of PDF.js in `pdfjs/` beside index.html. */
export function pdfjsAsset(path: string): string {
  return new URL(`pdfjs/${path}`, document.baseURI).href;
}

pdfjs.GlobalWorkerOptions.workerSrc = pdfjsAsset("pdf.worker.min.mjs");

/** The fit of a scale value of PDF.js; null for the scale of a zoom step. */
function fitOf(value: string): Fit | null {
  return FITS.find((fit) => fit === value) ?? null;
}

/** The matches of a find, as PDF.js counts them. */
interface MatchesCount {
  current: number;
  total: number;
}

export const openPaper: OpenPaper = async (container, url, events, start) => {
  const eventBus = new EventBus();
  const linkService = new PDFLinkService({ eventBus, externalLinkTarget: LinkTarget.BLANK });
  const findController = new PDFFindController({ eventBus, linkService });
  const viewer = new PDFViewer({
    container,
    eventBus,
    linkService,
    findController,
    // Links work; forms and editing do not.
    annotationMode: pdfjs.AnnotationMode.ENABLE,
    annotationEditorMode: pdfjs.AnnotationEditorType.DISABLE,
  });
  linkService.setViewer(viewer);

  // PDF.js reports no page for the first one: the page in view is reported once the pages exist.
  eventBus.on("pagesinit", () => {
    viewer.currentScaleValue = start.fit ?? String(start.scale);
    if (start.page > 1) viewer.currentPageNumber = Math.min(start.page, viewer.pagesCount);
    events.page(viewer.currentPageNumber);
  });
  eventBus.on("pagechanging", ({ pageNumber }: { pageNumber: number }) => events.page(pageNumber));
  eventBus.on("scalechanging", ({ scale }: { scale: number }) => events.scale(scale, fitOf(viewer.currentScaleValue)));
  // A find reports its state, first without matches, then the counts while it goes through the pages.
  let find: FindResult = { status: "pending", current: 0, total: 0 };
  function report(missing: boolean, { current, total }: MatchesCount): void {
    find = { status: missing ? "missing" : total > 0 ? "found" : "pending", current, total };
    events.found(find);
  }
  eventBus.on("updatefindcontrolstate", ({ state, matchesCount }: { state: number; matchesCount: MatchesCount }) =>
    report(state === FindState.NOT_FOUND, matchesCount),
  );
  eventBus.on("updatefindmatchescount", ({ matchesCount }: { matchesCount: MatchesCount }) =>
    report(find.status === "missing" && matchesCount.total === 0, matchesCount),
  );

  // PDF.js keeps a fit only until the size changes: the fit follows the pane, as in a PDF program.
  let frame = 0;
  const resized = new ResizeObserver(() => {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
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

  const task = pdfjs.getDocument({
    url,
    cMapUrl: pdfjsAsset("cmaps/"),
    cMapPacked: true,
    standardFontDataUrl: pdfjsAsset("standard_fonts/"),
    wasmUrl: pdfjsAsset("wasm/"),
    useWasm: false,
    disableAutoFetch: true,
    disableStream: true,
    enableXfa: false,
  });
  let pdf: Awaited<typeof task.promise>;
  try {
    pdf = await task.promise;
  } catch (error) {
    stop();
    await task.destroy();
    throw error;
  }
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
    },
    async close() {
      stop();
      viewer.setDocument(null);
      linkService.setDocument(null);
      await task.destroy();
    },
  };
  return session;
};
