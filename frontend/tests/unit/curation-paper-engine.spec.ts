import { beforeEach, describe, expect, it, vi } from "vitest";
import * as pdfjs from "pdfjs-dist";
import type { PaperEvents, PaperStart } from "../../src/curation-app/paper";
import { openPaper } from "../../src/curation-app/paperEngine";

/** A fake PDF.js: it records what the engine creates, asks and dispatches. */
const fake = vi.hoisted(() => {
  type Listener = (data: Record<string, unknown>) => void;
  const state: {
    bus: EventBus | null;
    viewer: PDFViewer | null;
    options: Record<string, unknown> | null;
    task: { promise: Promise<{ numPages: number }>; destroy: () => Promise<void> };
  } = { bus: null, viewer: null, options: null, task: { promise: Promise.resolve({ numPages: 3 }), destroy: async () => undefined } };
  class EventBus {
    readonly listeners = new Map<string, Listener[]>();
    readonly dispatched: [string, Record<string, unknown>][] = [];
    constructor() {
      state.bus = this;
    }
    on(name: string, listener: Listener): void {
      this.listeners.set(name, [...(this.listeners.get(name) ?? []), listener]);
    }
    dispatch(name: string, data: Record<string, unknown>): void {
      this.dispatched.push([name, data]);
      for (const listener of this.listeners.get(name) ?? []) listener(data);
    }
  }
  class PDFViewer {
    currentScaleValue = "auto";
    currentPageNumber = 1;
    readonly pagesCount = 3;
    readonly options: Record<string, unknown>;
    readonly documents: unknown[] = [];
    readonly steps: number[] = [];
    constructor(options: Record<string, unknown>) {
      this.options = options;
      state.viewer = this;
    }
    setDocument(document: unknown): void {
      this.documents.push(document);
    }
    increaseScale(): void {
      this.steps.push(1);
    }
    decreaseScale(): void {
      this.steps.push(-1);
    }
    update(): void {}
  }
  class PDFLinkService {
    readonly options: Record<string, unknown>;
    readonly documents: unknown[] = [];
    constructor(options: Record<string, unknown>) {
      this.options = options;
    }
    setViewer(): void {}
    setDocument(document: unknown): void {
      this.documents.push(document);
    }
  }
  class PDFFindController {
    readonly options: Record<string, unknown>;
    constructor(options: Record<string, unknown>) {
      this.options = options;
    }
  }
  return { state, EventBus, PDFViewer, PDFLinkService, PDFFindController };
});

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  AnnotationMode: { ENABLE: 1 },
  AnnotationEditorType: { DISABLE: -1 },
  getDocument: (options: Record<string, unknown>) => {
    fake.state.options = options;
    return fake.state.task;
  },
}));
vi.mock("pdfjs-dist/web/pdf_viewer.mjs", () => ({
  EventBus: fake.EventBus,
  PDFViewer: fake.PDFViewer,
  PDFLinkService: fake.PDFLinkService,
  PDFFindController: fake.PDFFindController,
  LinkTarget: { BLANK: 2 },
  FindState: { FOUND: 0, NOT_FOUND: 1, WRAPPED: 2, PENDING: 3 },
}));

const BASE = new URL("pdfjs/", document.baseURI).href;
const URL_A = "/local/studies/caffeine/Example/files/Example.pdf";
const START: PaperStart = { page: 1, fit: "page-width", scale: 1 };

function events() {
  return { opened: vi.fn(), page: vi.fn(), scale: vi.fn(), found: vi.fn() } satisfies PaperEvents;
}

/** The scroll container of the viewer with its empty `div.pdfViewer`. */
function container(): HTMLDivElement {
  const element = document.createElement("div");
  element.append(document.createElement("div"));
  return element;
}

beforeEach(() => {
  fake.state.bus = null;
  fake.state.viewer = null;
  fake.state.options = null;
  fake.state.task = { promise: Promise.resolve({ numPages: 3 }), destroy: vi.fn(async () => undefined) };
});

describe("the PDF.js engine of the paper viewer", () => {
  it("loads the worker of PDF.js from pdfjs/ beside the app", () => {
    expect(pdfjs.GlobalWorkerOptions.workerSrc).toBe(`${BASE}pdf.worker.min.mjs`);
  });

  it("opens a PDF in ranges with the options that the Content Security Policy of the local server allows", async () => {
    await openPaper(container(), URL_A, events(), START);
    expect(fake.state.options).toEqual({
      url: URL_A,
      cMapUrl: `${BASE}cmaps/`,
      cMapPacked: true,
      standardFontDataUrl: `${BASE}standard_fonts/`,
      wasmUrl: `${BASE}wasm/`,
      useWasm: false,
      disableAutoFetch: true,
      disableStream: true,
      enableXfa: false,
    });
    expect(fake.state.viewer!.options).toMatchObject({ annotationMode: 1, annotationEditorMode: -1 });
    expect(fake.state.viewer!.options).not.toHaveProperty("scriptingManager");
    expect(fake.state.viewer!.documents).toEqual([{ numPages: 3 }]);
  });

  it("starts on the page and the fit of the viewer and reports the page, the zoom and the finds", async () => {
    const reported = events();
    await openPaper(container(), URL_A, reported, { page: 2, fit: "page-fit", scale: 1 });
    const bus = fake.state.bus!;
    const viewer = fake.state.viewer!;
    expect(reported.opened).toHaveBeenCalledWith(3);
    bus.dispatch("pagesinit", {});
    expect([viewer.currentScaleValue, viewer.currentPageNumber]).toEqual(["page-fit", 2]);
    expect(reported.page).toHaveBeenLastCalledWith(2);
    bus.dispatch("pagechanging", { pageNumber: 3 });
    expect(reported.page).toHaveBeenLastCalledWith(3);
    viewer.currentScaleValue = "1.1";
    bus.dispatch("scalechanging", { scale: 1.1 });
    expect(reported.scale).toHaveBeenLastCalledWith(1.1, null);
    viewer.currentScaleValue = "page-width";
    bus.dispatch("scalechanging", { scale: 0.9 });
    expect(reported.scale).toHaveBeenLastCalledWith(0.9, "page-width");
    bus.dispatch("updatefindcontrolstate", { state: 0, matchesCount: { current: 0, total: 0 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "pending", current: 0, total: 0 });
    bus.dispatch("updatefindmatchescount", { matchesCount: { current: 1, total: 3 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "found", current: 1, total: 3 });
    bus.dispatch("updatefindcontrolstate", { state: 1, matchesCount: { current: 0, total: 0 } });
    expect(reported.found).toHaveBeenLastCalledWith({ status: "missing", current: 0, total: 0 });
  });

  it("starts at the scale of zoom steps without a fit", async () => {
    await openPaper(container(), URL_A, events(), { page: 1, fit: null, scale: 1.25 });
    fake.state.bus!.dispatch("pagesinit", {});
    expect(fake.state.viewer!.currentScaleValue).toBe("1.25");
  });

  it("goes to pages, zooms, fits, finds, and ends a find", async () => {
    const session = await openPaper(container(), URL_A, events(), START);
    const viewer = fake.state.viewer!;
    session.goTo(3);
    expect(viewer.currentPageNumber).toBe(3);
    session.zoom(1);
    session.zoom(-1);
    expect(viewer.steps).toEqual([1, -1]);
    session.fit("1");
    expect(viewer.currentScaleValue).toBe("1");
    session.find("the", { again: false, previous: false });
    session.find("the", { again: true, previous: true });
    session.find("", { again: false, previous: false });
    const dispatched = fake.state.bus!.dispatched;
    expect(dispatched.map(([name, data]) => [name, data.type, data.query, data.findPrevious])).toEqual([
      ["find", "", "the", false],
      ["find", "again", "the", true],
      ["findbarclose", undefined, undefined, undefined],
    ]);
    expect(dispatched[0]![1]).toMatchObject({ caseSensitive: false, entireWord: false, highlightAll: true, matchDiacritics: false });
  });

  it("closes the PDF and its worker", async () => {
    const session = await openPaper(container(), URL_A, events(), START);
    await session.close();
    expect(fake.state.viewer!.documents.at(-1)).toBeNull();
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
  });

  it("ends the loading of a PDF that PDF.js cannot open, with its error", async () => {
    const error = Object.assign(new Error("Invalid PDF structure."), { name: "InvalidPDFException" });
    fake.state.task = { promise: Promise.reject(error), destroy: vi.fn(async () => undefined) };
    await expect(openPaper(container(), URL_A, events(), START)).rejects.toBe(error);
    expect(fake.state.task.destroy).toHaveBeenCalledTimes(1);
  });
});
